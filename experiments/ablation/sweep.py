"""Shared bookkeeping for ablation studies: run the suite once per config, repeated.

An ablation study varies one axis of the framework's inputs (e.g. the
specification, in :mod:`experiments.ablation`, or the execution agent's
self-correction checks, in :mod:`experiments.ablation.validation`) across a
handful of named configs, repeating each one to measure variance. This module
factors out that shared repetition/config loop so each axis only has to
describe its own configs.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Mapping, Sequence, Union

from ageml import logger
from experiments.suite import run_suite

#: How many times each config is run, to measure the variance of the results.
DEFAULT_REPETITIONS: int = 5


def repetition_ids(repetitions: Union[int, Sequence[int]]) -> List[int]:
    """The ids of the repetitions to run.

    ``--repetitions=5`` runs the repetitions 1 to 5, whereas
    ``--repetitions=3,4,5`` runs exactly those three -- which is how an
    interrupted sweep is resumed, or spread over several machines.
    """
    if isinstance(repetitions, int):
        return list(range(1, repetitions + 1))
    return [int(repetition) for repetition in repetitions]


@dataclass(frozen=True)
class AblationConfig:
    """One point of an ablation axis: an id, and the ``run_suite`` kwargs that vary for it."""

    id: str
    run_suite_kwargs: Mapping[str, Any]


def run_sweep(
    model_name: str,
    output_root: Path,
    configs: Sequence[AblationConfig],
    repetitions: Union[int, Sequence[int]],
    axis: str,
) -> None:
    """Run the dataset suite once per (config, repetition) pair.

    Every pair gets its own ``results.csv`` and its own ``artifacts`` tree,
    under ``<output_root>/<config.id>/run-<n>``: the repetitions are what the
    variance reported in the paper is computed over, and they are kept apart
    so that they can be aggregated afterwards.

    Args:
        model_name: LLM backend forwarded to :func:`ageml.app.main`.
        output_root: parent of every config's ``<config.id>/run-<n>`` tree.
        configs: the points of the ablation axis to run.
        repetitions: how many times to run each config (``--repetitions=5``),
            or the exact ids of the repetitions to run (``--repetitions=4,5``).
        axis: short label for this ablation axis, used only in log messages
            (e.g. ``"specification"``, ``"validation"``).
    """
    for repetition in repetition_ids(repetitions):
        for config in configs:
            logger.info(
                f"Ablation ({axis}): running the suite with '{config.id}', "
                f"repetition {repetition}"
            )
            results: Path = run_suite(
                model_name=model_name,
                output_dir=output_root / config.id / f"run-{repetition}",
                **config.run_suite_kwargs,
            )
            logger.info(
                f"Ablation ({axis}): '{config.id}' repetition {repetition} "
                f"results written to {results}"
            )
