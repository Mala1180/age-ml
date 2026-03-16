import re
from itertools import product
from typing import Dict, Any, Iterator

from mlflow import MlflowClient


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
    client = MlflowClient()
    runs = client.search_runs(
        experiment_ids=[experiment_id],
        filter_string=f"tags.mlflow.parentRunId = '{parent_run_id}'",
    )

    for r in runs:
        client.delete_run(r.info.run_id)

    client.delete_run(parent_run_id)
