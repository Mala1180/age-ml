from typing import List

from automlllm.specification.parsing import SpecificationParser
from automlllm.specification.types import (
    Constraint,
    DatasetCondition,
    NaturalLanguageCondition,
    OrderingRule,
    SpecStep,
    StepCondition,
)


class Specification:
    def __init__(
        self,
        max_exploration: int,
        steps: List[SpecStep],
        ordering: List[OrderingRule],
        constraints: List[Constraint],
        semantic_constraints: List[Constraint],
        technical_details: List[str],
    ) -> None:
        self.max_exploration: int = max_exploration
        self.steps: List[SpecStep] = steps
        self.ordering: List[OrderingRule] = ordering
        self.constraints: List[Constraint] = constraints
        self.semantic_constraints: List[Constraint] = semantic_constraints
        self.technical_details: List[str] = technical_details

    @classmethod
    def parse(cls, spec_yaml: str) -> "Specification":
        parser: SpecificationParser = SpecificationParser(spec_yaml)
        parsed_spec = parser.parse()
        return cls(
            parsed_spec.max_exploration,
            parsed_spec.steps,
            parsed_spec.ordering,
            parsed_spec.constraints,
            parsed_spec.semantic_constraints,
            parsed_spec.technical_details,
        )

    def describe_pipeline(self) -> str:
        """Converts the pipeline specification into a human-readable format."""
        lines: List[str] = []
        step_ids: List[str] = [f"'{step.id}'" for step in self.steps]
        lines.append(
            f"The pool of admissible steps for the pipeline consists of: {', '.join(step_ids)}."
        )
        lines.append("")

        lines.append("Details:")
        for step in self.steps:
            lines.append(f"- Step '{step.id}':")
            if step.candidates:
                lines.append("  - Candidates:")
                for candidate in step.candidates:
                    if candidate.params:
                        lines.append(f"    - '{candidate.name}'")
                        lines.append(
                            f"      - with hyperparameters: {candidate.params}"
                        )
                    else:
                        lines.append(f"    - '{candidate.name}'")

            attrs: List[str] = []
            if step.mandatory:
                attrs.append("mandatory")

            if attrs:
                lines.append(f"  - Attributes: {', '.join(attrs)}")

        if self.ordering:
            lines.extend(
                [
                    "",
                    "Partial Ordering Rules (applied only if both steps are present):",
                ]
            )
            for order in self.ordering:
                lines.append(f"- '{order.before}' must precede '{order.after}'.")

        if self.constraints:
            lines.extend(["", "Constraints:"])
            for constraint in self.constraints:
                if isinstance(constraint.condition, DatasetCondition):
                    feature = constraint.condition.feature
                    parts: List[str] = []
                    if feature.role:
                        parts.append(f"role '{feature.role}'")
                    if feature.data_kind:
                        parts.append(f"data kind '{feature.data_kind}'")
                    if feature.is_like:
                        parts.append(f"is like '{feature.is_like}'")
                    cond_str = "dataset feature matches " + ", ".join(parts)
                elif isinstance(constraint.condition, NaturalLanguageCondition):
                    cond_str = (
                        f"natural-language condition: '{constraint.condition.text}'"
                    )
                elif isinstance(constraint.condition, StepCondition):
                    condition_node: str = constraint.condition.step
                    condition_value: str = (
                        constraint.condition.candidate.name
                        if constraint.condition.candidate
                        else ""
                    )
                    if condition_value:
                        cond_str = f"'{condition_node}' has value '{condition_value}'"
                    else:
                        cond_str = f"'{condition_node}' is present"
                else:
                    raise ValueError("Unknown condition type in constraint.")
                consequences: List[str] = []
                if constraint.require:
                    reqs: List[str] = []
                    for req in constraint.require:
                        if req.candidate:
                            reqs.append(
                                f"value '{req.candidate}' for step '{req.name}'"
                            )
                        else:
                            reqs.append(f"'{req.name}'")
                    consequences.append(
                        f"{', '.join(reqs)} {'are' if len(reqs) > 1 else 'is'} required"
                    )

                if constraint.forbid:
                    forbids: List[str] = []
                    for forb in constraint.forbid:
                        if forb.candidate:
                            forbids.append(
                                f"value '{forb.candidate}' for step '{forb.name}'"
                            )
                        else:
                            forbids.append(f"'{forb.name}'")
                    consequences.append(
                        f"{', '.join(forbids)} {'are' if len(forbids) > 1 else 'is'} forbidden"
                    )

                lines.append(f"- If {cond_str}, then {' and '.join(consequences)}.")

        return "\n".join(lines).strip()

    def describe_technical_details(self) -> str:
        """Converts technical details into a human-readable format."""
        if not self.technical_details:
            return ""
        nl: str = "Technical Details:\n"
        for detail in self.technical_details:
            nl += f"- {detail}\n"
        return nl.strip()
