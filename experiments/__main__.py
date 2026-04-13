from pathlib import Path
from typing import Dict

import openml
import pandas as pd
from openml.config import get_cache_directory, set_root_cache_directory
from pandas import DataFrame

from automlllm import logger
from automlllm.app import main
from automlllm.specification import Specification
from experiments.results_csv import (
    build_experiment_summary_row,
    save_experiment_summary_to_csv,
)
from resources import DIR as RESOURCES_DIR


def download_openml_datasets(datasets: Dict[str, int], path: Path) -> None:
    set_root_cache_directory(RESOURCES_DIR)
    logger.info("OpenML cache directory: " + get_cache_directory())

    for dataset_name, openml_id in datasets.items():
        dataset = openml.datasets.get_dataset(openml_id)
        X, y, _, _ = dataset.get_data(dataset_format="dataframe")
        df: DataFrame = pd.concat([X, y], axis=1)
        datasets_dir = path
        datasets_dir.mkdir(parents=True, exist_ok=True)
        df.to_csv(datasets_dir / f"{dataset_name}.csv")


if __name__ == "__main__":
    output_dir = Path(__file__).parent / "results"
    spec_path = str(RESOURCES_DIR / "general-specification.yml")
    specification = Specification.parse(Path(spec_path).read_text())

    datasets: Dict[str, Dict[str, int]] = {
        "classification": {
            "wilt": 40983,
            "texture": 40499,
            "madelon": 1485,
            "har": 1478,
            "adult": 1590,
            "mnist_784": 554,
        },
        "regression": {
            "california_housing": 43939,
            "ames_housing": 42165,
            "auto_mpg": 196,
        },
    }
    download_openml_datasets(
        datasets["classification"], RESOURCES_DIR / "datasets" / "classification"
    )
    download_openml_datasets(
        datasets["regression"], RESOURCES_DIR / "datasets" / "regression"
    )

    for kind, datasets_by_kind in datasets.items():
        for dataset_name, openml_id in datasets_by_kind.items():
            dataset_path = str(
                RESOURCES_DIR / "datasets" / kind / f"{dataset_name}.csv"
            )
            metric = "accuracy" if kind == "classification" else "rmse"
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
                problem=kind,
                dataset_df=dataset_df,
                result=result,
                pipeline_budget=specification.pipelines,
                workers=specification.workers,
            )
            output_path = output_dir / "results.csv"
            save_experiment_summary_to_csv(row=row, csv_path=output_path)
