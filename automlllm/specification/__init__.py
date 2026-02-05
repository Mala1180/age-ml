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
        required_nodes: List[Node],
        forbidden_nodes: List[Node],
    ) -> Tuple[bool, Optional[str]]:
        condition_node, condition_value = next(iter(condition.items()))
        feedbacks: List[str] = []

        # Condition node is not present, constraint irrelevant
        if condition_node not in graph:
            return True, None

        node_value = graph.nodes[condition_node].get("value")

        # Condition value mismatch, constraint irrelevant
        if condition_value and node_value != condition_value:
            return True, None

        condition_str = (
            f"'{condition_node}' is present"
            if not condition_value
            else f"'{condition_node}' has value '{condition_value}'"
        )

        for req_node in required_nodes:
            if req_node.id not in graph:
                feedbacks.append(
                    f"- since {condition_str}, required node '{req_node.id}' is missing."
                )
                continue

            if req_node.value is not None:
                actual_value = graph.nodes[req_node.id].get("value")
                if actual_value != req_node.value:
                    feedbacks.append(
                        f"- since {condition_str}, required value '{req_node.value}' for node '{req_node.id}' is missing."
                    )

        for forb_node in forbidden_nodes:
            if forb_node.id not in graph:
                continue

            actual_value = graph.nodes[forb_node.id].get("value")

            if forb_node.value is None:
                feedbacks.append(
                    f"- since {condition_str}, forbidden node '{forb_node.id}' is present."
                )
            elif actual_value == forb_node.value:
                feedbacks.append(
                    f"- since {condition_str}, forbidden value '{forb_node.value}' for node '{forb_node.id}' is present."
                )

        is_valid = not feedbacks
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
        nl_spec: str = ""

        step_ids = [f"'{step.id}'" for step in self.steps]
        nl_spec += f"The pool of admissible steps for the pipeline consists of: {', '.join(step_ids)}.\n\n"

        nl_spec += "Details:\n"
        for step in self.steps:
            details: List[str] = []
            if step.values:
                values_str = ", ".join([f"'{v}'" for v in step.values])
                details.append(f"Allowed values are {values_str}")

            attrs = []
            if step.mandatory:
                attrs.append("mandatory")
            if step.initial:
                attrs.append("initial")
            if step.terminal:
                attrs.append("terminal")

            if attrs:
                details.append(f"It is {' and '.join(attrs)}")

            nl_spec += f"- Step '{step.id}': {'. '.join(details)}.\n"

        if self.ordering:
            nl_spec += (
                "\nPartial Ordering Rules (applied only if both steps are present):\n"
            )
            for order in self.ordering:
                nl_spec += f"- '{order.before}' must precede '{order.after}'.\n"

        if self.constraints:
            nl_spec += "\nConstraints:\n"
            for constraint in self.constraints:
                condition_node, condition_value = next(
                    iter(constraint.condition.items())
                )
                if condition_value:
                    cond_str = f"'{condition_node}' has value '{condition_value}'"
                else:
                    cond_str = f"'{condition_node}' is present"

                consequences: List[str] = []
                if constraint.require:
                    reqs: List[str] = []
                    for req in constraint.require:
                        if req.value:
                            reqs.append(f"value '{req.value}' for node '{req.id}'")
                        else:
                            reqs.append(f"'{req.id}'")
                    consequences.append(
                        f"{', '.join(reqs)} {'are' if len(reqs) > 1 else 'is'} required"
                    )

                if constraint.forbid:
                    forbids: List[str] = []
                    for forb in constraint.forbid:
                        if forb.value:
                            forbids.append(f"value '{forb.value}' for node '{forb.id}'")
                        else:
                            forbids.append(f"'{forb.id}'")
                    consequences.append(
                        f"{', '.join(forbids)} {'are' if len(forbids) > 1 else 'is'} forbidden"
                    )

                nl_spec += f"- If {cond_str}, then {' and '.join(consequences)}.\n"

        return nl_spec.strip()
