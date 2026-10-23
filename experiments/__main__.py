from pathlib import Path

import fire

from ageml.common import DEFAULT_MODEL_NAME
from ageml.common.utils import safe_filename_part
from experiments import RESULTS_DIR
from experiments.suite import run_suite
from resources import DIR as RESOURCES_DIR


def run_experiments(
    model_name: str = DEFAULT_MODEL_NAME,
    spec_path: str | None = None,
    retry_on_semantic_failure: bool = True,
    retry_on_execution_failure: bool = True,
    model_provider: str = "gemini",
    model_base_url: str | None = None,
    model_api_key_env: str | None = None,
    evaluation_protocol: str = "holdout",
    run_seed: int = 42,
    model_seed: int | None = None,
    model_temperature: float | None = None,
    time_budget_seconds: int | None = None,
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
        retry_on_semantic_failure: forwarded to ``ageml.app.main`` for every
            dataset in the suite (default: True).
        retry_on_execution_failure: forwarded to ``ageml.app.main`` for every
            dataset in the suite (default: True).
    """
    run_suite(
        model_name=model_name,
        evaluation_protocol=evaluation_protocol,
        run_seed=run_seed,
        model_seed=model_seed,
        model_temperature=model_temperature,
        time_budget_seconds=time_budget_seconds,
        model_provider=model_provider,
        model_base_url=model_base_url,
        model_api_key_env=model_api_key_env,
        spec_path=Path(spec_path or RESOURCES_DIR / "general-specification.yml"),
        output_dir=RESULTS_DIR / safe_filename_part(model_name),
        retry_on_semantic_failure=retry_on_semantic_failure,
        retry_on_execution_failure=retry_on_execution_failure,
    )


if __name__ == "__main__":
    fire.Fire(run_experiments)
