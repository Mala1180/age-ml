from typing import Any, Dict

import fire
import mlflow
import pandas as pd

from automlllm.common.types import Step
from automlllm.execution.agent import execution_agent, ExecutionPipeline
from automlllm import logger
from automlllm.planning.agent import PlanningPipeline
from resources import get_resource_path

mlflow.set_experiment("mattia-experiment")
mlflow.openai.autolog()
mlflow.langchain.autolog()


def main() -> None:
    dataset_path: str = "datasets/adult.csv"
    # prompt = "Help me to build a machine learning pipeline for Adult Income Prediction."
    df: pd.DataFrame = pd.read_csv(get_resource_path(dataset_path))
    dataset_info: str = f"""
            Loaded dataset with {len(df)} rows and {len(df.columns)} columns
            Columns:\n{list(df.columns)}
            Data Types:\n{df.dtypes.to_markdown()}
            Description:\n{df.describe().to_markdown()}
            Preview:\n{df.head().to_markdown()}
        """

    planning_pipeline_mock: PlanningPipeline = PlanningPipeline(
        steps=[
            Step(
                name="imputation",
                candidate="simple_imputer",
                hyperparameters={"strategy": ["mean", "median"]},
            ),
            Step(
                name="classification",
                candidate="random_forest",
                hyperparameters={"n_estimators": [200], "max_depth": [None, 20]},
            ),
        ]
    )
    execution_pipeline: ExecutionPipeline = ExecutionPipeline(
        id=1, steps=planning_pipeline_mock.steps
    )

    initial_state: Dict[str, Any] = {
        "dataset_path": dataset_path,
        "dataset_info": dataset_info,
        "pipeline": execution_pipeline,
    }
    for mode, chunk in execution_agent.stream(
        initial_state,
        stream_mode=["values"],
    ):
        assert isinstance(chunk, dict)
        for step, data in chunk.items():
            logger.info(f"step: {step}")
            logger.info(f"content: {data}")


if __name__ == "__main__":
    fire.Fire(main)
