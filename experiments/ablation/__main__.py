"""Run the dataset suite once per specification variant.

    python -m experiments.ablation --model_name=gemini-2.5-flash

Results are written to ``<model_tag>/<variant_id>/results.csv`` under
``experiments/ablation/specifications/results``, with the same schema as
``experiments/results/<model_tag>/results.csv``, so that the ablation can be
compared to the main experiments row by row.

The specification files must have been generated first, with
``python -m experiments.ablation.specifications``.
"""

from pathlib import Path
from typing import List, Optional, Sequence, Union

import fire

from ageml import logger
from ageml.app import DEFAULT_MODEL_NAME
from ageml.common.utils import safe_filename_part
from experiments.ablation.specifications import (
    DIR as SPECIFICATIONS_DIR,
    GENERATED_DIR,
    VARIANTS,
    Variant,
    get_variant,
    specification_path,
)
from experiments.suite import run_suite

#: Where the results of the ablation runs are written.
RESULTS_DIR: Path = SPECIFICATIONS_DIR / "results"


def run_ablation(
    model_name: str = DEFAULT_MODEL_NAME,
    variants: Optional[Union[str, Sequence[str]]] = None,
    generated_dir: Optional[str] = None,
    results_dir: Optional[str] = None,
) -> None:
    """Run the dataset suite once per specification variant.

    Args:
        model_name: Name of the LLM backend used for planning/execution/evaluation
            (e.g. "gemini-2.5-flash"). Defaults to ``ageml.app.DEFAULT_MODEL_NAME``.
        variants: Ids of the variants to run (e.g. ``--variants=general`` or
            ``--variants=poor,general``). Defaults to all of them,
            from the poorest to the richest.
        generated_dir: Where the generated specifications live. Defaults to
            ``experiments/ablation/specifications/generated``.
        results_dir: Where to write the results. Defaults to
            ``experiments/ablation/specifications/results``.
    """
    requested: Sequence[str] = (
        [variants] if isinstance(variants, str) else list(variants or ())
    )
    selected: List[Variant] = [get_variant(v) for v in requested] or list(VARIANTS)
    specifications_dir: Path = Path(generated_dir or GENERATED_DIR)
    output_root: Path = Path(results_dir or RESULTS_DIR) / safe_filename_part(
        model_name
    )

    for variant in selected:
        spec_path: Path = specification_path(variant, specifications_dir)
        if not spec_path.exists():
            raise FileNotFoundError(
                f"No specification for variant '{variant.id}' at {spec_path}. "
                "Run `python -m experiments.ablation.specifications` first."
            )
        logger.info(f"Ablation: running the suite with '{variant.id}' ({spec_path})")
        results: Path = run_suite(
            model_name=model_name,
            spec_path=spec_path,
            output_dir=output_root / variant.id,
        )
        logger.info(f"Ablation: '{variant.id}' results written to {results}")


if __name__ == "__main__":
    fire.Fire(run_ablation)
