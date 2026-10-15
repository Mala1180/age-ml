"""Run the dataset suite once per specification variant, several times over.

    python -m experiments.ablation --model_name=gemini-3.1-flash-lite-preview

Every (variant, repetition) pair gets its own ``results.csv`` and its own
``artifacts`` tree, under ``experiments/results/<model_tag>/<variant>/run-<n>``,
with the same schema as ``experiments/results/<model_tag>/results.csv``: the
repetitions are what the variance reported in the paper is computed over, and
they are kept apart so that they can be aggregated afterwards.

The specification files must have been generated first, with
``python -m experiments.ablation.specifications``.

See :mod:`experiments.ablation.validation` for the other ablation axis (the
execution agent's semantic/execution self-correction checks).
"""

from pathlib import Path
from typing import List, Optional, Sequence, Tuple, Union

import fire

from ageml.common import DEFAULT_MODEL_NAME
from ageml.common.utils import safe_filename_part
from experiments import RESULTS_DIR
from experiments.ablation.campaign import (
    DEFAULT_REPETITIONS,
    AblationConfig,
    run_campaign,
)
from experiments.ablation.specifications import (
    VARIANTS,
    Variant,
    get_variant,
    specification_path,
)


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
            Defaults to :data:`experiments.ablation.campaign.DEFAULT_REPETITIONS`.
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
            "Run `poetry run poe generate-ablation-specs` first."
        )

    run_campaign(
        model_name=model_name,
        output_root=RESULTS_DIR / safe_filename_part(model_name),
        configs=[
            AblationConfig(id=variant.id, run_suite_kwargs={"spec_path": path})
            for variant, path in specifications
        ],
        repetitions=repetitions,
        axis="specification",
    )


if __name__ == "__main__":
    fire.Fire(run_ablation)
