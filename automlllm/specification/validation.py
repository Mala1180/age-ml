from typing import List, Optional, Tuple, Set, Dict

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

    def validate_pipeline(
        self, pipeline: List[Node], fail_fast: bool = False
    ) -> Tuple[bool, Optional[str]]:
        checks = [
            self._validate_allowed_steps,
            self._validate_mandatory_steps,
            self._validate_initial_steps,
            self._validate_terminal_steps,
            self._validate_ordering,
            self._validate_constraints,
        ]
        feedback: List[str] = []
        for check in checks:
            is_valid, message = check(pipeline)
            if not is_valid and message:
                feedback.append(message)
                if fail_fast:
                    return False, "\n".join(feedback)
        if len(feedback) > 0:
            return False, "\n\n".join(feedback)

        return True, None

    def _validate_allowed_steps(
        self, pipeline: List[Node]
    ) -> Tuple[bool, Optional[str]]:
        step_ids: Set[str] = set(map(lambda n: n.id, self.steps))
        unknown_ids = {node.id for node in pipeline} - step_ids

        is_valid: bool = True
        messages: List[str] = []
        if len(unknown_ids) > 0:
            is_valid = False
            messages.append(
                f"Unknown nodes {sorted(list(unknown_ids))}, admissible nodes are {[s.id for s in self.steps]}."
            )

        # Remove unknown nodes from pipeline for further checks
        pipeline[:] = [node for node in pipeline if node.id not in unknown_ids]

        for node in pipeline:
            step: Step = next(filter(lambda n, nid=node.id: n.id == nid, self.steps))
            if step.candidates:
                candidate_names = {c.name for c in step.candidates}
                if node.value and node.value not in candidate_names:
                    is_valid = False
                    messages.append(
                        f"Node '{node.id}' has invalid value '{node.value}', "
                        f"admissible values are {sorted(list(candidate_names))}.",
                    )

        feedback = " ".join(messages) if len(messages) > 0 else None
        return is_valid, feedback

    def _validate_mandatory_steps(
        self, pipeline: List[Node]
    ) -> Tuple[bool, Optional[str]]:
        pipeline_ids = {node.id for node in pipeline}
        mandatory_step_ids: List[str] = [
            step.id for step in self.steps if step.mandatory
        ]
        missing_mandatory_steps: List[str] = [
            step_id for step_id in mandatory_step_ids if step_id not in pipeline_ids
        ]
        if len(missing_mandatory_steps) > 0:
            return (
                False,
                f"Missing mandatory steps {str(missing_mandatory_steps)}.",
            )

        return True, None

    def _validate_initial_steps(
        self, pipeline: List[Node]
    ) -> Tuple[bool, Optional[str]]:
        is_valid: bool = True
        messages: List[str] = []
        pipeline_ids = {node.id for node in pipeline}
        for step in self.steps:
            if step.id in pipeline_ids and step.initial:
                if pipeline[0].id != step.id:
                    is_valid = False
                    messages.append(
                        f"Node {step.id} must be initial but is not the first step.",
                    )
        feedback = " ".join(messages) if len(messages) > 0 else None
        return is_valid, feedback

    def _validate_terminal_steps(
        self, pipeline: List[Node]
    ) -> Tuple[bool, Optional[str]]:
        is_valid: bool = True
        messages: List[str] = []
        pipeline_ids = {node.id for node in pipeline}
        for step in self.steps:
            if step.id in pipeline_ids and step.terminal:
                if pipeline[-1].id != step.id:
                    is_valid = False
                    messages.append(
                        f"Node {step.id} must be terminal but is not the last step.",
                    )
        feedback = " ".join(messages) if len(messages) > 0 else None
        return is_valid, feedback

    def _validate_ordering(self, pipeline: List[Node]) -> Tuple[bool, Optional[str]]:
        is_valid: bool = True
        messages: List[str] = []
        pipeline_ids = [node.id for node in pipeline]
        for ordering in self.ordering:
            if ordering.before in pipeline_ids and ordering.after in pipeline_ids:
                before_idx = pipeline_ids.index(ordering.before)
                after_idx = pipeline_ids.index(ordering.after)
                if before_idx >= after_idx:
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

    def _validate_constraints(self, pipeline: List[Node]) -> Tuple[bool, Optional[str]]:
        is_valid: bool = True
        messages: List[str] = []
        for constraint in self.constraints:
            constraint_valid, message = self._check_constraint(
                pipeline, constraint.condition, constraint.require, constraint.forbid
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
        pipeline: List[Node],
        condition: Dict,
        required_nodes: List[Node],
        forbidden_nodes: List[Node],
    ) -> Tuple[bool, Optional[str]]:
        condition_node, condition_value = next(iter(condition.items()))
        feedbacks: List[str] = []

        pipeline_map: Dict[str, Optional[str]] = {
            node.id: node.value for node in pipeline
        }

        # Condition node is not present, constraint irrelevant
        if condition_node not in pipeline_map:
            return True, None

        node_value = pipeline_map[condition_node]

        # Condition value mismatch, constraint irrelevant
        if condition_value and node_value != condition_value:
            return True, None

        condition_str = (
            f"'{condition_node}' is present"
            if not condition_value
            else f"'{condition_node}' has value '{condition_value}'"
        )

        for req_node in required_nodes:
            if req_node.id not in pipeline_map:
                feedbacks.append(
                    f"- since {condition_str}, required node '{req_node.id}' is missing."
                )
                continue

            if req_node.value is not None:
                actual_value = pipeline_map[req_node.id]
                if actual_value != req_node.value:
                    feedbacks.append(
                        f"- since {condition_str}, required value '{req_node.value}' for node '{req_node.id}' is missing."
                    )

        for forb_node in forbidden_nodes:
            if forb_node.id not in pipeline_map:
                continue

            actual_value = pipeline_map[forb_node.id]

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
