"""Running the whole dataset suite with a given LLM backend and specification.

Factored out of ``experiments/__main__.py`` so that the ablation study
(:mod:`experiments.ablation`) can reuse the very same loop while varying the
specification per dataset.
"""

import shutil
from pathlib import Path
from typing import Dict, Mapping, Optional, Set

import pandas as pd

from ageml import logger
from ageml.app import main
from ageml.common.utils import copy_out_artifacts, safe_filename_part
from ageml.specification import Specification
from experiments.download_datasets import (
    DEFAULT_OPENML_DATASETS,
    download_all_openml_datasets,
)
from experiments.results_csv import (
    SUMMARY_COLUMNS,
    build_experiment_summary_row,
    save_experiment_summary_to_csv,
)
from resources import DIR as RESOURCES_DIR


def already_recorded(csv_path: Path) -> Set[str]:
    """The datasets an interrupted run of the same suite already wrote.

    Summary rows are *appended*, so re-running a suite over a non-empty
    ``results.csv`` would both redo hours of work and duplicate its rows,
    biasing whatever is later computed over the repetitions. Re-running is
    therefore a resume; delete the directory to start the suite afresh.
    """
    if not csv_path.exists() or csv_path.stat().st_size == 0:
        return set()
    column: str = SUMMARY_COLUMNS["dataset"]
    return set(pd.read_csv(csv_path)[column].astype(str))


def run_suite(
    model_name: str,
    spec_path: Path,
    output_dir: Path,
    datasets: Optional[Mapping[str, Mapping[str, int]]] = None,
) -> Path:
    """Run every dataset of the suite and append one summary row per dataset.

    Args:
        model_name: LLM backend forwarded to :func:`ageml.app.main`.
        spec_path: the specification to use. A directory is read as one
            ``<dataset>.yml`` specification per dataset, as produced by
            ``python -m experiments.ablation.specifications``; a file is used
            for every dataset of the suite.
        output_dir: directory of ``results.csv`` and of the ``artifacts`` tree.
            Datasets already summarized in that ``results.csv`` are skipped, so
            that an interrupted suite is resumed by re-running it.
        datasets: the suite to run, defaulting to
            :data:`experiments.download_datasets.DEFAULT_OPENML_DATASETS`.

    Returns:
        The path of the written ``results.csv``.
    """
    suite: Mapping[str, Mapping[str, int]] = datasets or DEFAULT_OPENML_DATASETS
    download_all_openml_datasets(suite)

    output_path: Path = output_dir / "results.csv"
    recorded: Set[str] = already_recorded(output_path)
    for task, datasets_by_task in suite.items():
        for dataset_name, openml_id in datasets_by_task.items():
            if dataset_name in recorded:
                logger.info(f"Skipping '{dataset_name}': already in {output_path}")
                continue

            out_dir = Path("out")
            shutil.rmtree(out_dir, ignore_errors=True)

            specification: Path = (
                spec_path / f"{dataset_name}.yml" if spec_path.is_dir() else spec_path
            )
            dataset_path = str(
                RESOURCES_DIR / "datasets" / task / f"{dataset_name}.csv"
            )
            result: Dict = main(
                spec_path=str(specification),
                dataset_path=dataset_path,
                model_name=model_name,
                validation_metric="balanced_accuracy"
                if task == "classification"
                else "rmse",
                maximize=task == "classification",
            )

            copy_out_artifacts(
                out_dir=out_dir,
                destination=output_dir / "artifacts" / safe_filename_part(dataset_name),
            )

            parsed: Specification = Specification.parse(specification.read_text())
            row = build_experiment_summary_row(
                dataset_name=dataset_name,
                openml_id=openml_id,
                problem=task,
                dataset_df=pd.read_csv(dataset_path),
                result=result,
                pipeline_budget=parsed.pipelines,
                workers=parsed.workers,
            )
            save_experiment_summary_to_csv(row=row, csv_path=output_path)
    return output_path
