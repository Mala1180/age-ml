from typing import Optional, List

import fire
import mlflow
from langchain_core.messages import BaseMessage

from automlllm import logger
from automlllm.common.types import Step
from automlllm.execution.agent import (
    execution_agent,
    ExecutionAgentState,
    ExecutionPipeline,
)
from automlllm.planning.agent import (
    create_user_prompt,
    PlanningPipeline,
)

mlflow.set_experiment("mattia-experiment")
mlflow.openai.autolog()
mlflow.langchain.autolog()


def main(prompt: str = "", dataset_path: Optional[str] = None):
    dataset_path = "resources/datasets/adult.csv"
    specification_path = "resources/adult-specification.yml"
    prompt = "Help me to build a machine learning pipeline for Adult Income Prediction."
    messages: List[BaseMessage] = create_user_prompt(prompt)

    planned_pipeline = PlanningPipeline(
        steps=[
            Step(
                name="imputation",
                candidate="simple_imputer",
                hyperparameters={"strategy": ["mean", "median"]},
            ),
            Step(
                name="features",
                candidate="select_k_best",
                hyperparameters={"k": [5, 10]},
            ),
            Step(
                name="classification",
                candidate="random_forest",
                hyperparameters={
                    "n_estimators": [200],
                    "max_depth": [None, 20],
                },
            ),
        ]
    )
    # planned_pipeline: PlanningPipeline = planning["pipeline"]

    # dataset_info: str = planning["dataset_info"]
    execution_pipeline: ExecutionPipeline = ExecutionPipeline(
        id=1, steps=planned_pipeline.steps
    )
    execution: ExecutionAgentState = execution_agent.invoke(  # type: ignore[assignment]
        {
            "dataset_path": dataset_path,
            "specification_path": specification_path,
            "pipeline": execution_pipeline,
        }
    )
    logger.info(execution)


if __name__ == "__main__":
    fire.Fire(main)
