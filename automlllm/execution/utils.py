import re
from itertools import product
from typing import Dict, Any, Iterator

import numpy as np
from mlflow import MlflowClient
from sklearn import metrics

client = MlflowClient()


def compute_metric(y_true: Any, y_pred: Any, metric_name: str) -> float:
    """Compute a validation metric given true and predicted values."""
    metric_functions = {
        "accuracy": metrics.accuracy_score,
        "f1": metrics.f1_score,
        "precision": metrics.precision_score,
        "recall": metrics.recall_score,
        "roc_auc": metrics.roc_auc_score,
        "mse": metrics.mean_squared_error,
        "rmse": lambda y, p: np.sqrt(metrics.mean_squared_error(y, p)),
        "mae": metrics.mean_absolute_error,
        "r2": metrics.r2_score,
    }

    if metric_name not in metric_functions:
        raise ValueError(
            f"Unknown metric: {metric_name}. "
            f"Available metrics: {list(metric_functions.keys())}"
        )

    return float(metric_functions[metric_name](y_true, y_pred))


def extract_python_code(text: str) -> str:
    blocks = re.findall(r"```(?:python)?\s*(.*?)```", text, re.DOTALL)
    if blocks:
        return "\n\n".join(blocks).strip()
    return text.strip()


def grid_search_exploration(
    hyperparameters: Dict[str, Any],
) -> Iterator[Dict[str, Any]]:
    keys = hyperparameters.keys()
    values = hyperparameters.values()
    for combination in product(*values):
        yield dict(zip(keys, combination))


def delete_failed_runs(parent_run_id: str, experiment_id: str):
    runs = client.search_runs(
        experiment_ids=[experiment_id],
        filter_string=f"tags.mlflow.parentRunId = '{parent_run_id}'",
    )

    for r in runs:
        client.delete_run(r.info.run_id)

    client.delete_run(parent_run_id)


def set_run_description(run_id: str, description: str) -> None:
    client.set_tag(run_id, "mlflow.note.content", description)


def get_best_run(
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
