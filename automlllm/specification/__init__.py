from typing import List

from automlllm.specification.parsing import SpecificationParser
from automlllm.specification.types import Constraint, OrderingRule, SpecStep


class Specification:
    def __init__(
        self,
        steps: List[SpecStep],
        ordering: List[OrderingRule],
        constraints: List[Constraint],
        technical_details: List[str],
    ) -> None:
        self.steps: List[SpecStep] = steps
        self.ordering: List[OrderingRule] = ordering
        self.constraints: List[Constraint] = constraints
        self.technical_details: List[str] = technical_details

    @classmethod
    def parse(cls, spec_yaml: str) -> "Specification":
        parser: SpecificationParser = SpecificationParser(spec_yaml)
        parsed_spec = parser.parse()
        return cls(
            parsed_spec.steps,
            parsed_spec.ordering,
            parsed_spec.constraints,
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
            if step.initial:
                attrs.append("initial")
            if step.terminal:
                attrs.append("terminal")

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
                condition_node: str = constraint.condition.step
                condition_value: str = (
                    constraint.condition.candidate.name
                    if constraint.condition.candidate
                    else ""
                )
                if condition_value:
                    cond_str: str = f"'{condition_node}' has value '{condition_value}'"
                else:
                    cond_str = f"'{condition_node}' is present"

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
