import csv
import json
from datetime import timedelta
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

import pandas as pd
from pandas.api.types import is_bool_dtype, is_numeric_dtype


SUMMARY_COLUMNS: dict[str, str] = {
    "openml_id": "OpenML ID",
    "dataset": "Dataset",
    "problem": "Problem",
    "best_pipeline": "Best Pipeline",
    "best_test_score": "Best Test-set Score",
    "baseline": "Baseline",
    "features": "Features",
    "instances": "Instances",
    "numeric_features": "Numeric Features",
    "discrete_features": "Discrete Features",
    "actual_time": "Actual Time",
    "equivalent_time": "Equivalent Time",
    "llm_inference_time": "LLM Inference Time",
    "ml_training_time": "ML Training Time",
    "workers": "Workers",
    "pipeline_budget": "Pipeline Budget",
    "actual_pipelines": "Actual Pipelines",
    "input_tokens": "Input Tokens",
    "output_tokens": "Output Tokens",
    "total_tokens": "Total Tokens",
    "putative_cost": "Putative Cost ($)",
}


def _serialize_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return value
    return json.dumps(value, sort_keys=True, default=str)


def _append_row(
    row: Mapping[str, Any],
    csv_path: str | Path,
    columns: Sequence[str],
    *,
    strict_schema: bool = False,
) -> Path:
    path = Path(csv_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    expected_columns = list(columns)

    if strict_schema:
        missing = [column for column in expected_columns if column not in row]
        extra = [key for key in row if key not in expected_columns]
        if missing or extra:
            raise ValueError(
                "Row keys do not match expected columns. "
                f"Missing: {missing or '[]'}. Extra: {extra or '[]'}."
            )

    normalized_row = {
        column: _serialize_value(row.get(column, "")) for column in expected_columns
    }

    file_exists = path.exists() and path.stat().st_size > 0
    if file_exists:
        with path.open("r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            existing_columns = reader.fieldnames or []
            existing_rows = list(reader)
        if existing_columns != expected_columns:
            with path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=expected_columns)
                writer.writeheader()
                for existing_row in existing_rows:
                    aligned_existing_row = {
                        column: existing_row.get(column, "")
                        for column in expected_columns
                    }
                    writer.writerow(aligned_existing_row)
            file_exists = True

    mode = "a" if file_exists else "w"
    with path.open(mode, newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=expected_columns)
        if not file_exists:
            writer.writeheader()
        writer.writerow(normalized_row)
    return path


def _format_duration(seconds: float | int | None) -> str:
    if seconds is None:
        return ""
    return str(timedelta(seconds=round(float(seconds))))


def _compute_feature_stats(df: pd.DataFrame) -> tuple[int, int]:
    numeric_features = 0
    for dtype in df.dtypes:
        if is_numeric_dtype(dtype) and not is_bool_dtype(dtype):
            numeric_features += 1
    discrete_features = int(df.shape[1]) - numeric_features
    return numeric_features, discrete_features


def build_experiment_summary_row(
    dataset_name: str,
    openml_id: int,
    problem: str,
    dataset_df: pd.DataFrame,
    result: Mapping[str, Any],
    pipeline_budget: int,
    workers: int,
) -> Dict[str, Any]:
    features_df = dataset_df.iloc[:, :-1] if dataset_df.shape[1] > 1 else dataset_df
    numeric_features, discrete_features = _compute_feature_stats(features_df)

    token_usage = result.get("token_usage", {})
    if not isinstance(token_usage, Mapping):
        token_usage = {}

    pipeline_run_ids = result.get("pipeline_run_ids", {})
    if isinstance(pipeline_run_ids, Mapping):
        actual_pipelines = sum(1 for run_id in pipeline_run_ids.values() if run_id)
    else:
        actual_pipelines = ""

    actual_runtime_seconds = result.get("runtime_seconds")
    try:
        actual_runtime_seconds = (
            float(actual_runtime_seconds)
            if actual_runtime_seconds is not None
            else None
        )
    except (TypeError, ValueError):
        actual_runtime_seconds = None

    actual_time = result.get("runtime_human_readable") or _format_duration(
        actual_runtime_seconds
    )
    training_time_seconds = float(result.get("training_time") or 0.0)
    inference_time_seconds = float(result.get("inference_time") or 0.0)

    equivalent_time = _format_duration(training_time_seconds + inference_time_seconds)
    llm_inference_time = _format_duration(inference_time_seconds)
    ml_training_time = _format_duration(training_time_seconds)

    best_pipeline_id = result.get("best_pipeline_id")
    best_pipeline = (
        f"Pipeline {best_pipeline_id}" if best_pipeline_id is not None else ""
    )
    baseline = "hamlet" if problem == "classification" else "to fill"
    return {
        SUMMARY_COLUMNS["openml_id"]: openml_id,
        SUMMARY_COLUMNS["dataset"]: dataset_name,
        SUMMARY_COLUMNS["problem"]: problem,
        SUMMARY_COLUMNS["best_pipeline"]: best_pipeline,
        SUMMARY_COLUMNS["best_test_score"]: result.get("best_test_score", "")
        + f" ({result.get('validation_metric', '')})",
        SUMMARY_COLUMNS["baseline"]: baseline,
        SUMMARY_COLUMNS["features"]: int(features_df.shape[1]),
        SUMMARY_COLUMNS["instances"]: int(dataset_df.shape[0]),
        SUMMARY_COLUMNS["numeric_features"]: numeric_features,
        SUMMARY_COLUMNS["discrete_features"]: discrete_features,
        SUMMARY_COLUMNS["actual_time"]: actual_time,
        SUMMARY_COLUMNS["equivalent_time"]: equivalent_time,
        SUMMARY_COLUMNS["llm_inference_time"]: llm_inference_time,
        SUMMARY_COLUMNS["ml_training_time"]: ml_training_time,
        SUMMARY_COLUMNS["workers"]: workers,
        SUMMARY_COLUMNS["pipeline_budget"]: pipeline_budget,
        SUMMARY_COLUMNS["actual_pipelines"]: actual_pipelines,
        SUMMARY_COLUMNS["input_tokens"]: token_usage.get("input_tokens", ""),
        SUMMARY_COLUMNS["output_tokens"]: token_usage.get("output_tokens", ""),
        SUMMARY_COLUMNS["total_tokens"]: token_usage.get("total_tokens", ""),
        SUMMARY_COLUMNS["putative_cost"]: token_usage.get("total_cost", ""),
    }


def save_experiment_summary_to_csv(
    row: Mapping[str, Any], csv_path: str | Path
) -> Path:
    return _append_row(
        row=row,
        csv_path=csv_path,
        columns=list(SUMMARY_COLUMNS.values()),
        strict_schema=True,
    )


def _flatten_mapping(
    data: Mapping[str, Any], parent_key: str = "", sep: str = "_"
) -> Dict[str, Any]:
    flat: Dict[str, Any] = {}
    for key, value in data.items():
        full_key = f"{parent_key}{sep}{key}" if parent_key else key
        if isinstance(value, Mapping):
            flat.update(_flatten_mapping(value, parent_key=full_key, sep=sep))
        else:
            flat[full_key] = _serialize_value(value)
    return flat


def save_experiment_result_to_csv(
    result: Mapping[str, Any], csv_path: str | Path
) -> Path:
    row = _flatten_mapping(result)
    return _append_row(row=row, csv_path=csv_path, columns=list(row.keys()))
