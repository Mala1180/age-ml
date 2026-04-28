from typing import Iterator

from z3 import (
    Solver,
    ModelRef,
    And,
    AtMost,
    Or,
    Implies,
    Not,
    sat,
    Int,
    Sum,
    If,
    ArithRef,
    BoolRef,
    Bool,
    ExprRef,
    BoolVal,
)

from ageml.specification import Specification
from ageml.specification.types import (
    DatasetCondition,
    NaturalLanguageCondition,
    TrueCondition,
    StepCondition,
)


class Variables:
    def __init__(self):
        self.__variables = dict()

    def add(self, variable: ExprRef) -> None:
        self.__variables[str(variable)] = variable

    def __getitem__(self, key) -> ExprRef:
        return self.__variables[key]

    def __iter__(self) -> Iterator[ExprRef]:
        return iter(self.__variables.values())

    def items(self):
        return self.__variables.items()

    def __len__(self):
        return len(self.__variables)

    def int(self, name) -> ArithRef:
        variable = Int(name)
        self.add(variable)
        return variable

    def bool(self, name) -> BoolRef:
        variable = Bool(name)
        self.add(variable)
        return variable

    def with_name(self, name):
        for variable_name, variable in self.__variables.items():
            if variable_name.startswith(name):
                yield variable


def create_solver(specification: Specification) -> Solver:
    solver = Solver()
    variables = Variables()
    add_steps_to_solver(solver, variables, specification)
    add_orderings_to_solver(solver, variables, specification)
    add_constraints_to_solver(solver, variables, specification)
    return solver


def add_steps_to_solver(
    solver: Solver, variables: Variables, specification: Specification
) -> None:
    for i, step in enumerate(specification.steps):
        step_index = variables.int(f"index_of_step_{step.id}")
        # if step_index != 0, then all subsequent steps must have different indices to ensure a valid ordering of steps in the pipeline.
        for step_j in specification.steps[i + 1 :]:
            step_index_j = variables.int(f"index_of_step_{step_j.id}")
            solver.add(
                Implies(
                    And(step_index != 0, step_index_j != 0),
                    step_index != step_index_j,
                )
            )

        step_index = variables.int(f"index_of_step_{step.id}")
        do_step = variables.bool(f"do_step_{step.id}")
        # index_lt_than_num_steps = step_index < len(specification.steps)
        index_lte_sum_of_do_steps = step_index <= Sum(
            [
                If(variables.bool(f"do_step_{step.id}"), 1, 0)
                for step in specification.steps
            ]
        )
        solver.add(Implies(do_step, And(step_index > 0, index_lte_sum_of_do_steps)))

        # Canonicalize skipped steps to avoid duplicate models that only differ on
        # irrelevant index values for steps that are not part of the pipeline.
        solver.add(Implies(Not(do_step), step_index == 0))

        for candidate in step.candidates:
            variables.bool(f"implement_{step.id}_as_{candidate.name}")

        all_candidates = tuple(variables.with_name(f"implement_{step.id}_as_"))
        solver.add(AtMost(*all_candidates, 1))
        solver.add(do_step == Or(*all_candidates))
        if step.mandatory:
            solver.add(variables[f"do_step_{step.id}"])


def add_orderings_to_solver(
    solver: Solver, variables: Variables, specification: Specification
) -> None:
    for ordering in specification.ordering:
        solver.add(
            Implies(
                And(
                    variables[f"do_step_{ordering.before}"],
                    variables[f"do_step_{ordering.after}"],
                ),
                variables[f"index_of_step_{ordering.before}"]  # type: ignore
                < variables[f"index_of_step_{ordering.after}"],
            )
        )


def add_constraints_to_solver(
    solver: Solver, variables: Variables, specification: Specification
) -> None:
    for constraint in specification.constraints:
        if isinstance(
            constraint.condition, (DatasetCondition, NaturalLanguageCondition)
        ):
            # Non-step constraints cannot be encoded without external metadata/context.
            continue

        if isinstance(constraint.condition, StepCondition):
            conditions = [variables[f"do_step_{constraint.condition.step}"]]
            if constraint.condition.candidate:
                candidate_name: str = constraint.condition.candidate.name
                conditions.append(
                    And(
                        variables[f"do_step_{constraint.condition.step}"],
                        variables[
                            f"implement_{constraint.condition.step}_as_{candidate_name}"
                        ],
                    )
                )
        elif isinstance(constraint.condition, TrueCondition):
            conditions = [BoolVal(True)]
        else:
            raise ValueError(
                f"Unsupported condition type: {type(constraint.condition)}"
            )

        effects = []
        for forbidden_step in constraint.forbid:
            effects.append(Not(variables[f"do_step_{forbidden_step.name}"]))

        for required_step in constraint.require:
            effects.append(variables[f"do_step_{required_step.name}"])

        if len(effects) == 0:
            raise ValueError(f"{constraint} has no effects, which is not supported.")

        condition = And(*conditions) if len(conditions) > 1 else conditions[0]
        effects = And(*effects) if len(effects) > 1 else effects[0]
        solver.add(Implies(condition, effects))


def enumerate_solutions(solver: Solver) -> Iterator[ModelRef]:
    while solver.check() == sat:
        model = solver.model()
        yield model
        # Add a constraint to block the current solution and find the next one
        different_assignments = [decl() != model[decl] for decl in model.decls()]
        solver.add(Or(*different_assignments))
