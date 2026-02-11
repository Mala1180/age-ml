from typing import List, Optional, Tuple, Set, Dict

import networkx as nx
from networkx import DiGraph

from automlllm.specification import Specification
from automlllm.specification.types import (
    Node,
    Step,
)


class SpecificationValidator:
    def __init__(
        self,
        specification: Specification,
    ):
        self.steps = specification.steps
        self.ordering = specification.ordering
        self.constraints = specification.constraints

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
        is_valid: bool
        message: str | None
        for path in all_paths:
            is_valid, message = self.validate_path(path, fail_fast=fail_fast)
            if not is_valid and message:
                overall_feedback.append(message)
                if fail_fast:
                    return False, "\n".join(overall_feedback)

        if len(overall_feedback) > 0:
            return False, "\n\n".join(overall_feedback)
        return True, None

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

        # Work on a copy to avoid side effects if path is reused (though logical removal implies we ignore them for further checks)
        # However, original logic removed them from path object. Let's stick to original behavior or be careful.
        # The original code did `path.remove_nodes_from(unknown_nodes)`.
        # This acts on the `path` object passed in.
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
