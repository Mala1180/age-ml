from typing import Optional, Dict, List, Set

import mlflow
from mlflow import MlflowClient
from mlflow.entities import Run, Trace

from automlllm import logger

client = MlflowClient()


def delete_failed_runs(parent_run_id: str, experiment_id: str):
    """Delete nested runs except the one(s) named 'failed_runs'."""
    runs = client.search_runs(
        experiment_ids=[experiment_id],
        filter_string=f"tags.mlflow.parentRunId = '{parent_run_id}'",
    )

    for r in runs:
        if r.info.run_name == "failed_runs":
            continue
        client.delete_run(r.info.run_id)


def set_run_description(run_id: str, description: str) -> None:
    client.set_tag(run_id, "mlflow.note.content", description)


def get_best_pipeline_run(
    parent_run_id: str,
    experiment_id: str,
    metric: str = "validation_score",
    maximize: bool = True,
) -> str | None:
    """Get the best nested run based on a metric."""
    runs = client.search_runs(
        experiment_ids=[experiment_id],
        filter_string=f"tags.mlflow.parentRunId = '{parent_run_id}'",
        order_by=[f"metrics.{metric} {'DESC' if maximize else 'ASC'}"],
        max_results=1,
    )
    if runs:
        return runs[0].info.run_id
    return None


def get_model_from_run_id(run_id: str):
    return mlflow.pyfunc.load_model(f"runs:/{run_id}/model")


def get_run_name_from_run_id(run_id: str) -> str:
    run: Run = client.get_run(run_id)
    return run.info.run_name


def enable_mlflow_llm_autologging() -> None:
    mlflow.openai.autolog()
    mlflow.langchain.autolog()
    mlflow.gemini.autolog()


def get_session_total_token_usage(session: str) -> Dict[str, int | float]:
    escaped_session: str = session.replace("'", "\\'")
    filter_string = f"tags.session = '{escaped_session}'"

    try:
        traces: List[Trace] = mlflow.search_traces(
            filter_string=filter_string,
            return_type="list",
        )
    except Exception as exc:
        logger.warning(f"Unable to search traces for session '{session}': {exc}")
        return {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
        }

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    input_cost: float = 0
    output_cost: float = 0
    total_cost: float = 0

    for trace in traces:
        usage: Optional[Dict[str, int]] = trace.info.token_usage
        if usage is not None:
            input_tokens += usage["input_tokens"]
            output_tokens += usage["output_tokens"]
            total_tokens += usage["total_tokens"]

        cost: Optional[Dict[str, float]] = trace.info.cost
        if cost is not None:
            input_cost += cost["input_cost"]
            output_cost += cost["output_cost"]
            total_cost += cost["total_cost"]

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "input_cost": input_cost,
        "output_cost": output_cost,
        "total_cost": total_cost,
    }


def _get_run_duration_seconds(run: Run) -> float:
    start_time = run.info.start_time
    end_time = run.info.end_time

    if start_time is None or end_time is None:
        return 0.0
    if end_time < start_time:
        return 0.0

    return (end_time - start_time) / 1000.0


def get_nested_runs_total_duration(parent_run_id: str, experiment_id: str) -> float:
    """Return total duration (seconds) across all nested descendants of a run."""
    total_duration_seconds = 0.0

    parents_to_visit = [parent_run_id]
    visited_parent_ids: Set[str] = set()

    while parents_to_visit:
        current_parent_id = parents_to_visit.pop()
        if current_parent_id in visited_parent_ids:
            continue
        visited_parent_ids.add(current_parent_id)
        escaped_current_parent_id = current_parent_id.replace("'", "\\'")

        runs = client.search_runs(
            experiment_ids=[experiment_id],
            filter_string=(
                f"tags.mlflow.parentRunId = '{escaped_current_parent_id}' "
                "AND attributes.run_name != 'failed_runs'"
            ),
            max_results=50000,
        )

        for run in runs:
            if run.info.run_name == "failed_runs":
                continue
            total_duration_seconds += _get_run_duration_seconds(run)
            run_id = run.info.run_id
            if run_id and run_id not in visited_parent_ids:
                parents_to_visit.append(run_id)

    return total_duration_seconds


def _get_trace_duration_seconds(trace: Trace) -> float:
    execution_duration = trace.info.execution_duration
    if execution_duration is None:
        return 0.0
    if execution_duration < 0:
        return 0.0
    return execution_duration / 1000.0


def get_nested_runs_total_llm_latency(session: str, experiment_id: str) -> float:
    """Return total LLM trace latency (seconds) across all traces in a session."""
    total_latency_seconds = 0.0
    escaped_session = session.replace("'", "\\'")
    filter_string = f"tags.session = '{escaped_session}'"

    try:
        traces: List[Trace] = mlflow.search_traces(
            locations=[experiment_id],
            filter_string=filter_string,
            max_results=None,
            return_type="list",
            include_spans=False,
        )
    except Exception as exc:
        logger.warning(
            f"Unable to search traces for session '{session}' in experiment '{experiment_id}': {exc}"
        )
        return 0.0

    for trace in traces:
        total_latency_seconds += _get_trace_duration_seconds(trace)

    return total_latency_seconds
