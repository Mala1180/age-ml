from concurrent.futures import ProcessPoolExecutor
from typing import Dict, List

import fire
import mlflow

from automlllm import logger
from automlllm.execution.agent import (
    execution_agent,
    ExecutionPipeline,
)
from automlllm.planning.agent import PlanningPipeline, planning_agent

mlflow.openai.autolog()
mlflow.langchain.autolog()


def main(spec_path: str, dataset_path: str, max_pipelines: int = 5) -> None:
    """Run planning and execution from the command line.

    The command can be invoked as:

    ``python -m automlllm --spec_path=<path> --dataset_path=<path>``

    Args:
        spec_path: Filesystem path to the YAML specification file.
        dataset_path: Filesystem path to the input dataset used for the AutoML task.
        max_pipelines: Maximum number of pipelines to explore and execute.

    Returns:
        None.
    """
    # dataset_path = "resources/datasets/adult.csv"
    # spec_path = "resources/general-specification.yml"

    planning = planning_agent.invoke(
        {
            "specification_path": spec_path,
            "dataset_path": dataset_path,
            "max_pipelines": max_pipelines,
        }
    )
    planned_pipelines: List[PlanningPipeline] = planning["pipelines"]

    mlflow.set_experiment("adult-experiment")

    with ProcessPoolExecutor(max_workers=4) as executor:
        for i, planned_pipeline in enumerate(planned_pipelines):
            print(f"Executing pipeline {i}")
            execution_pipeline: ExecutionPipeline = ExecutionPipeline(
                id=i, steps=planned_pipeline.steps
            )
            # invoke_agent(
            #     {
            #         "dataset_path": dataset_path,
            #         "specification_path": spec_path,
            #         "pipeline": execution_pipeline,
            #     }
            # )
            executor.submit(
                invoke_agent,
                {
                    "dataset_path": dataset_path,
                    "specification_path": spec_path,
                    "pipeline": execution_pipeline,
                },
            )
            # future.result()


def invoke_agent(input: dict) -> Dict:
    logger.info(f"Invoking execution agent with input: {input}")
    result = execution_agent.invoke(input)
    logger.info(f"Agent returned result: {result}")
    return result


if __name__ == "__main__":
    fire.Fire(main)
