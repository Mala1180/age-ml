from typing import Optional, Dict, List, Tuple

import networkx as nx
import yaml
from networkx import MultiDiGraph
from pydantic import BaseModel, Field, ConfigDict


class StepFields(BaseModel):
    model_config = ConfigDict(extra="forbid")
    values: List[str] = Field(default_factory=list)
    mandatory: bool = False
    initial: bool = False
    terminal: bool = False


class Defaults(StepFields):
    pass


class Step(StepFields):
    id: str


class OrderingRule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    before: str
    after: str


class Constraint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    condition: Dict
    require: Optional[List[str] | Dict] = Field(default_factory=list)
    forbid: Optional[List[str] | Dict] = Field(default_factory=list)


class Specification:
    def __init__(
        self,
        steps: List[Step],
        ordering: List[OrderingRule],
        constraints: List[Constraint],
    ) -> None:
        self.steps: List[Step] = steps
        self.ordering: List[OrderingRule] = ordering
        self.constraints: List[Constraint] = constraints

    @classmethod
    def parse(cls, spec_yaml: str) -> "Specification":
        spec: Dict = yaml.safe_load(spec_yaml)

        defaults = Defaults.model_validate(spec["pipeline"]["defaults"]).model_dump()

        steps: List[Step] = [
            Step.model_validate(
                {
                    "id": step_id,
                    **defaults,
                    **step_data,
                }
            )
            for step_id, step_data in spec["pipeline"]["steps"].items()
        ]

        ordering: List[OrderingRule] = [
            OrderingRule.model_validate(order) for order in spec["partial_ordering"]
        ]

        constraints: List[Constraint] = [
            Constraint.model_validate(
                {
                    "condition": constraint["if"],
                    "require": constraint.get("require", None),
                    "forbid": constraint.get("forbid", None),
                }
            )
            for constraint in spec.get("constraints", [])
        ]

        return cls(steps, ordering, constraints)

    def _check_admissible_step(self, graph: MultiDiGraph) -> bool:
        for node in graph:
            if node not in self.steps:
                return False
        return True

    def _check_ordering(self, graph: MultiDiGraph, before: str, after: str) -> bool:
        return any(nx.all_simple_paths(graph, source=before, target=after))

    def _check_constraint(
        self,
        graph: MultiDiGraph,
        condition: Dict,
        require: Dict,
        forbid: Dict,
    ) -> Tuple[bool, Optional[str]]:
        condition_node, condition_value = list(condition.items())[0]
        is_valid: bool = True
        feedbacks: List[str] = []
        if condition_node in graph:
            if (
                condition_value == {}
                or graph.nodes[condition_node]["value"] == condition_value
            ):
                message: str
                required_nodes = set(require.get("steps", {}))
                if not required_nodes.issubset(graph.nodes):
                    is_valid = False
                    message = (
                        f"Constraint violated since {str(condition)} "
                        f"condition is met but some of required nodes "
                        f"{str(require['steps'])} are missing."
                    )
                    feedbacks.append(message)

                forbidden_nodes = set(forbid.get("steps", []))
                if forbidden_nodes.intersection(graph.nodes):
                    is_valid = False
                    message = (
                        f"Constraint violated since {str(condition)} "
                        f"condition is met but some of forbidden nodes "
                        f"{str(forbid['steps'])} are present."
                    )
                    feedbacks.append(message)

        return is_valid, None if is_valid else "\n".join(feedbacks)

    def _validate_allowed_steps(
        self, graph: MultiDiGraph
    ) -> Tuple[bool, Optional[str]]:
        for node_id in graph:
            if node_id not in self.steps:
                return (
                    False,
                    f"Unknown node '{node_id}', admissible nodes are {list(self.steps.keys())}.",
                )

            if self.steps[node_id].get("values") == {}:
                continue
            if graph.nodes[node_id]["value"] not in self.steps[node_id].get("values"):
                return (
                    False,
                    f"Node '{node_id}' has invalid value '{graph.nodes[node_id]['value']}', "
                    f"admissible values are {self.steps[node_id].get('values')}.",
                )
        return True, None

    def _validate_initial_steps(
        self, graph: MultiDiGraph
    ) -> Tuple[bool, Optional[str]]:
        for step_id, step in self.steps.items():
            if step_id in graph and step.get("initial", False):
                if graph.in_degree(step_id) != 0:
                    return (
                        False,
                        f"Node {step_id} must be initial but has ingoing edges.",
                    )
        return True, None

    def _validate_terminal_steps(
        self, graph: MultiDiGraph
    ) -> Tuple[bool, Optional[str]]:
        for step_id, step in self.steps.items():
            if step_id in graph and step.get("terminal", False):
                if graph.out_degree(step_id) != 0:
                    return (
                        False,
                        f"Node {step_id} must be terminal but has outgoing edges.",
                    )
        return True, None

    def _validate_connectivity(self, graph: MultiDiGraph) -> Tuple[bool, Optional[str]]:
        if not nx.is_weakly_connected(graph):
            return False, "Graph is not connected."
        return True, None

    def _validate_ordering(self, graph: MultiDiGraph) -> Tuple[bool, Optional[str]]:
        for ordering in self.rules.get("ordering", []):
            before = ordering["before"]
            after = ordering["after"]

            if (
                after in graph
                and before in graph
                and not self._check_ordering(graph, before, after)
            ):
                return False, f"Ordering {ordering} violated."
        return True, None

    def _validate_constraints(self, graph: MultiDiGraph) -> Tuple[bool, Optional[str]]:
        for constraint in self.constraints:
            condition = constraint["if"]
            require = constraint.get("require", {})
            forbid = constraint.get("forbid", {})
            is_valid, message = self._check_constraint(
                graph, condition, require, forbid
            )
            if not is_valid:
                return False, message
        return True, None

    def validate(
        self, graph: MultiDiGraph, fail_fast: bool = False
    ) -> Tuple[bool, Optional[str]]:
        checks = [
            self._validate_allowed_steps,
            self._validate_initial_steps,
            self._validate_terminal_steps,
            self._validate_connectivity,
            self._validate_ordering,
            self._validate_constraints,
        ]
        overall_feedback: List[str] = []
        for check in checks:
            is_valid, message = check(graph)
            if not is_valid and message:
                overall_feedback.append(message)
                if fail_fast:
                    return is_valid, "\n".join(overall_feedback)
        if len(overall_feedback) > 0:
            return False, "\n".join(overall_feedback)
        return True, None


# spec_string: str = get_test_resource_path("specification-sample.yml").read_text()
# # spec_string = get_resource_path("automl-specification.yml").read_text()
#
# spec_sample: Specification = Specification.parse(spec_string)
# print(spec_sample.steps)
# print(spec_sample.ordering)
# print(spec_sample.constraints)
