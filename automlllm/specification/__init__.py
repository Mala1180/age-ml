from typing import List

from automlllm.specification.parsing import SpecificationParser
from automlllm.specification.types import (
    Budgets,
    Constraint,
    OrderingRule,
    SpecStep,
)


class Specification:
    def __init__(
        self,
        budgets: Budgets,
        steps: List[SpecStep],
        ordering: List[OrderingRule],
        constraints: List[Constraint],
        semantic_constraints: List[Constraint],
        technical_details: List[str],
    ) -> None:
        self.budgets: Budgets = budgets
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
            parsed_spec.budgets,
            parsed_spec.steps,
            parsed_spec.ordering,
            parsed_spec.constraints,
            parsed_spec.semantic_constraints,
            parsed_spec.technical_details,
        )

    @property
    def pipelines(self) -> int:
        return self.budgets.pipelines

    @property
    def workers(self) -> int:
        return self.budgets.workers

    @property
    def time_budget_minutes(self) -> int:
        return self.budgets.time.total_seconds // 60

    @property
    def time_budget_seconds(self) -> int:
        return self.budgets.time.total_seconds

    def describe_technical_details(self) -> str:
        """Converts technical details into a human-readable format."""
        if not self.technical_details:
            return ""
        nl: str = "Technical Details:\n"
        for detail in self.technical_details:
            nl += f"- {detail}\n"
        return nl.strip()
