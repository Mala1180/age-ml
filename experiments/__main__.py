from pathlib import Path
from typing import Dict

import pandas as pd

from automlllm.app import main
from automlllm.common.model import model_name
from automlllm.specification import Specification
from experiments.download_datasets import (
    DEFAULT_OPENML_DATASETS,
    download_all_openml_datasets,
)
from experiments.results_csv import (
    build_experiment_summary_row,
    save_experiment_summary_to_csv,
)
from resources import DIR as RESOURCES_DIR


def _safe_filename_part(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in value)


if __name__ == "__main__":
    output_dir = Path(__file__).parent / "results"
    model_tag = _safe_filename_part(model_name)
    output_path = output_dir / f"results_{model_tag}.csv"
    spec_path = str(RESOURCES_DIR / "general-specification.yml")
    specification = Specification.parse(Path(spec_path).read_text())

    datasets: Dict[str, Dict[str, int]] = DEFAULT_OPENML_DATASETS
    download_all_openml_datasets(datasets)

    for kind, datasets_by_kind in datasets.items():
        for dataset_name, openml_id in datasets_by_kind.items():
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
