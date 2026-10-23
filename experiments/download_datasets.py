import json
from collections.abc import Mapping
from pathlib import Path

import fire
import openml
import pandas as pd
from openml.config import get_cache_directory, set_root_cache_directory
from pandas import DataFrame

from ageml import logger
from resources import DIR as RESOURCES_DIR

DEFAULT_OPENML_DATASETS: dict[str, dict[str, int]] = {
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


def download_openml_datasets(datasets: Mapping[str, int], path: Path) -> None:
    set_root_cache_directory(RESOURCES_DIR)
    logger.info("OpenML cache directory: " + get_cache_directory())

    path.mkdir(parents=True, exist_ok=True)
    for dataset_name, openml_id in datasets.items():
        dataset = openml.datasets.get_dataset(openml_id)
        target = dataset.default_target_attribute
        if not target or "," in target:
            raise ValueError(
                f"Dataset {dataset_name} requires one explicit OpenML target"
            )
        X, y, _, _ = dataset.get_data(dataset_format="dataframe", target=target)
        df: DataFrame = pd.concat([X, y], axis=1)
        df.to_csv(path / f"{dataset_name}.csv", index=False)
        (path / f"{dataset_name}.metadata.json").write_text(
            json.dumps(
                {
                    "target_column": y.name,
                    "task": path.name,
                    "openml_id": openml_id,
                    "dataset_version": dataset.version,
                    "preparation": "OpenML get_data; all rows; no filtering",
                }
            )
        )


def download_all_openml_datasets(
    datasets_by_kind: Mapping[str, Mapping[str, int]] | None = None,
    base_dir: Path = RESOURCES_DIR / "datasets",
) -> None:
    selected_datasets = datasets_by_kind or DEFAULT_OPENML_DATASETS
    for kind, datasets in selected_datasets.items():
        download_openml_datasets(datasets, base_dir / kind)


def download_openml_datasets_cli(
    base_dir: str = str(RESOURCES_DIR / "datasets"),
) -> None:
    download_all_openml_datasets(DEFAULT_OPENML_DATASETS, Path(base_dir))


if __name__ == "__main__":
    fire.Fire(download_openml_datasets_cli)
