from typing import List

from automlllm.specification.parsing import SpecificationParser
from automlllm.specification.types import OrderingRule, Constraint, SpecStep


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
        return cls(parsed_spec.steps, parsed_spec.ordering, parsed_spec.constraints, parsed_spec.technical_details)

    def describe_pipeline(self) -> str:
        """Converts the pipeline specification into a human-readable format."""
        nl_spec: str = ""

        step_ids: List[str] = [f"'{step.id}'" for step in self.steps]
        nl_spec += f"The pool of admissible steps for the pipeline consists of: {', '.join(step_ids)}.\n\n"

        nl_spec += "Details:\n"
        for step in self.steps:
            details: List[str] = []
            if step.candidates:
                values_str: str = ", ".join([f"'{c.name}'" for c in step.candidates])
                details.append(f"Allowed values are {values_str}")

            attrs: List[str] = []
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
                condition_node: str
                condition_value: str
                condition_node, condition_value = next(
                    iter(constraint.condition.items())
                )
                if condition_value:
                    cond_str: str = f"'{condition_node}' has value '{condition_value}'"
                else:
                    cond_str = f"'{condition_node}' is present"

                consequences: List[str] = []
                if constraint.require:
                    reqs: List[str] = []
                    for req in constraint.require:
                        if req.content:
                            reqs.append(f"value '{req.content}' for step '{req.name}'")
                        else:
                            reqs.append(f"'{req.name}'")
                    consequences.append(
                        f"{', '.join(reqs)} {'are' if len(reqs) > 1 else 'is'} required"
                    )

                if constraint.forbid:
                    forbids: List[str] = []
                    for forb in constraint.forbid:
                        if forb.content:
                            forbids.append(
                                f"value '{forb.content}' for step '{forb.name}'"
                            )
                        else:
                            forbids.append(f"'{forb.name}'")
                    consequences.append(
                        f"{', '.join(forbids)} {'are' if len(forbids) > 1 else 'is'} forbidden"
                    )

                nl_spec += f"- If {cond_str}, then {' and '.join(consequences)}.\n"

        return nl_spec.strip()

    def describe_technical_details(self) -> str:
        """Converts technical details into a human-readable format."""
        if not self.technical_details:
            return ""
        nl: str = "Technical Details:\n"
        for detail in self.technical_details:
            nl += f"- {detail}\n"
        return nl.strip()
