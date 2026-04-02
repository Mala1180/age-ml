import mlflow
from mlflow import MlflowClient

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
    run = client.get_run(run_id)
    return run.info.run_name
