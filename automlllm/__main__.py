from datetime import datetime
from multiprocessing import Process, Semaphore
from time import monotonic, sleep
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


def main(spec_path: str, dataset_path: str) -> None:
    """Run planning and execution from the command line.

    The command can be invoked as:

    ``python -m automlllm --spec_path=<path> --dataset_path=<path>``

    Runtime budgets are read from ``budgets`` in the specification YAML:
    ``budgets.pipelines``, ``budgets.time`` (hours/minutes/seconds), and ``budgets.workers``.

    Args:
        spec_path: Filesystem path to the YAML specification file.
        dataset_path: Filesystem path to the input dataset used for the AutoML task.
    Returns:
        None.
    """
    # dataset_path = "resources/datasets/adult.csv"
    # spec_path = "resources/general-specification.yml"

    specification: Specification = Specification.parse(Path(spec_path).read_text())
    time_budget_seconds: int = specification.budgets.time.total_seconds
    max_workers: int = specification.budgets.workers
    execution_deadline = monotonic() + time_budget_seconds

    planning = planning_agent.invoke(
        {
            "specification_path": spec_path,
            "dataset_path": dataset_path,
        }
    )
    planned_pipelines: List[PlanningPipeline] = planning["pipelines"]

    experiment_name: str = "adult-experiment"
    mlflow.set_experiment(experiment_name)
    experiment: Optional[Experiment] = mlflow.get_experiment_by_name(experiment_name)
    assert experiment is not None, "Experiment should exist after setting it"
    experiment_id = experiment.experiment_id

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    run_name: str = f"pipelines_exploration-{timestamp}"
    with mlflow.start_run(run_name=run_name) as run:
        semaphore = Semaphore(max_workers)
        processes: List[Process] = []

        for i, planned_pipeline in enumerate(planned_pipelines):
            print(f"Executing pipeline {i}")
            execution_pipeline: ExecutionPipeline = ExecutionPipeline(
                id=i, steps=planned_pipeline.steps
            )
            process = Process(
                target=invoke_agent,
                args=(
                    {
                        "dataset_path": dataset_path,
                        "specification_path": spec_path,
                        "pipeline": execution_pipeline,
                        "run_id": run.info.run_id,
                        "experiment_id": experiment_id,
                    },
                    semaphore,
                ),
            )
            process.start()
            processes.append(process)

        while monotonic() < execution_deadline:
            if all(not p.is_alive() for p in processes):
                break
            sleep(1)

        completed = 0
        terminated = 0
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)
                terminated += 1
                logger.warning("Terminated pipeline due to deadline")
            else:
                completed += 1

        logger.info(f"Completed {completed} pipelines, terminated {terminated}")


def invoke_agent(input: dict, semaphore) -> Dict:
    with semaphore:
        logger.info(f"Invoking execution agent with input: {input}")
        result = execution_agent.invoke(input)
        logger.info(f"Agent returned result: {result}")
        return result


if __name__ == "__main__":
    fire.Fire(main)
