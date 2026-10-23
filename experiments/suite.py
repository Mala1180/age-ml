"""Running the whole dataset suite with a given LLM backend and specification.

Factored out of ``experiments/__main__.py`` so that the ablation study
(:mod:`experiments.ablation`) can reuse the very same loop while varying the
specification per dataset.
"""

import json
import shutil
from collections.abc import Mapping
from pathlib import Path

import pandas as pd

from ageml import logger
from ageml.app import main
from ageml.common.llm_config import resolve_llm_config
from ageml.common.utils import copy_out_artifacts, safe_filename_part, save_file
from ageml.protocol import VERSION, digest, file_hash, prepare
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


def already_recorded(csv_path: Path) -> set[str]:
    """The datasets an interrupted run of the same suite already wrote.

    Summary rows are *appended*, so re-running a suite over a non-empty
    ``results.csv`` would both redo hours of work and duplicate its rows,
    biasing whatever is later computed over the repetitions. Re-running is
    therefore a resume; delete the directory to start the suite afresh.
    """
    if not csv_path.exists() or csv_path.stat().st_size == 0:
        return set()
    frame = pd.read_csv(csv_path)
    if "Resume Identity" not in frame or "Protocol Version" not in frame:
        return set()
    return set(
        frame.loc[frame["Protocol Version"] == VERSION, "Resume Identity"].astype(str)
    )


def run_suite(
    model_name: str,
    spec_path: Path,
    output_dir: Path,
    datasets: Mapping[str, Mapping[str, int]] | None = None,
    retry_on_semantic_failure: bool = True,
    retry_on_execution_failure: bool = True,
    use_csp: bool = True,
    model_provider: str = "gemini",
    model_base_url: str | None = None,
    model_api_key_env: str | None = None,
    split_manifests: Mapping[str, str] | None = None,
    split_seed: int = 42,
    download_datasets: bool = True,
    evaluation_protocol: str | None = None,
    run_seed: int = 42,
    model_seed: int | None = None,
    model_temperature: float | None = None,
    time_budget_seconds: int | None = None,
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
        retry_on_semantic_failure: forwarded to :func:`ageml.app.main`.
        retry_on_execution_failure: forwarded to :func:`ageml.app.main`.
        use_csp: forwarded to :func:`ageml.app.main`.

    Returns:
        The path of the written ``results.csv``.
    """
    llm_config = resolve_llm_config(
        model_name,
        model_provider,
        model_base_url,
        model_api_key_env,
        model_seed,
        model_temperature,
    )
    suite: Mapping[str, Mapping[str, int]] = datasets or DEFAULT_OPENML_DATASETS
    if download_datasets:
        download_all_openml_datasets(suite)

    output_dir = output_dir / VERSION
    output_path: Path = output_dir / "results.csv"
    recorded: set[str] = already_recorded(output_path)
    for task, datasets_by_task in suite.items():
        for dataset_name, openml_id in datasets_by_task.items():
            out_dir = Path("out")
            shutil.rmtree(out_dir, ignore_errors=True)

            specification: Path = (
                spec_path / f"{dataset_name}.yml" if spec_path.is_dir() else spec_path
            )
            dataset_path = str(
                RESOURCES_DIR / "datasets" / task / f"{dataset_name}.csv"
            )
            metadata = json.loads(
                Path(dataset_path).with_suffix(".metadata.json").read_text()
            )
            target = metadata["target_column"]
            if metadata["task"] != task:
                raise ValueError("Dataset manifest task mismatch")
            imported = (
                None if split_manifests is None else split_manifests[dataset_name]
            )
            _, frozen = prepare(
                dataset_path,
                target,
                task,
                seed=split_seed,
                manifest=imported,
                evaluation_protocol=evaluation_protocol,
            )
            identity = digest(
                {
                    "protocol": VERSION,
                    "run_seed": run_seed,
                    "time_budget_seconds": time_budget_seconds,
                    "source": file_hash(dataset_path),
                    "split": frozen["split_identity"],
                    "specification": file_hash(specification),
                    "model": llm_config.public_dict(),
                    "code": digest(
                        {
                            str(p.relative_to(Path(__file__).parents[1])): file_hash(p)
                            for p in sorted(
                                (Path(__file__).parents[1] / "ageml").rglob("*.py")
                            )
                        }
                    ),
                    "repetition": str(output_dir.resolve()),
                    "retry_on_semantic_failure": retry_on_semantic_failure,
                    "retry_on_execution_failure": retry_on_execution_failure,
                    "use_csp": use_csp,
                }
            )
            if identity in recorded:
                logger.info(f"Skipping completed identity for {dataset_name}")
                continue
            protocol_dir = (
                output_dir / "protocol" / safe_filename_part(dataset_name) / identity
            )
            # A partial prior run remains immutable; retries use a distinct attempt.
            if (protocol_dir / "protocol.json").exists():
                import uuid

                protocol_dir = protocol_dir / uuid.uuid4().hex
            result: dict = main(
                spec_path=str(specification),
                dataset_path=dataset_path,
                model_name=model_name,
                evaluation_protocol=evaluation_protocol,
                run_seed=run_seed,
                model_seed=model_seed,
                model_temperature=model_temperature,
                time_budget_seconds=time_budget_seconds,
                model_provider=model_provider,
                model_base_url=model_base_url,
                model_api_key_env=model_api_key_env,
                target_column=target,
                split_seed=split_seed,
                split_manifest=imported,
                task=task,
                protocol_output_dir=str(protocol_dir),
                validation_metric="balanced_accuracy"
                if task == "classification"
                else "rmse",
                maximize=task == "classification",
                retry_on_semantic_failure=retry_on_semantic_failure,
                retry_on_execution_failure=retry_on_execution_failure,
                use_csp=use_csp,
            )

            copy_out_artifacts(
                out_dir=out_dir,
                destination=output_dir
                / "artifacts"
                / safe_filename_part(dataset_name)
                / identity,
            )

            semantic_failure_reasons: Mapping[int, list] = result.get(
                "semantic_validation_failure_reasons", {}
            )
            for pipeline_id, reasons in semantic_failure_reasons.items():
                save_file(
                    f"pipeline_{pipeline_id}.md",
                    "\n\n---\n\n".join(
                        f"Attempt {i + 1}:\n{reason}"
                        for i, reason in enumerate(reasons)
                    ),
                    out_dir=output_dir
                    / "semantic_failures"
                    / safe_filename_part(dataset_name)
                    / identity,
                )

            parsed: Specification = Specification.parse(specification.read_text())
            row = build_experiment_summary_row(
                dataset_name=dataset_name,
                openml_id=openml_id,
                problem=task,
                dataset_df=pd.read_csv(dataset_path),
                result=result,
                pipeline_budget=parsed.pipelines if use_csp else 1,
                workers=parsed.workers,
                specification=specification.name,
            )
            row["Resume Identity"] = identity
            save_experiment_summary_to_csv(row=row, csv_path=output_path)
    return output_path
