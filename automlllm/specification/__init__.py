from typing import Optional, Dict, List, Tuple, Set, Any

import networkx as nx
import yaml
from networkx import DiGraph
from pydantic import BaseModel, Field, ConfigDict


class Node(BaseModel):
    id: str
    value: Optional[str] = None


class Defaults(BaseModel):
    mandatory: bool = False
    initial: bool = False
    terminal: bool = False


class Candidate(BaseModel):
    name: str
    params: Dict[str, List[Any]] = Field(default_factory=dict)


class StepFields(Defaults):
    candidates: List[Candidate] = Field(default_factory=list)


class Step(StepFields):
    model_config = ConfigDict(extra="forbid")
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
        path: DiGraph,
        condition: Dict,
        required_nodes: List[Node],
        forbidden_nodes: List[Node],
    ) -> Tuple[bool, Optional[str]]:
        condition_node, condition_value = next(iter(condition.items()))
        feedbacks: List[str] = []

        # Condition node is not present, constraint irrelevant
        if condition_node not in path:
            return True, None

        node_value = path.nodes[condition_node].get("value")

        # Condition value mismatch, constraint irrelevant
        if condition_value and node_value != condition_value:
            return True, None

        condition_str = (
            f"'{condition_node}' is present"
            if not condition_value
            else f"'{condition_node}' has value '{condition_value}'"
        )

        for req_node in required_nodes:
            if req_node.id not in path:
                feedbacks.append(
                    f"- since {condition_str}, required node '{req_node.id}' is missing."
                )
                continue

            if req_node.value is not None:
                actual_value = path.nodes[req_node.id].get("value")
                if actual_value != req_node.value:
                    feedbacks.append(
                        f"- since {condition_str}, required value '{req_node.value}' for node '{req_node.id}' is missing."
                    )

        for forb_node in forbidden_nodes:
            if forb_node.id not in path:
                continue

            actual_value = path.nodes[forb_node.id].get("value")

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

    def _validate_allowed_steps(self, path: DiGraph) -> Tuple[bool, Optional[str]]:
        step_ids: Set[str] = set(map(lambda n: n.id, self.steps))
        unknown_nodes = set(path.nodes) - step_ids

        is_valid: bool = True
        messages: List[str] = []
        if len(unknown_nodes) > 0:
            is_valid = False
            messages.append(
                f"Unknown nodes {list(unknown_nodes)}, admissible nodes are {[s.id for s in self.steps]}."
            )

        path.remove_nodes_from(unknown_nodes)
        for node_id in path:
            step: Step = next(filter(lambda n: n.id == node_id, self.steps))
            if step.candidates:
                candidate_names = {c.name for c in step.candidates}
                node_value: Optional[str] = path.nodes[node_id].get("value", None)
                if node_value and node_value not in candidate_names:
                    is_valid = False
                    messages.append(
                        f"Node '{node_id}' has invalid value '{node_value}', "
                        f"admissible values are {sorted(list(candidate_names))}.",
                    )

        feedback = " ".join(messages) if len(messages) > 0 else None
        return is_valid, feedback

    def _validate_mandatory_steps(self, path: DiGraph) -> Tuple[bool, Optional[str]]:
        mandatory_step_ids: List[str] = [
            step.id for step in self.steps if step.mandatory
        ]
        missing_mandatory_steps: List[str] = [
            step_id for step_id in mandatory_step_ids if step_id not in path.nodes
        ]
        if len(missing_mandatory_steps) > 0:
            return (
                False,
                f"Missing mandatory steps {str(missing_mandatory_steps)}.",
            )

        return True, None

    def _validate_initial_steps(self, path: DiGraph) -> Tuple[bool, Optional[str]]:
        is_valid: bool = True
        messages: List[str] = []
        for step in self.steps:
            if step.id in path and step.initial:
                if path.in_degree(step.id) != 0:
                    is_valid = False
                    messages.append(
                        f"Node {step.id} must be initial but has ingoing edges.",
                    )
        feedback = " ".join(messages) if len(messages) > 0 else None
        return is_valid, feedback

    def _validate_terminal_steps(self, path: DiGraph) -> Tuple[bool, Optional[str]]:
        is_valid: bool = True
        messages: List[str] = []
        for step in self.steps:
            if step.id in path and step.terminal:
                if path.out_degree(step.id) != 0:
                    is_valid = False
                    messages.append(
                        f"Node {step.id} must be terminal but has outgoing edges.",
                    )
        feedback = " ".join(messages) if len(messages) > 0 else None
        return is_valid, feedback

    def _validate_ordering(self, path: DiGraph) -> Tuple[bool, Optional[str]]:
        is_valid: bool = True
        messages: List[str] = []
        for ordering in self.ordering:
            if (
                ordering.after in path
                and ordering.before in path
                and (
                    not nx.has_path(path, ordering.before, ordering.after)
                    or nx.has_path(path, ordering.after, ordering.before)
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

    def _validate_constraints(self, graph: DiGraph) -> Tuple[bool, Optional[str]]:
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

    def validate_path(
        self, path: DiGraph, fail_fast: bool = False
    ) -> Tuple[bool, Optional[str]]:
        checks = [
            self._validate_allowed_steps,
            self._validate_mandatory_steps,
            self._validate_initial_steps,
            self._validate_terminal_steps,
            self._validate_ordering,
            self._validate_constraints,
        ]
        path_feedback: List[str] = []
        for check in checks:
            is_valid, message = check(path)
            if not is_valid and message:
                path_feedback.append(message)
                if fail_fast:
                    return False, "\n".join(path_feedback)
        if len(path_feedback) > 0:
            return False, "\n\n".join(path_feedback)

        return True, None

    def validate_graph(
        self, graph: DiGraph, fail_fast: bool = False
    ) -> Tuple[bool, Optional[str]]:
        overall_feedback: List[str] = []
        if not nx.is_weakly_connected(graph):
            if fail_fast:
                return False, "Graph is not connected."
            else:
                overall_feedback.append("Graph is not connected.")

        all_paths: List[DiGraph] = self.enumerate_paths(graph)
        for path in all_paths:
            is_valid, message = self.validate_path(path, fail_fast=fail_fast)
        if not is_valid and message:
            overall_feedback.append(message)
            if fail_fast:
                return False, "\n".join(overall_feedback)

        if len(overall_feedback) > 0:
            return False, "\n\n".join(overall_feedback)
        return True, None

    def enumerate_paths(self, graph: DiGraph) -> List[DiGraph]:
        roots = [n for n, d in graph.in_degree() if d == 0]
        leaves = [n for n, d in graph.out_degree() if d == 0]
        all_paths: List[DiGraph] = []
        for root in roots:
            for leaf in leaves:
                all_paths.extend(
                    DiGraph(graph.subgraph(p).copy())
                    for p in nx.all_simple_paths(graph, root, leaf)
                )
        return all_paths

    def to_natural_language(self) -> str:
        """Convert the specification to a natural language description."""
        nl_spec: str = ""

        step_ids = [f"'{step.id}'" for step in self.steps]
        nl_spec += f"The pool of admissible steps for the pipeline consists of: {', '.join(step_ids)}.\n\n"

        nl_spec += "Details:\n"
        for step in self.steps:
            details: List[str] = []
            if step.candidates:
                values_str = ", ".join([f"'{c.name}'" for c in step.candidates])
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
