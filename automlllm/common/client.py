from typing import Optional, Dict, List

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


def set_trace_metadata(session: str) -> None:
    try:
        mlflow.update_current_trace(
            tags={"session": session},
            metadata={"mlflow.trace.session": session},
        )
    except Exception as exc:
        logger.debug(f"Unable to update current active trace metadata: {exc}")


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
