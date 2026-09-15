import shutil
from pathlib import Path
from typing import Dict, Optional

import fire
import pandas as pd

from ageml.common.utils import copy_out_artifacts, safe_filename_part
from ageml.specification import Specification
from experiments.download_datasets import (
    DEFAULT_OPENML_DATASETS,
    download_all_openml_datasets,
)
from experiments.results_csv import (
    build_experiment_summary_row,
    save_experiment_summary_to_csv,
)
from resources import DIR as RESOURCES_DIR
from ageml.app import DEFAULT_MODEL_NAME, main


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

    Args:
        model_name: Name of the LLM backend used for planning/execution/evaluation
            (e.g. "gemini-2.5-flash"). Defaults to ``ageml.app.DEFAULT_MODEL_NAME``
            when not provided.
        spec_path: Filesystem path to the YAML specification file used for every
            dataset in the suite. Defaults to ``resources/general-specification.yml``
            when not provided.
    """
    spec_path = spec_path or str(RESOURCES_DIR / "general-specification.yml")
    specification = Specification.parse(Path(spec_path).read_text())

    datasets: Dict[str, Dict[str, int]] = DEFAULT_OPENML_DATASETS
    download_all_openml_datasets(datasets)

    for kind, datasets_by_kind in datasets.items():
        for dataset_name, openml_id in datasets_by_kind.items():
            out_dir = Path("out")
            shutil.rmtree(out_dir, ignore_errors=True)

            dataset_path = str(
                RESOURCES_DIR / "datasets" / kind / f"{dataset_name}.csv"
            )
            metric = "balanced_accuracy" if kind == "classification" else "rmse"
            maximize = kind == "classification"
            result: Dict = main(
                spec_path=spec_path,
                dataset_path=dataset_path,
                model_name=model_name,
                validation_metric=metric,
                maximize=maximize,
            )

            model_tag = safe_filename_part(model_name)
            output_dir = Path(__file__).parent / "results" / model_tag
            output_path = output_dir / "results.csv"
            artifacts_path = output_dir / "artifacts"

            dataset_artifacts_dir = artifacts_path / safe_filename_part(dataset_name)
            copy_out_artifacts(out_dir=out_dir, destination=dataset_artifacts_dir)

            dataset_df = pd.read_csv(dataset_path)
            row = build_experiment_summary_row(
                dataset_name=dataset_name,
                openml_id=openml_id,
                problem=kind,
                dataset_df=dataset_df,
                result=result,
                pipeline_budget=specification.pipelines,
                workers=specification.workers,
            )
            save_experiment_summary_to_csv(row=row, csv_path=output_path)


if __name__ == "__main__":
    fire.Fire(run_experiments)
