"""Size of the planning search space induced by a specification.

The planner enumerates *every* model of the constraint system before sampling
``budgets.pipelines`` of them (``ageml.planning.agent.generate_pipelines`` and
``select_pipelines``), so that size is what the ablation is really varying. It
is recomputed here by brute force, independently of ``z3``, both as a
cross-check of the encoding and to report it in the tables of the paper.
"""

from itertools import product
from typing import Any, Dict, Iterator, List, Mapping, Optional, Set, Tuple

from experiments.ablation.specifications.generator import (
    condition_operator,
    is_dataset_condition,
    mandatory_steps_of,
    operator_of,
    steps_of,
)

#: A pipeline, as the planner sees it: the chosen candidate of every step it
#: includes. Steps that are not in the pipeline are simply absent.
Pipeline = Dict[str, str]


def is_totally_ordered(document: Mapping[str, Any]) -> bool:
    """Whether ``ordering`` fixes the relative position of every pair of steps.

    When it does, each admissible set of steps is exactly one model of the
    solver; when it does not, the solver also enumerates the admissible
    permutations, and the search space grows factorially.
    """
    pairs: Set[Tuple[str, str]] = set()
    for node in document.get("ordering") or []:
        sequence: List[str] = list(node.get("sequence", []))
        pairs |= {(a, b) for i, a in enumerate(sequence) for b in sequence[i + 1 :]}
        if "sequence" not in node:
            pairs.add((node["before"], node["after"]))
    steps: List[str] = list(steps_of(document))
    return all(
        (a, b) in pairs or (b, a) in pairs
        for i, a in enumerate(steps)
        for b in steps[i + 1 :]
    )


def _applies(
    constraint: Mapping[str, Any], pipeline: Pipeline, task: Optional[str]
) -> bool:
    """Whether the condition of ``constraint`` holds for ``pipeline``.

    ``translate_semantic_conditions`` turns every dataset condition the LLM
    validates into an unconditional constraint before solving; the conditions
    of the general specification discriminate classification from regression,
    so the task is enough to predict the outcome.
    """
    if is_dataset_condition(constraint):
        required: Set[str] = {
            operator_of(node)[0] for node in constraint.get("require", [])
        }
        return task is not None and task in required
    step, candidate = condition_operator(constraint)
    if step is None:  # a natural language condition, not encodable in the solver
        return False
    return step in pipeline and (candidate is None or pipeline[step] == candidate)


def _satisfied(constraint: Mapping[str, Any], pipeline: Pipeline) -> bool:
    for node in constraint.get("require", []):
        step, candidate = operator_of(node)
        if step not in pipeline or (candidate and pipeline[step] != candidate):
            return False
    for node in constraint.get("forbid", []):
        step, candidate = operator_of(node)
        if step in pipeline and (candidate is None or pipeline[step] == candidate):
            return False
    return True


def enumerate_pipelines(
    document: Mapping[str, Any], task: Optional[str] = None
) -> Iterator[Pipeline]:
    """Yield every admissible combination of steps and candidates."""
    steps: Dict[str, Tuple[str, ...]] = steps_of(document)
    mandatory: Tuple[str, ...] = mandatory_steps_of(document)
    constraints: List[Mapping[str, Any]] = list(document.get("constraints") or [])
    choices: List[Tuple[Optional[str], ...]] = [
        candidates if step_id in mandatory else (None, *candidates)
        for step_id, candidates in steps.items()
    ]
    for combination in product(*choices):
        pipeline: Pipeline = {
            step_id: candidate
            for step_id, candidate in zip(steps, combination)
            if candidate is not None
        }
        if all(
            not _applies(constraint, pipeline, task) or _satisfied(constraint, pipeline)
            for constraint in constraints
        ):
            yield pipeline


def count_pipelines(document: Mapping[str, Any], task: Optional[str] = None) -> int:
    """Number of pipelines the planner may pick from, the empty one included."""
    return sum(1 for _ in enumerate_pipelines(document, task))
