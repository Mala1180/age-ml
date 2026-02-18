from typing import Callable, List, Optional, Tuple, Set, Dict

from automlllm.common.types import Step
from automlllm.specification import Specification
from automlllm.specification.types import (
    Constraint,
    OrderingRule,
    SpecStep,
)


class SpecificationValidator:
    def __init__(
        self,
        specification: Specification,
    ) -> None:
        self.steps: List[SpecStep] = specification.steps
        self.ordering: List[OrderingRule] = specification.ordering
        self.constraints: List[Constraint] = specification.constraints

    def validate_pipeline(
        self, pipeline: List[Step], fail_fast: bool = False
    ) -> Tuple[bool, Optional[str]]:
        checks: List[Callable[[List[Step]], Tuple[bool, Optional[str]]]] = [
            self._validate_allowed_steps,
            self._validate_mandatory_steps,
            self._validate_initial_steps,
            self._validate_terminal_steps,
            self._validate_ordering,
            self._validate_constraints,
        ]
        feedback: List[str] = []
        for check in checks:
            is_valid: bool
            message: Optional[str]
            is_valid, message = check(pipeline)
            if not is_valid and message:
                feedback.append(message)
                if fail_fast:
                    return False, "\n".join(feedback)
        if len(feedback) > 0:
            return False, "\n\n".join(feedback)

        return True, None

    def _validate_allowed_steps(
        self, pipeline: List[Step]
    ) -> Tuple[bool, Optional[str]]:
        spec_step_ids: Set[str] = {s.id for s in self.steps}
        unknown_names: Set[str] = {step.name for step in pipeline} - spec_step_ids

        is_valid: bool = True
        messages: List[str] = []
        if len(unknown_names) > 0:
            is_valid = False
            messages.append(
                f"Unknown steps {sorted(list(unknown_names))}, admissible steps are {[s.id for s in self.steps]}."
            )

        # Remove unknown steps from pipeline for further checks
        pipeline[:] = [step for step in pipeline if step.name not in unknown_names]

        for step in pipeline:
            spec_step: SpecStep = next(
                filter(lambda s, name=step.name: s.id == name, self.steps)
            )
            if spec_step.candidates:
                candidate_names: Set[str] = {c.name for c in spec_step.candidates}
                if step.content and step.content not in candidate_names:
                    is_valid = False
                    messages.append(
                        f"Step '{step.name}' has invalid value '{step.content}', "
                        f"admissible values are {sorted(list(candidate_names))}.",
                    )

        feedback: Optional[str] = " ".join(messages) if len(messages) > 0 else None
        return is_valid, feedback

    def _validate_mandatory_steps(
        self, pipeline: List[Step]
    ) -> Tuple[bool, Optional[str]]:
        pipeline_names: Set[str] = {step.name for step in pipeline}
        mandatory_step_ids: List[str] = [s.id for s in self.steps if s.mandatory]
        missing_mandatory_steps: List[str] = [
            step_id for step_id in mandatory_step_ids if step_id not in pipeline_names
        ]
        if len(missing_mandatory_steps) > 0:
            return (
                False,
                f"Missing mandatory steps {str(missing_mandatory_steps)}.",
            )

        return True, None

    def _validate_initial_steps(
        self, pipeline: List[Step]
    ) -> Tuple[bool, Optional[str]]:
        is_valid: bool = True
        messages: List[str] = []
        pipeline_names: Set[str] = {step.name for step in pipeline}
        for spec_step in self.steps:
            if spec_step.id in pipeline_names and spec_step.initial:
                if pipeline[0].name != spec_step.id:
                    is_valid = False
                    messages.append(
                        f"Step {spec_step.id} must be initial but is not the first step.",
                    )
        feedback: Optional[str] = " ".join(messages) if len(messages) > 0 else None
        return is_valid, feedback

    def _validate_terminal_steps(
        self, pipeline: List[Step]
    ) -> Tuple[bool, Optional[str]]:
        is_valid: bool = True
        messages: List[str] = []
        pipeline_names: Set[str] = {step.name for step in pipeline}
        for spec_step in self.steps:
            if spec_step.id in pipeline_names and spec_step.terminal:
                if pipeline[-1].name != spec_step.id:
                    is_valid = False
                    messages.append(
                        f"Step {spec_step.id} must be terminal but is not the last step.",
                    )
        feedback: Optional[str] = " ".join(messages) if len(messages) > 0 else None
        return is_valid, feedback

    def _validate_ordering(self, pipeline: List[Step]) -> Tuple[bool, Optional[str]]:
        is_valid: bool = True
        messages: List[str] = []
        pipeline_names: List[str] = [step.name for step in pipeline]
        for ordering in self.ordering:
            if ordering.before in pipeline_names and ordering.after in pipeline_names:
                before_idx: int = pipeline_names.index(ordering.before)
                after_idx: int = pipeline_names.index(ordering.after)
                if before_idx >= after_idx:
                    is_valid = False
                    messages.append(
                        f"- '{ordering.before}' must come before '{ordering.after}'."
                    )

        feedback: Optional[str] = (
            "Partial ordering violated:\n" + "\n".join(messages)
            if len(messages) > 0
            else None
        )
        return is_valid, feedback

    def _validate_constraints(self, pipeline: List[Step]) -> Tuple[bool, Optional[str]]:
        is_valid: bool = True
        messages: List[str] = []
        for constraint in self.constraints:
            constraint_valid: bool
            message: Optional[str]
            constraint_valid, message = self._check_constraint(
                pipeline, constraint.condition, constraint.require, constraint.forbid
            )
            if not constraint_valid and message:
                is_valid = False
                messages.append(message)

        feedback: Optional[str] = (
            "Constraints violated:\n" + "\n".join(messages)
            if len(messages) > 0
            else None
        )
        return is_valid, feedback

    def _check_constraint(
        self,
        pipeline: List[Step],
        condition: Dict,
        required_steps: List[Step],
        forbidden_steps: List[Step],
    ) -> Tuple[bool, Optional[str]]:
        condition_name: str
        condition_value: Optional[str]
        condition_name, condition_value = next(iter(condition.items()))
        feedbacks: List[str] = []

        pipeline_map: Dict[str, Optional[str | Dict]] = {
            step.name: step.content for step in pipeline
        }

        # Condition step is not present, constraint irrelevant
        if condition_name not in pipeline_map:
            return True, None

        step_content: Optional[str | Dict] = pipeline_map[condition_name]

        # Condition value mismatch, constraint irrelevant
        if condition_value and step_content != condition_value:
            return True, None

        condition_str: str = (
            f"'{condition_name}' is present"
            if not condition_value
            else f"'{condition_name}' has value '{condition_value}'"
        )

        for req_step in required_steps:
            if req_step.name not in pipeline_map:
                feedbacks.append(
                    f"- since {condition_str}, required step '{req_step.name}' is missing."
                )
                continue

            if req_step.content is not None:
                actual_content: Optional[str | Dict] = pipeline_map[req_step.name]
                if actual_content != req_step.content:
                    feedbacks.append(
                        f"- since {condition_str}, required value '{req_step.content}' for step '{req_step.name}' is missing."
                    )

        for forb_step in forbidden_steps:
            if forb_step.name not in pipeline_map:
                continue

            actual_content = pipeline_map[forb_step.name]

            if forb_step.content is None:
                feedbacks.append(
                    f"- since {condition_str}, forbidden step '{forb_step.name}' is present."
                )
            elif actual_content == forb_step.content:
                feedbacks.append(
                    f"- since {condition_str}, forbidden value '{forb_step.content}' for step '{forb_step.name}' is present."
                )

        is_valid: bool = not feedbacks
        return is_valid, None if is_valid else "\n".join(feedbacks)
