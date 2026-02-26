from typing import Any, Dict, List

import yaml
from pydantic import BaseModel

from automlllm.common.types import Step
from automlllm.specification.types import (
    Candidate,
    Constraint,
    Defaults,
    OrderingRule,
    SpecStep,
)


class ParsedSpecification(BaseModel):
    steps: List[SpecStep]
    ordering: List[OrderingRule]
    constraints: List[Constraint]
    technical_details: List[str]


class SpecificationParser:
    def __init__(self, spec_yaml: str) -> None:
        self.spec_yaml: str = spec_yaml

    def parse(self) -> ParsedSpecification:
        spec: Dict = yaml.safe_load(self.spec_yaml)

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

        ordering: List[OrderingRule] = [
            OrderingRule.model_validate(order)
            for order in spec["pipeline"]["partial_ordering"]
        ]

        constraints: List[Constraint] = []
        for constraint in spec["pipeline"].get("constraints", []):
            required_steps: List[Step] = []
            forbidden_steps: List[Step] = []
            for required in constraint.get("require", []):
                required_steps.append(self._get_step_with_value(required))
            for forbidden in constraint.get("forbid", []):
                forbidden_steps.append(self._get_step_with_value(forbidden))

            constraints.append(
                Constraint.model_validate(
                    {
                        "condition": constraint["if"],
                        "require": required_steps,
                        "forbid": forbidden_steps,
                    }
                )
            )

        technical_details: List[str] = spec.get("technical_details", [])

        return ParsedSpecification(
            steps=steps,
            ordering=ordering,
            constraints=constraints,
            technical_details=technical_details,
        )

    def _get_step_with_value(self, node: str | Dict[str, Any]) -> Step:
        if isinstance(node, str):
            return Step(name=node, candidate="", hyperparameters={})
        else:
            node_id: str = list(node.keys())[0]
            node_value: Any = node[node_id]
            candidate: str = node_value if isinstance(node_value, str) else ""
            return Step(name=node_id, candidate=candidate, hyperparameters={})
