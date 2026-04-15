import re
from itertools import product
from typing import Any, Dict, Iterator, Callable

import numpy as np
from sklearn import metrics

METRIC_FUNCTIONS: Dict[str, Callable] = {
    "accuracy": metrics.accuracy_score,
    "balanced_accuracy": metrics.balanced_accuracy_score,
    "f1": metrics.f1_score,
    "precision": metrics.precision_score,
    "recall": metrics.recall_score,
    "roc_auc": metrics.roc_auc_score,
    "mse": metrics.mean_squared_error,
    "rmse": lambda y, p: np.sqrt(metrics.mean_squared_error(y, p)),
    "mae": metrics.mean_absolute_error,
    "r2": metrics.r2_score,
}


def get_metric(metric_name: str) -> Callable:
    """Get the metric function by name."""
    if metric_name not in METRIC_FUNCTIONS:
        raise ValueError(
            f"Unknown metric: {metric_name}. "
            f"Available metrics: {list(METRIC_FUNCTIONS.keys())}"
        )
    return METRIC_FUNCTIONS[metric_name]


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
