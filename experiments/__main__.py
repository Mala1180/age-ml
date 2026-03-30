from pathlib import Path
from typing import Dict

import openml
import pandas as pd
from openml.config import get_cache_directory, set_root_cache_directory
from pandas import DataFrame

from automlllm import logger
from automlllm.app import main
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
            "diabetes": 37,
            "auto_mpg": 196,
        },
    }
    download_openml_datasets(
        datasets["classification"], RESOURCES_DIR / "datasets" / "classification"
    )
    download_openml_datasets(
        datasets["regression"], RESOURCES_DIR / "datasets" / "regression"
    )

    for kind, datasets in datasets.items():
        for dataset_name, openml_id in datasets.items():
            spec_path = str(RESOURCES_DIR / "general-specification.yml")
            dataset_path = str(
                RESOURCES_DIR / "datasets" / kind / f"{dataset_name}.csv"
            )
            metric = "rmse" if kind == "classification" else "accuracy"
            maximize = False if kind == "regression" else True
            results: Dict = main(
                spec_path=spec_path,
                dataset_path=dataset_path,
                validation_metric=metric,
                maximize=maximize,
            )

            # process results...
