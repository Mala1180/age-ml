from typing import Optional, Dict, List, Tuple, Set

import networkx as nx
import yaml
from networkx import MultiDiGraph
from pydantic import BaseModel, Field, ConfigDict


class Node(BaseModel):
    id: str
    value: Optional[str] = None


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
    require: List[Node] = Field(default_factory=list)
    forbid: List[Node] = Field(default_factory=list)


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

        constraints: List[Constraint] = []
        for constraint in spec.get("constraints", []):
            required_nodes: List[Node] = []
            forbidden_nodes: List[Node] = []
            for required in constraint.get("require", []):
                required_nodes.append(cls._get_node_with_value(required))
            for forbidden in constraint.get("forbid", []):
                forbidden_nodes.append(cls._get_node_with_value(forbidden))

            constraints.append(
                Constraint.model_validate(
                    {
                        "condition": constraint["if"],
                        "require": required_nodes,
                        "forbid": forbidden_nodes,
                    }
                )
            )

        return cls(steps, ordering, constraints)

    @classmethod
    def _get_node_with_value(cls, node: str | Dict[str, str]) -> Node:
        if isinstance(node, str):
            return Node(id=node)
        else:
            node_id: str = list(node.keys())[0]
            node_value: str = node[node_id]
            return Node(id=node_id, value=node_value)

    def _check_constraint(
        self,
        graph: MultiDiGraph,
        condition: Dict,
        require: List[Node],
        forbid: List[Node],
    ) -> Tuple[bool, Optional[str]]:
        condition_node, condition_value = list(condition.items())[0]
        is_valid: bool = True
        feedbacks: List[str] = []
        if condition_node in graph:
            if (
                condition_value == {}
                or graph.nodes[condition_node]["value"] == condition_value
            ):
                condition_str: str = (
                    f"'{condition_node}' is present"
                    if condition_value == {}
                    else f"'{condition_node}' has value '{condition_value}'"
                )

                # or graph.nodes[n.id].get("value", None) != n.value

                missing_nodes: List[str] = [
                    required_node.id
                    for required_node in require
                    if required_node.id not in graph.nodes
                ]
                if missing_nodes:
                    is_valid = False
                    feedbacks.append(
                        f"- since {condition_str}, required nodes {missing_nodes} are missing."
                    )

                for required_node in require:
                    for node_id in graph.nodes:
                        if (
                            node_id == required_node.id
                            and required_node.value is not None
                        ):
                            if (
                                graph.nodes[node_id].get("value", None)
                                != required_node.value
                            ):
                                is_valid = False
                                feedbacks.append(
                                    f"- since {condition_str}, required value '{required_node.value}' to node '{required_node.id}' is missing."
                                )

                forbidden_nodes: List[str] = [
                    forbidden_node.id
                    for forbidden_node in forbid
                    if forbidden_node.id in graph.nodes and forbidden_node.value is None
                ]

                if forbidden_nodes:
                    is_valid = False
                    feedbacks.append(
                        f"- since {condition_str}, forbidden nodes {forbidden_nodes} are present."
                    )

                for forbidden_node in forbid:
                    for node_id in graph.nodes:
                        if (
                            node_id == forbidden_node.id
                            and forbidden_node.value is not None
                        ):
                            if (
                                graph.nodes[node_id].get("value", None)
                                == forbidden_node.value
                            ):
                                is_valid = False
                                feedbacks.append(
                                    f"- since {condition_str}, forbidden value '{forbidden_node.value}' to node '{forbidden_node.id}' is present."
                                )

        return is_valid, None if is_valid else "\n".join(feedbacks)

    def _validate_allowed_steps(
        self, graph: MultiDiGraph
    ) -> Tuple[bool, Optional[str]]:
        step_ids: Set[str] = set(map(lambda n: n.id, self.steps))
        unknown_nodes = set(graph.nodes) - step_ids

        is_valid: bool = True
        messages: List[str] = []
        if len(unknown_nodes) > 0:
            is_valid = False
            messages.append(
                f"Unknown nodes {list(unknown_nodes)}, admissible nodes are {[s.id for s in self.steps]}."
            )

        graph.remove_nodes_from(unknown_nodes)
        for node_id in graph:
            step: Step = next(filter(lambda n: n.id == node_id, self.steps))
            if step.values is None:
                continue

            node_value: Optional[str] = graph.nodes[node_id].get("value", None)
            if node_value and node_value not in step.values:
                is_valid = False
                messages.append(
                    f"Node '{node_id}' has invalid value '{node_value}', "
                    f"admissible values are {step.values}.",
                )

        feedback = " ".join(messages) if len(messages) > 0 else None
        return is_valid, feedback

    def _validate_mandatory_steps(
        self, graph: MultiDiGraph
    ) -> Tuple[bool, Optional[str]]:
        mandatory_step_ids: List[str] = [
            step.id for step in self.steps if step.mandatory
        ]
        missing_mandatory_steps: List[str] = [
            step_id for step_id in mandatory_step_ids if step_id not in graph.nodes
        ]
        if len(missing_mandatory_steps) > 0:
            return (
                False,
                f"Missing mandatory steps {str(missing_mandatory_steps)}.",
            )

        return True, None

    def _validate_initial_steps(
        self, graph: MultiDiGraph
    ) -> Tuple[bool, Optional[str]]:
        is_valid: bool = True
        messages: List[str] = []
        for step in self.steps:
            if step.id in graph and step.initial:
                if graph.in_degree(step.id) != 0:
                    is_valid = False
                    messages.append(
                        f"Node {step.id} must be initial but has ingoing edges.",
                    )
        feedback = " ".join(messages) if len(messages) > 0 else None
        return is_valid, feedback

    def _validate_terminal_steps(
        self, graph: MultiDiGraph
    ) -> Tuple[bool, Optional[str]]:
        is_valid: bool = True
        messages: List[str] = []
        for step in self.steps:
            if step.id in graph and step.terminal:
                if graph.out_degree(step.id) != 0:
                    is_valid = False
                    messages.append(
                        f"Node {step.id} must be terminal but has outgoing edges.",
                    )
        feedback = " ".join(messages) if len(messages) > 0 else None
        return is_valid, feedback

    def _validate_connectivity(self, graph: MultiDiGraph) -> Tuple[bool, Optional[str]]:
        if not nx.is_weakly_connected(graph):
            return False, "Graph is not connected."
        return True, None

    def _validate_ordering(self, graph: MultiDiGraph) -> Tuple[bool, Optional[str]]:
        is_valid: bool = True
        messages: List[str] = []
        for ordering in self.ordering:
            if (
                ordering.after in graph
                and ordering.before in graph
                and not any(
                    nx.all_simple_paths(
                        graph, source=ordering.before, target=ordering.after
                    )
                )
            ):
                is_valid = False
                messages.append(
                    f"- '{ordering.before}' node must come before '{ordering.after}' node."
                )

        feedback = (
            "Partial ordering violated:\n" + "\n".join(messages)
            if len(messages) > 0
            else None
        )
        return is_valid, feedback

    def _validate_constraints(self, graph: MultiDiGraph) -> Tuple[bool, Optional[str]]:
        is_valid: bool = True
        messages: List[str] = []
        for constraint in self.constraints:
            constraint_valid, message = self._check_constraint(
                graph, constraint.condition, constraint.require, constraint.forbid
            )
            if not constraint_valid and message:
                is_valid = False
                messages.append(message)

        feedback = (
            "Constraints violated:\n" + "\n".join(messages)
            if len(messages) > 0
            else None
        )
        return is_valid, feedback

    def validate(
        self, graph: MultiDiGraph, fail_fast: bool = False
    ) -> Tuple[bool, Optional[str]]:
        checks = [
            self._validate_allowed_steps,
            self._validate_mandatory_steps,
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
            return False, "\n\n".join(overall_feedback)
        return True, None

    def to_natural_language(self) -> str:
        """Convert the specification to a natural language description."""
        description = "Pipeline Specification:\n\nSteps:\n"
        for step in self.steps:
            description += f"- {step.id}: values={step.values}, mandatory={step.mandatory}, initial={step.initial}, terminal={step.terminal}\n"

        description += (
            "\nOrdering Rules.\n"
            "They are valid only if both steps are present in the pipeline.\n"
            "The order is intended to be relative and partial.\n"
        )
        for order in self.ordering:
            description += f"- {order.before} must come before {order.after}\n"

        description += "\nConstraints:\n"
        for constraint in self.constraints:
            condition_list: List[str] = []
            for node_id, node_value in constraint.condition.items():
                if node_value == {}:
                    condition_list.append(f"step '{node_id}' is present")
                else:
                    condition_list.append(
                        f"step '{node_id}' is present and has value '{node_value}'"
                    )
            condition_str = ", and ".join(condition_list)

            require_list: List[str] = []
            for required_node in constraint.require:
                require_list.append(
                    f"step '{required_node.id}' is present and has value '{required_node.value}'"
                )

            description += f"- If {condition_str}, then require {constraint.require} and forbid {constraint.forbid}\n"

        return description
