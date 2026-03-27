from datetime import datetime
from multiprocessing import Process, Semaphore, Queue
from time import monotonic, sleep
from pathlib import Path
from typing import Dict, List, Optional, Any

import fire
import mlflow
import pandas as pd
from langchain_core.messages import HumanMessage
from mlflow.entities import Experiment
from pydantic import BaseModel
from sklearn.model_selection import train_test_split

from automlllm import logger
from automlllm.common.model import model
from automlllm.evaluation.agent import evaluation_agent
from automlllm.execution.agent import (
    execution_agent,
    ExecutionPipeline,
)
from automlllm.planning.agent import PlanningPipeline, planning_agent
from automlllm.specification import Specification

mlflow.openai.autolog()
mlflow.langchain.autolog()


def main(
    spec_path: str,
    dataset_path: str,
    validation_metric: str = "accuracy",
    maximize: bool = True,
) -> None:
    """Run planning and execution from the command line.

    The command can be invoked as:

    ``python -m automlllm --spec_path=<path> --dataset_path=<path>``

    Runtime budgets are read from ``budgets`` in the specification YAML:
    ``budgets.pipelines``, ``budgets.time`` (hours/minutes/seconds), and ``budgets.workers``.

    Args:
        spec_path: Filesystem path to the YAML specification file.
        dataset_path: Filesystem path to the input dataset used for the AutoML task.
        validation_metric: Name of the metric to use for model selection (default: "accuracy").
        maximize: Whether to maximize the metric (True) or minimize it (False). Default: True.
    Returns:
        None.
    """
    specification: Specification = Specification.parse(Path(spec_path).read_text())
    execution_deadline = monotonic() + specification.budgets.time.total_seconds

    df: pd.DataFrame = pd.read_csv(Path(dataset_path))
    target_feature = identify_target_feature(df)

    planning = planning_agent.invoke(
        {
            "specification_path": spec_path,
            "dataset_path": dataset_path,
            "target_feature": target_feature,
        }
    )
    planned_pipelines: List[PlanningPipeline] = planning["pipelines"]

    experiment_name: str = Path(dataset_path).stem
    mlflow.set_experiment(experiment_name)
    experiment: Optional[Experiment] = mlflow.get_experiment_by_name(experiment_name)
    assert experiment is not None, "Experiment should exist after setting it"
    experiment_id = experiment.experiment_id

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    run_name: str = f"pipelines_exploration-{timestamp}"
    with mlflow.start_run(run_name=run_name) as run:
        train_df, test_df = train_test_split(df, test_size=0.2, random_state=42)

        result_queue: Queue = Queue()
        semaphore = Semaphore(specification.budgets.workers)
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
                        "specification_path": spec_path,
                        "dataset_path": dataset_path,
                        "train_df": train_df,
                        "target_feature": target_feature,
                        "pipeline": execution_pipeline,
                        "root_run_id": run.info.run_id,
                        "experiment_id": experiment_id,
                        "validation_metric": validation_metric,
                        "maximize": maximize,
                    },
                    semaphore,
                    result_queue,
                ),
            )
            process.start()
            processes.append(process)

        results = wait_and_collect_agents_results(
            processes, result_queue, execution_deadline
        )

        pipeline_run_ids: Dict[str, Optional[str]] = {
            result["pipeline"].id: result.get("pipeline_run_id") for result in results
        }

        # for result in results:
        #     if result.get("pipeline_run_id") is None:
        #         os.system(f"echo '{str(result["pipeline"])}' >> failed_pipelines.md")

        res = evaluation_agent.invoke(
            {
                "experiment_id": experiment_id,
                "pipeline_run_ids": pipeline_run_ids,
                "validation_metric": validation_metric,
                "maximize": maximize,
                "test_df": test_df,
                "target_feature": target_feature,
            }
        )
        logger.info(
            f"Best model: pipeline {res['best_pipeline_id']}, run {res['best_run_id']}, {res['validation_metric']} = {res['best_test_score']} on test set"
        )


def invoke_agent(input: dict, semaphore, result_queue) -> None:
    with semaphore:
        logger.info(f"Invoking execution agent with input: {input}")
        result = execution_agent.invoke(input)
        logger.info(f"Agent returned result: {result}")
        result_queue.put(result)


def wait_and_collect_agents_results(
    processes: List[Process],
    result_queue: Queue,
    execution_deadline: float,
) -> List[Dict]:
    results: List[Dict] = []
    expected_results = len(processes)

    while monotonic() < execution_deadline:
        # Collect any available results (non-blocking)
        while not result_queue.empty():
            results.append(result_queue.get_nowait())

        # Exit early if we have all results
        if len(results) >= expected_results:
            break
        sleep(1)

    # Collect any remaining results
    while not result_queue.empty():
        results.append(result_queue.get_nowait())

    completed = 0
    terminated = 0
    for process in processes:
        if process.is_alive():
            process.terminate()
            process.join(timeout=5)
            terminated += 1
            logger.warning("Terminated pipeline due to deadline")
        else:
            process.join()
            completed += 1

    logger.info(
        f"Completed {completed} pipelines, terminated by deadline budget: {terminated}"
    )

    logger.info(f"Got {results} results from execution agents")
    return results


class TargetFeatureResponse(BaseModel):
    target_feature: str
    reasoning: str


target_model = model.with_structured_output(TargetFeatureResponse)


def identify_target_feature(df: pd.DataFrame) -> str:
    identify_prompt: str = f"""
        Analyze the following dataset and identify the target column (the variable to predict).

        Dataset columns: {list(df.columns)}
        Data types:
        {df.dtypes.to_markdown()}

        Sample data:
        {df.head().to_markdown()}

        Based on the column names, data types, and sample values, determine which column
        is most likely the target variable for a machine learning task.

        Consider:
        - Common target column names (e.g., 'target', 'label', 'class', 'y', 'outcome')
        - The position of the column (often last)
        - The data type (classification targets are often categorical/integer, regression targets are often numeric)

        Provide your answer with the exact column name and your reasoning.
    """

    response: Any = target_model.invoke([HumanMessage(content=identify_prompt)])
    assert isinstance(response, TargetFeatureResponse)
    return response.target_feature


if __name__ == "__main__":
    fire.Fire(main)
