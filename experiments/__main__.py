from pathlib import Path
from typing import Optional

import fire

from ageml.common import DEFAULT_MODEL_NAME
from ageml.common.utils import safe_filename_part
from experiments import RESULTS_DIR
from experiments.suite import run_suite
from resources import DIR as RESOURCES_DIR


def run_experiments(
    model_name: str = DEFAULT_MODEL_NAME,
    spec_path: Optional[str] = None,
) -> None:
    """Run the full experiments suite (all datasets) with a given LLM backend.

    Can be invoked as:

    ``python -m experiments --model_name=gemini-2.5-flash --spec_path=resources/general-specification.yml``

    ``model_name`` (optional, defaults to ``ageml.app.DEFAULT_MODEL_NAME``) is
    forwarded to ``ageml.app.main`` for every dataset in the suite and
    determines the ``<model_name>`` results folder below.

    ``spec_path`` (optional) is the YAML specification used for every dataset
    in the suite. When omitted, defaults to ``resources/general-specification.yml``.
    A directory is accepted too, and is read as one ``<dataset>.yml``
    specification per dataset, as produced by
    ``python -m experiments.ablation.specifications``.

    Args:
        model_name: Name of the LLM backend used for planning/execution/evaluation
            (e.g. "gemini-2.5-flash"). Defaults to ``ageml.app.DEFAULT_MODEL_NAME``
            when not provided.
        spec_path: Filesystem path to the YAML specification file (or to a
            directory of per-dataset specification files) used for the suite.
            Defaults to ``resources/general-specification.yml`` when not provided.
    """
    run_suite(
        model_name=model_name,
        spec_path=Path(spec_path or RESOURCES_DIR / "general-specification.yml"),
        output_dir=RESULTS_DIR / safe_filename_part(model_name),
    )


if __name__ == "__main__":
    fire.Fire(run_experiments)
