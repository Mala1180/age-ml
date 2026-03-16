from typing import List

from z3 import ModelRef, is_true

from automlllm.common.types import Step
from automlllm.planning.types import PlanningPipeline
from automlllm.specification import Specification


def compare_solutions(solution_a: ModelRef, solution_b: ModelRef) -> bool:
    assignments_a = {
        decl.name(): solution_a[decl].sexpr() for decl in solution_a.decls()
    }
    assignments_b = {
        decl.name(): solution_b[decl].sexpr() for decl in solution_b.decls()
    }
    all_keys = sorted(set(assignments_a) | set(assignments_b))
    differences: List[tuple[str, str, str]] = []

    for key in all_keys:
        value_a = assignments_a.get(key, "<missing>")
        value_b = assignments_b.get(key, "<missing>")
        if value_a != value_b:
            differences.append((key, value_a, value_b))

    if differences:
        print("Different assignments found:")
        for key, value_a, value_b in differences:
            print(f"- {key}: solution_a={value_a}, solution_b={value_b}")
    else:
        print("No differences found.")

    return len(differences) == 0


def convert_solution_to_pipeline(
    solution: ModelRef, specification: Specification
) -> PlanningPipeline:
    model_values = {decl.name(): solution[decl] for decl in solution.decls()}
    selected_steps: List[tuple[int, Step]] = []

    for specification_step in specification.steps:
        step_id: str = specification_step.id
        do_step = model_values.get(f"do_step_{step_id}")
        if do_step is None or not is_true(do_step):
            continue

        step_index_value = model_values.get(f"index_of_step_{step_id}")
        step_index: int = (
            step_index_value.as_long() if step_index_value is not None else 0
        )

        selected_candidate: str = ""
        selected_hyperparameters = {}
        for candidate in specification_step.candidates:
            candidate_value = model_values.get(
                f"implement_{step_id}_as_{candidate.name}"
            )
            if candidate_value is not None and is_true(candidate_value):
                selected_candidate = candidate.name
                selected_hyperparameters = candidate.params
                break

        selected_steps.append(
            (
                step_index,
                Step(
                    name=step_id,
                    candidate=selected_candidate,
                    hyperparameters=selected_hyperparameters,
                ),
            )
        )

    selected_steps.sort(key=lambda item: item[0])
    return PlanningPipeline(steps=[step for _, step in selected_steps])
