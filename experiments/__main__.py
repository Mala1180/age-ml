import shutil
from pathlib import Path
from typing import Dict

import pandas as pd

from ageml.app import main
from ageml.common.model import model_name
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

if __name__ == "__main__":
    model_tag = safe_filename_part(model_name)
    output_dir = Path(__file__).parent / "results" / model_tag
    output_path = output_dir / "results.csv"
    artifacts_path = output_dir / "artifacts"
    spec_path = str(RESOURCES_DIR / "general-specification.yml")
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
                validation_metric=metric,
                maximize=maximize,
            )
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
