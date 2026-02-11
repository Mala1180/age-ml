from typing import Dict, List

import yaml
from pydantic import BaseModel

from automlllm.specification.types import (
    Candidate,
    Constraint,
    Defaults,
    Node,
    OrderingRule,
    Step,
)


class ParsedSpecification(BaseModel):
    steps: List[Step]
    ordering: List[OrderingRule]
    constraints: List[Constraint]


class SpecificationParser:
    def __init__(self, spec_yaml: str):
        self.spec_yaml = spec_yaml

    def parse(self) -> ParsedSpecification:
        spec: Dict = yaml.safe_load(self.spec_yaml)

        defaults_data = spec["pipeline"]["defaults"]
        defaults = Defaults.model_validate(defaults_data).model_dump()

        steps: List[Step] = []
        for step_id, step_data in spec["pipeline"]["steps"].items():
            candidates_data = step_data.get("candidates", [])
            parsed_candidates = []
            for c in candidates_data:
                if isinstance(c, str):
                    parsed_candidates.append(Candidate(name=c))
                elif isinstance(c, dict):
                    name = list(c.keys())[0]
                    params = c[name].get("params", {})
                    parsed_candidates.append(Candidate(name=name, params=params))

            step_data["candidates"] = parsed_candidates
            steps.append(
                Step.model_validate(
                    {
                        "id": step_id,
                        **defaults,
                        **step_data,
                    }
                )
            )

        ordering: List[OrderingRule] = [
            OrderingRule.model_validate(order) for order in spec["partial_ordering"]
        ]

        constraints: List[Constraint] = []
        for constraint in spec.get("constraints", []):
            required_nodes: List[Node] = []
            forbidden_nodes: List[Node] = []
            for required in constraint.get("require", []):
                required_nodes.append(self._get_node_with_value(required))
            for forbidden in constraint.get("forbid", []):
                forbidden_nodes.append(self._get_node_with_value(forbidden))

            constraints.append(
                Constraint.model_validate(
                    {
                        "condition": constraint["if"],
                        "require": required_nodes,
                        "forbid": forbidden_nodes,
                    }
                )
            )

        return ParsedSpecification(
            steps=steps, ordering=ordering, constraints=constraints
        )

    def _get_node_with_value(self, node: str | Dict[str, str]) -> Node:
        if isinstance(node, str):
            return Node(id=node)
        else:
            node_id: str = list(node.keys())[0]
            node_value: str = node[node_id]
            return Node(id=node_id, value=node_value)
