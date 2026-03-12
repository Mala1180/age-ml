from concurrent.futures import ProcessPoolExecutor
from typing import Optional, Dict

import fire
import mlflow

from automlllm import logger
from automlllm.execution.agent import (
    execution_agent,
    ExecutionPipeline,
)
from automlllm.mocks import planned_pipeline_1, planned_pipeline_2

mlflow.openai.autolog()
mlflow.langchain.autolog()


def main(prompt: str = "", dataset_path: Optional[str] = None):
    dataset_path = "resources/datasets/adult.csv"
    specification_path = "resources/adult-specification.yml"
    # prompt = "Help me to build a machine learning pipeline for Adult Income Prediction."
    # messages: List[BaseMessage] = create_user_prompt(prompt)

    # planning: PlanningAgentState = planning_agent.invoke(
    #     {
    #         "messages": messages,
    #         "user_prompt": prompt,
    #         "specification_path": specification_path,
    #         "dataset_path": dataset_path,
    #     }
    # )
    # planned_pipeline: PlanningPipeline = planning["pipeline"]

    # dataset_info: str = planning["dataset_info"]
    execution_pipeline_1: ExecutionPipeline = ExecutionPipeline(
        id=1, steps=planned_pipeline_1.steps
    )
    execution_pipeline_2: ExecutionPipeline = ExecutionPipeline(
        id=2, steps=planned_pipeline_2.steps
    )
    print("Execution pipeline:")
    # print(str(execution_pipeline))
    mlflow.set_experiment("adult-experiment")

    with ProcessPoolExecutor(max_workers=2) as executor:
        future_1 = executor.submit(
            invoke_agent,
            {
                "dataset_path": dataset_path,
                "specification_path": specification_path,
                "pipeline": execution_pipeline_1,
            },
        )
        future_2 = executor.submit(
            invoke_agent,
            {
                "dataset_path": dataset_path,
                "specification_path": specification_path,
                "pipeline": execution_pipeline_2,
            },
        )
        future_1.result()
        future_2.result()


def invoke_agent(input: dict) -> Dict:
    logger.info(f"Invoking execution agent with input: {input}")
    result = execution_agent.invoke(input)
    logger.info(f"Agent returned result: {result}")
    return result


if __name__ == "__main__":
    fire.Fire(main)
