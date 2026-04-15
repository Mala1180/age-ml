from typing import Any, Dict, List

import yaml
from pydantic import BaseModel

from automlllm.common.types import Step
from automlllm.specification.types import (
    Budgets,
    Candidate,
    Constraint,
    DatasetCondition,
    DatasetFeatureCondition,
    Defaults,
    NaturalLanguageCondition,
    OrderingRule,
    SpecStep,
    StepCondition,
    SemanticCondition,
)


class ParsedSpecification(BaseModel):
    budgets: Budgets
    steps: List[SpecStep]
    ordering: List[OrderingRule]
    constraints: List[Constraint]
    semantic_constraints: List[Constraint]
    technical_details: List[str]


class SpecificationParser:
    def __init__(self, spec_yaml: str) -> None:
        self.spec_yaml: str = spec_yaml

    def parse(self) -> ParsedSpecification:
        spec: Dict = yaml.safe_load(self.spec_yaml)
        raw_budgets: Dict[str, Any] = dict(spec.get("budgets", {}))
        budgets: Budgets = Budgets.model_validate(raw_budgets)

        defaults_data = spec["pipeline"]["defaults"]
        defaults = Defaults.model_validate(defaults_data).model_dump()

        steps: List[SpecStep] = []
        for step_id, step_data in spec["pipeline"]["steps"].items():
            candidates_data = step_data.get("candidates", [])
            parsed_candidates: List[Candidate] = []
            for c in candidates_data:
                if isinstance(c, str):
                    parsed_candidates.append(Candidate(name=c))
                elif isinstance(c, dict):
                    name: str = list(c.keys())[0]
                    params: Dict = c[name].get("params", {})
                    parsed_candidates.append(Candidate(name=name, params=params))

            step_data["candidates"] = parsed_candidates
            steps.append(
                SpecStep.model_validate(
                    {
                        "id": step_id,
                        **defaults,
                        **step_data,
                    }
                )
            )

        ordering = self._parse_ordering(spec.get("ordering", []))

        constraints: List[Constraint] = []
        semantic_constraints: List[Constraint] = []
        for constraint_dict in spec.get("constraints", []):
            condition_node: str | Dict[str, Any] = constraint_dict["if"]
            require_nodes: List[str | Dict[str, Any]] = constraint_dict.get(
                "require", []
            )
            forbid_nodes: List[str | Dict[str, Any]] = constraint_dict.get("forbid", [])

            required_steps: List[Step] = []
            forbidden_steps: List[Step] = []
            for required in require_nodes:
                required_steps.append(self._get_step_with_value(required))
            for forbidden in forbid_nodes:
                forbidden_steps.append(self._get_step_with_value(forbidden))

            condition = self._parse_condition(condition_node)
            constraint: Constraint = Constraint.model_validate(
                {
                    "condition": condition,
                    "require": required_steps,
                    "forbid": forbidden_steps,
                }
            )
            if isinstance(constraint.condition, SemanticCondition):
                semantic_constraints.append(constraint)
            else:
                constraints.append(constraint)

        technical_details: List[str] = spec.get("technical_details", [])

        return ParsedSpecification(
            budgets=budgets,
            steps=steps,
            ordering=ordering,
            constraints=constraints,
            semantic_constraints=semantic_constraints,
            technical_details=technical_details,
        )

    def _parse_ordering(
        self, ordering_nodes: List[Dict[str, Any]]
    ) -> List[OrderingRule]:
        parsed_ordering: List[OrderingRule] = []
        seen_pairs: set[tuple[str, str]] = set()

        for node in ordering_nodes:
            rules: List[OrderingRule] = []

            if "sequence" in node:
                sequence: List[str] = node["sequence"]
                for i in range(len(sequence) - 1):
                    for j in range(i + 1, len(sequence)):
                        rules.append(
                            OrderingRule.model_validate(
                                {"before": sequence[i], "after": sequence[j]}
                            )
                        )
            else:
                rules.append(OrderingRule.model_validate(node))

            for rule in rules:
                pair = (rule.before, rule.after)
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                parsed_ordering.append(rule)

        return parsed_ordering

    def _get_step_with_value(self, node: str | Dict[str, Any]) -> Step:
        if isinstance(node, str):
            return Step(name=node, candidate="", hyperparameters={})
        else:
            node_id: str = list(node.keys())[0]
            node_value: Any = node[node_id]
            candidate: str = node_value if isinstance(node_value, str) else ""
            return Step(name=node_id, candidate=candidate, hyperparameters={})

    def _parse_condition(
        self, node: str | Dict[str, Any]
    ) -> StepCondition | DatasetCondition | NaturalLanguageCondition:
        if isinstance(node, str):
            return self._parse_natural_language_condition(node)
        if not isinstance(node, dict) or not node:
            raise ValueError(
                "Constraint 'if' condition must be a non-empty string or define a 'step' or 'dataset' key."
            )

        if "step" in node:
            return self._parse_step_condition(node)
        if "dataset" in node:
            return self._parse_dataset_condition(node)
        raise ValueError(
            "Constraint 'if' condition must be a non-empty string or define a 'step' or 'dataset' key."
        )

    def _parse_step_condition(self, node: Dict[str, Any]) -> StepCondition:
        step_node: Any = node.get("step")
        if isinstance(step_node, str):
            if step_node == "":
                raise ValueError("Constraint 'if.step' condition cannot be empty.")
            return StepCondition(step=step_node, candidate=None)

        if not isinstance(step_node, dict):
            raise ValueError(
                "Constraint 'if.step' condition must be a string or a dict[str, str]."
            )
        if not step_node:
            raise ValueError("Constraint 'if.step' condition cannot be empty.")
        if len(step_node) > 1:
            raise ValueError(
                "Constraint 'if.step' dictionary condition must contain a single step."
            )

        step: str = next(iter(step_node.keys()))
        candidate_node: Any = step_node[step]
        if not isinstance(candidate_node, str) or candidate_node == "":
            raise ValueError(
                "Constraint 'if.step' dictionary condition must be of type dict[str, str]."
            )
        return StepCondition(step=step, candidate=Candidate(name=candidate_node))

    def _parse_dataset_condition(self, node: Dict[str, Any]) -> DatasetCondition:
        dataset_node: Any = node.get("dataset")
        if not isinstance(dataset_node, dict) or not dataset_node:
            raise ValueError("Constraint 'if.dataset' condition cannot be empty.")

        feature_node: Any = dataset_node.get("feature")
        if not isinstance(feature_node, dict) or not feature_node:
            raise ValueError("Constraint 'if.dataset.feature' cannot be empty.")

        return DatasetCondition(
            feature=DatasetFeatureCondition.model_validate(feature_node)
        )

    def _parse_natural_language_condition(self, node: str) -> NaturalLanguageCondition:
        if not isinstance(node, str) or node == "":
            raise ValueError(
                "Constraint 'if' natural language condition must be a non-empty string."
            )
        return NaturalLanguageCondition(text=node)
