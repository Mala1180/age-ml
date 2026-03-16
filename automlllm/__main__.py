from datetime import datetime
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Dict, List, Optional

import fire
import mlflow
from mlflow.entities import Experiment

from automlllm import logger
from automlllm.execution.agent import (
    execution_agent,
    ExecutionPipeline,
)
from automlllm.planning.agent import PlanningPipeline, planning_agent
from automlllm.specification import Specification

mlflow.openai.autolog()
mlflow.langchain.autolog()


def main(spec_path: str, dataset_path: str, max_workers: int = 5) -> None:
    """Run planning and execution from the command line.

    The command can be invoked as:

    ``python -m automlllm --spec_path=<path> --dataset_path=<path> --max_workers=<number>``

    The max pipeline exploration cap is read from ``max_exploration`` in the
    specification YAML.

    Args:
        spec_path: Filesystem path to the YAML specification file.
        dataset_path: Filesystem path to the input dataset used for the AutoML task.
        max_workers: Maximum number of workers to launch.

    Returns:
        None.
    """
    # dataset_path = "resources/datasets/adult.csv"
    # spec_path = "resources/general-specification.yml"

    specification: Specification = Specification.parse(Path(spec_path).read_text())
    max_pipelines: int = specification.max_exploration

    planning = planning_agent.invoke(
        {
            "specification_path": spec_path,
            "dataset_path": dataset_path,
            "max_pipelines": max_pipelines,
        }
    )
    planned_pipelines: List[PlanningPipeline] = planning["pipelines"]

    experiment_name: str = "adult-experiment"
    mlflow.set_experiment(experiment_name)
    experiment: Optional[Experiment] = mlflow.get_experiment_by_name(experiment_name)
    assert experiment is not None, "Experiment should exist after setting it"
    experiment_id = experiment.experiment_id

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    run_name: str = f"pipeline_exploration-{timestamp}"
    with mlflow.start_run(run_name=run_name) as run:
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            for i, planned_pipeline in enumerate(planned_pipelines):
                print(f"Executing pipeline {i}")
                execution_pipeline: ExecutionPipeline = ExecutionPipeline(
                    id=i, steps=planned_pipeline.steps
                )
                executor.submit(
                    invoke_agent,
                    {
                        "dataset_path": dataset_path,
                        "specification_path": spec_path,
                        "pipeline": execution_pipeline,
                        "run_id": run.info.run_id,
                        "experiment_id": experiment_id,
                    },
                )
                # invoke_agent(
                #     {
                #         "dataset_path": dataset_path,
                #         "specification_path": spec_path,
                #         "pipeline": execution_pipeline,
                #     }
                # )


def invoke_agent(input: dict) -> Dict:
    logger.info(f"Invoking execution agent with input: {input}")
    result = execution_agent.invoke(input)
    logger.info(f"Agent returned result: {result}")
    return result


if __name__ == "__main__":
    fire.Fire(main)
