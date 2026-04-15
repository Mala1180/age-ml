import multiprocessing
import time
from copy import deepcopy
from datetime import datetime, timedelta
from multiprocessing import Pool
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
from automlllm.common.client import (
    enable_mlflow_llm_autologging,
    get_nested_runs_total_llm_latency,
    get_nested_runs_total_duration,
    get_session_total_token_usage,
)
from automlllm.common.model import model
from automlllm.evaluation.agent import evaluation_agent
from automlllm.execution.agent import (
    execution_agent,
    ExecutionPipeline,
    PipelineStatus,
)
from automlllm.planning.agent import PlanningPipeline, planning_agent
from automlllm.specification import Specification


def main(
    spec_path: str,
    dataset_path: str,
    validation_metric: str = "accuracy",
    maximize: bool = True,
) -> Dict:
    """Run planning and execution from the command line.

    The command can be invoked as:

    ``python -m automlllm --spec_path=<path> --dataset_path=<path>``

    Runtime budgets are read from ``budgets`` in the specification YAML:
    ``budgets.pipelines``, ``budgets.time`` (hours/minutes/seconds), ``budgets.workers``,
    and ``budgets.generation_attempts``.

    Args:
        spec_path: Filesystem path to the YAML specification file.
        dataset_path: Filesystem path to the input dataset used for the AutoML task.
        validation_metric: Name of the metric to use for model selection (default: "accuracy").
        maximize: Whether to maximize the metric (True) or minimize it (False). Default: True.
    Returns:
        None.
    """
    enable_mlflow_llm_autologging()

    specification: Specification = Specification.parse(Path(spec_path).read_text())

    start_time = time.perf_counter()
    timeout = specification.budgets.time.total_seconds
    deadline = time.time() + timeout

    df: pd.DataFrame = pd.read_csv(Path(dataset_path))
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    run_name: str = f"pipelines_exploration-{timestamp}"
    session: str = run_name
    with mlflow.context(
        tags={"session": session},
        metadata={"mlflow.trace.session": session},
    ):
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
        experiment: Optional[Experiment] = mlflow.get_experiment_by_name(
            experiment_name
        )
        assert experiment is not None, "Experiment should exist after setting it"
        experiment_id = experiment.experiment_id

        with mlflow.start_run(run_name=run_name) as run:
            try:
                train_df, test_df = train_test_split(
                    df, test_size=0.2, stratify=df[target_feature], random_state=42
                )
            except ValueError:
                train_df, test_df = train_test_split(df, test_size=0.2, random_state=42)

            inputs: List[Dict[str, Any]] = []
            for i, planned_pipeline in enumerate(planned_pipelines):
                execution_pipeline: ExecutionPipeline = ExecutionPipeline(
                    id=i, steps=planned_pipeline.steps
                )
                inputs.append(
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
                    }
                )

            results: List = deepcopy(inputs)
            failed: int = 0
            timed_out: int = 0
            with Pool(processes=specification.budgets.workers) as pool:
                jobs = [pool.apply_async(invoke_agent, (i, session)) for i in inputs]

                for i, job in enumerate(jobs):
                    remaining = deadline - time.time()
                    if remaining <= 0:
                        remaining = 0

                    try:
                        results[i] = job.get(timeout=remaining)
                    except multiprocessing.TimeoutError:
                        logger.info(f"Pipeline {i} execution timed out")
                        results[i]["status"] = PipelineStatus.TIMED_OUT
                    except Exception as e:
                        logger.error(
                            f"Pipeline {i} execution failed with general error:\n{e}"
                        )
                        results[i]["status"] = PipelineStatus.FAILED
                        failed += 1

            total_training_time: float = 0.0
            for r in results:
                if r["status"] == PipelineStatus.FAILED:
                    failed += 1
                if r["status"] == PipelineStatus.TIMED_OUT:
                    timed_out += 1
                if r["status"] != PipelineStatus.TIMED_OUT:
                    logger.info(
                        f"Pipeline id: {r['pipeline'].id}, validation_attempts: {r['validation_attempts']}, execution_attempts: {r['execution_attempts']}"
                    )

                pipeline_run_id: Optional[str] = r.get("pipeline_run_id")
                if pipeline_run_id:
                    nested_runs_duration = get_nested_runs_total_duration(
                        pipeline_run_id, experiment_id
                    )
                    total_training_time += nested_runs_duration
            total_inference_time: float = get_nested_runs_total_llm_latency(
                session, experiment_id
            )

            logger.info(f"Failed pipelines: {failed}")
            logger.info(f"Timed out pipelines: {timed_out}")

            pipeline_run_ids: Dict[str, Optional[str]] = {
                result["pipeline"].id: result.get("pipeline_run_id")
                if result["status"] == PipelineStatus.COMPLETED
                else None
                for result in results
            }

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

            elapsed_seconds = time.perf_counter() - start_time
            human_readable_runtime = str(timedelta(seconds=round(elapsed_seconds)))
            res["runtime_seconds"] = elapsed_seconds
            res["runtime_human_readable"] = human_readable_runtime
            res["training_time"] = total_training_time
            res["inference_time"] = total_inference_time
            res["token_usage"] = get_session_total_token_usage(session)
            logger.info(
                f"Best model: Pipeline {res['best_pipeline_id']}\n"
                f"  - run id = {res['best_run_id']}\n"
                f"  - run name = {res['best_run_name']}\n"
                f"  - {res['validation_metric']} = {res['best_test_score']} on test set"
            )
            logger.info(
                f"Session '{run.info.run_name}' time:\n"
                f"  - runtime_seconds = {res['runtime_seconds']:.2f}\n"
                f"  - runtime_human_readable = {res['runtime_human_readable']}\n"
                f"  - training_time = {res['training_time']:.2f}\n"
                f"  - inference_time = {res['inference_time']:.2f}"
            )
            logger.info(
                f"Session '{run.info.run_name}' token usage:\n"
                f"  - input_tokens = {res['token_usage']['input_tokens']}\n"
                f"  - output_tokens = {res['token_usage']['output_tokens']}\n"
                f"  - total_tokens = {res['token_usage']['total_tokens']}"
            )
            logger.info(
                f"Session '{run.info.run_name}' costs:\n"
                f"  - input_cost = {res['token_usage']['input_cost']}\n"
                f"  - output_cost = {res['token_usage']['output_cost']}\n"
                f"  - total_cost = {res['token_usage']['total_cost']}"
            )

            return res


def invoke_agent(agent_input: dict, session: str) -> Dict[str, Any]:
    with mlflow.context(
        tags={"session": session},
        metadata={"mlflow.trace.session": session},
    ):
        logger.info(f"Invoking execution agent with input: {agent_input}")
        result = execution_agent.invoke(agent_input)
        logger.info(f"Agent returned result with keys {result.keys()}")
    return result


class TargetFeatureResponse(BaseModel):
    target_feature: str
    reasoning: str


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
        - The data type (classification targets are often categorical/integer, regression targets are often float)

        Provide your answer with the exact column name and your reasoning.
    """
    target_model = model.with_structured_output(TargetFeatureResponse)
    response = target_model.invoke([HumanMessage(content=identify_prompt)])
    assert isinstance(response, TargetFeatureResponse)
    return response.target_feature


if __name__ == "__main__":
    fire.Fire(main)
