from typing import Optional, List

import fire
import mlflow
from langchain_core.messages import BaseMessage

from automlllm import logger
from automlllm.execution.agent import (
    execution_agent,
    ExecutionAgentState,
    ExecutionPipeline,
)
from automlllm.planning.agent import (
    planning_agent,
    create_user_prompt,
    PlanningAgentState,
    PlanningPipeline,
)

mlflow.set_experiment("mattia-experiment")
mlflow.openai.autolog()
mlflow.langchain.autolog()


def main(prompt: str = "", dataset_path: Optional[str] = None):
    dataset_path = "resources/datasets/adult.csv"
    specification_path = "resources/automl-specification.yml"
    prompt = "Help me to build a machine learning pipeline for Adult Income Prediction."
    messages: List[BaseMessage] = create_user_prompt(prompt)

    planning: PlanningAgentState = planning_agent.invoke(  # type: ignore[assignment]
        {
            "messages": messages,
            "user_prompt": prompt,
            "specification_path": specification_path,
            "dataset_path": dataset_path,
        }
    )
    planned_pipeline: PlanningPipeline = planning["pipeline"]

    dataset_info: str = planning["dataset_info"]
    execution_pipeline: ExecutionPipeline = ExecutionPipeline(
        id=1, steps=planned_pipeline.steps
    )
    execution: ExecutionAgentState = execution_agent.invoke(  # type: ignore[assignment]
        {
            "dataset_path": dataset_path,
            "dataset_info": dataset_info,
            "specification_path": specification_path,
            "pipeline": execution_pipeline,
        }
    )
    logger.info(execution)


if __name__ == "__main__":
    fire.Fire(main)
