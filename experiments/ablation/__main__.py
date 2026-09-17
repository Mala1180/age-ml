"""Run the dataset suite once per specification variant, several times over.

    python -m experiments.ablation --model_name=gemini-3.1-flash-lite-preview

Every (variant, repetition) pair gets its own ``results.csv`` and its own
``artifacts`` tree, under ``experiments/results/<model_tag>/<variant>/run-<n>``,
with the same schema as ``experiments/results/<model_tag>/results.csv``: the
repetitions are what the variance reported in the paper is computed over, and
they are kept apart so that they can be aggregated afterwards.

The specification files must have been generated first, with
``python -m experiments.ablation.specifications``.
"""

from pathlib import Path
from typing import List, Optional, Sequence, Tuple, Union

import fire

from ageml import logger
from ageml.common import DEFAULT_MODEL_NAME
from ageml.common.utils import safe_filename_part
from experiments import RESULTS_DIR
from experiments.ablation.specifications import (
    VARIANTS,
    Variant,
    get_variant,
    specification_path,
)
from experiments.suite import run_suite

#: How many times each variant is run, to measure the variance of the results.
DEFAULT_REPETITIONS: int = 5


def repetition_ids(repetitions: Union[int, Sequence[int]]) -> List[int]:
    """The ids of the repetitions to run.

    ``--repetitions=5`` runs the repetitions 1 to 5, whereas
    ``--repetitions=3,4,5`` runs exactly those three -- which is how an
    interrupted campaign is resumed, or spread over several machines.
    """
    if isinstance(repetitions, int):
        return list(range(1, repetitions + 1))
    return [int(repetition) for repetition in repetitions]


def run_ablation(
    model_name: str = DEFAULT_MODEL_NAME,
    variants: Optional[Union[str, Sequence[str]]] = None,
    repetitions: Union[int, Sequence[int]] = DEFAULT_REPETITIONS,
) -> None:
    """Run the dataset suite once per specification variant, once per repetition.

    Repetitions are the outer loop: after the first one, every variant already
    has a complete -- if not yet significant -- set of results.

    Args:
        model_name: Name of the LLM backend used for planning/execution/evaluation
            (e.g. "gemini-3.1-flash-lite-preview"). Defaults to
            ``ageml.common.DEFAULT_MODEL_NAME``.
        variants: Ids of the variants to run (e.g. ``--variants=general`` or
            ``--variants=poor,general``). Defaults to all of them,
            from the poorest to the richest.
        repetitions: How many times to run each variant (``--repetitions=5``),
            or the exact ids of the repetitions to run (``--repetitions=4,5``).
            Defaults to :data:`DEFAULT_REPETITIONS`.
    """
    requested: Sequence[str] = (
        [variants] if isinstance(variants, str) else list(variants or ())
    )
    selected: List[Variant] = [get_variant(v) for v in requested] or list(VARIANTS)
    specifications: List[Tuple[Variant, Path]] = [
        (variant, specification_path(variant)) for variant in selected
    ]
    # Upfront, rather than when the campaign is already hours in.
    missing: List[str] = [str(path) for _, path in specifications if not path.exists()]
    if missing:
        raise FileNotFoundError(
            f"No specification at {', '.join(missing)}. "
            "Run `poetry run poe ablation-specs` first."
        )

    output_root: Path = RESULTS_DIR / safe_filename_part(model_name)
    for repetition in repetition_ids(repetitions):
        for variant, spec_path in specifications:
            logger.info(
                f"Ablation: running the suite with '{variant.id}' ({spec_path}), "
                f"repetition {repetition}"
            )
            results: Path = run_suite(
                model_name=model_name,
                spec_path=spec_path,
                output_dir=output_root / variant.id / f"run-{repetition}",
            )
            logger.info(
                f"Ablation: '{variant.id}' repetition {repetition} "
                f"results written to {results}"
            )


if __name__ == "__main__":
    fire.Fire(run_ablation)
