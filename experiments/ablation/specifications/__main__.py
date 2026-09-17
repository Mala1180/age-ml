"""(Re)generate the specification variants of the ablation study.

    python -m experiments.ablation.specifications

Writes, under ``experiments/ablation/specifications/generated``:
``poor.yml`` and ``general.yml``, used for every dataset;
``specific/<dataset>.yml``, one per dataset of the suite;
``meta-features.csv``, what the specializations are derived from; and
``manifest.csv``, the ablation matrix.
"""

import csv
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import fire

from ageml import logger
from experiments.ablation.specifications import (
    GENERATED_DIR,
    VARIANTS,
    specification_path,
)
from experiments.ablation.specifications.generator import (
    GeneratedSpecification,
    generate,
)
from experiments.ablation.specifications.meta_features import (
    CLASSIFICATION,
    REGRESSION,
    DatasetMetaFeatures,
    compute_meta_features,
)
from experiments.ablation.specifications.search_space import count_pipelines
from experiments.download_datasets import (
    DEFAULT_OPENML_DATASETS,
    download_all_openml_datasets,
)
from resources import DIR as RESOURCES_DIR

#: The specification every variant is derived from.
BASE_SPECIFICATION: Path = RESOURCES_DIR / "general-specification.yml"

#: Where the CSVs of the suite live, used to compute the meta-features.
DATASETS_DIR: Path = RESOURCES_DIR / "datasets"


def _write_csv(path: Path, rows: Sequence[Dict[str, Any]]) -> Path:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path


def _manifest_row(
    specification: GeneratedSpecification, path: Path, out_dir: Path
) -> Dict[str, Any]:
    document: Dict[str, Any] = specification.document
    steps: Dict[str, Any] = specification.steps
    task: Optional[str] = specification.meta.task if specification.meta else None
    return {
        "variant": specification.variant.id,
        "dataset": specification.meta.name if specification.meta else "",
        "task": task or "",
        "steps": len(steps),
        "step_ids": " ".join(steps),
        "candidates": sum(len(candidates) for candidates in steps.values()),
        "constraints": len(document["constraints"]),
        # The planner turns the dataset conditions it validates into
        # unconditional constraints before solving, so the space it explores
        # depends on the task.
        **{
            f"pipelines_{candidate_task}": count_pipelines(document, candidate_task)
            if task in (None, candidate_task)
            else ""
            for candidate_task in (CLASSIFICATION, REGRESSION)
        },
        "file": str(path.relative_to(out_dir)),
    }


def generate_specifications() -> None:
    """Generate every specification of the ablation study."""
    base: str = BASE_SPECIFICATION.read_text()

    # The dataset-specific variant is a pure function of the meta-features of
    # the CSVs, so they must be there -- exactly as `run_suite` requires them.
    download_all_openml_datasets()

    meta_features: List[DatasetMetaFeatures] = [
        compute_meta_features(
            dataset_path=DATASETS_DIR / task / f"{dataset_name}.csv",
            task=task,
            name=dataset_name,
        )
        for task, datasets in DEFAULT_OPENML_DATASETS.items()
        for dataset_name in datasets
    ]
    for meta in meta_features:
        logger.info(f"Meta-features of '{meta.name}': {meta}")

    manifest: List[Dict[str, Any]] = []
    for variant in VARIANTS:
        destination: Path = specification_path(variant)
        targets: List[Optional[DatasetMetaFeatures]] = (
            list(meta_features) if variant.dataset_specific else [None]
        )
        for target in targets:
            specification: GeneratedSpecification = generate(base, variant, target)
            path: Path = (
                destination / f"{specification.name}.yml"
                if variant.dataset_specific
                else destination
            )
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(specification.to_yaml(), encoding="utf-8")
            manifest.append(_manifest_row(specification, path, GENERATED_DIR))
            logger.info(f"Wrote {path}: {manifest[-1]}")

    logger.info(f"Wrote {_write_csv(GENERATED_DIR / 'manifest.csv', manifest)}")
    logger.info(
        f"Wrote {_write_csv(GENERATED_DIR / 'meta-features.csv', [m.as_row() for m in meta_features])}"
    )


if __name__ == "__main__":
    fire.Fire(generate_specifications)
