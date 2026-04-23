from pathlib import Path
from typing import Optional, Dict, List

import mlflow
import pandas as pd
from langgraph.constants import START, END
from langgraph.graph import MessagesState
from langgraph.graph.state import CompiledStateGraph, StateGraph

from automlllm import logger
from automlllm.common.client import (
    get_best_pipeline_run,
    get_model_from_run_id,
    get_run_name_from_run_id,
    enable_mlflow_llm_autologging,
)
from automlllm.execution.utils import get_metric


class EvaluationAgentState(MessagesState):
    experiment_id: str
    pipeline_run_ids: Dict[int, Optional[str]]
    best_run_per_pipeline: Dict[int, Optional[str]]
    specification_path: str
    validation_metric: str
    maximize: bool
    test_df: pd.DataFrame
    target_feature: str
    best_pipeline_id: Optional[int]
    best_run_id: Optional[str]
    best_run_name: Optional[str]
    best_test_score: Optional[float]
    test_scores: Dict[int, float]
    artifacts: Dict[str, List[str]]


def get_best_run_per_pipeline(state: EvaluationAgentState) -> EvaluationAgentState:
    enable_mlflow_llm_autologging()
    state["best_run_per_pipeline"] = {}

    for pipeline_id, pipeline_run_id in state["pipeline_run_ids"].items():
        if pipeline_run_id:
            best_run_id: Optional[str] = get_best_pipeline_run(
                pipeline_run_id,
                state["experiment_id"],
                metric=state["validation_metric"],
                maximize=state["maximize"],
            )
            logger.info(f"Best run for pipeline {pipeline_id}: {best_run_id}")
            state["best_run_per_pipeline"][pipeline_id] = best_run_id
        else:
            logger.info(f"No runs found for pipeline {pipeline_id}")

    return state


def get_best_run_across_pipelines(state: EvaluationAgentState) -> EvaluationAgentState:
    X_test = state["test_df"].drop(columns=[state["target_feature"]])
    y_test = state["test_df"][state["target_feature"]]

    metric_fn = get_metric(state["validation_metric"])
    state["test_scores"] = {}

    best_score = None
    best_run_id = None
    best_run_name = None
    best_pipeline_id = None

    for pipeline_id, run_id in state["best_run_per_pipeline"].items():
        if run_id is not None:
            try:
                model = get_model_from_run_id(run_id)
                y_pred = model.predict(X_test)
                score = metric_fn(y_test, y_pred)
                state["test_scores"][pipeline_id] = score

                run_name = get_run_name_from_run_id(run_id)
                logger.info(
                    f"Pipeline {pipeline_id}\n"
                    f"  - run id: {run_id}\n"
                    f"  - run name: {run_name}\n"
                    f"  - {state['validation_metric']} = {score} on test set\n"
                )

                if best_score is None:
                    best_score = score
                    best_run_id = run_id
                    best_run_name = run_name
                    best_pipeline_id = pipeline_id
                elif state["maximize"] and score > best_score:
                    best_score = score
                    best_run_id = run_id
                    best_run_name = run_name
                    best_pipeline_id = pipeline_id
                elif not state["maximize"] and score < best_score:
                    best_score = score
                    best_run_id = run_id
                    best_run_name = run_name
                    best_pipeline_id = pipeline_id

            except Exception as e:
                logger.error(
                    f"Error evaluating pipeline {pipeline_id} with run id {run_id}:\n{e}"
                )

    state["best_run_id"] = best_run_id
    state["best_run_name"] = best_run_name
    state["best_test_score"] = best_score
    state["best_pipeline_id"] = best_pipeline_id
    return state


def _download_artifacts(run_id: str, out_dir: Path) -> List[str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    downloaded_dir = Path(
        mlflow.artifacts.download_artifacts(run_id=run_id, dst_path=str(out_dir))
    )
    return [
        str(file_path) for file_path in downloaded_dir.rglob("*") if file_path.is_file()
    ]


def download_artifacts(state: EvaluationAgentState) -> EvaluationAgentState:
    state["artifacts"] = {}
    out_path = Path("out")

    best_run_id = state.get("best_run_id")
    if best_run_id:
        logger.info(f"Downloading artifacts for best run: {best_run_id}")
        state["artifacts"]["best_run"] = _download_artifacts(
            best_run_id,
            out_path / "best_run",
        )

    best_pipeline_id = state.get("best_pipeline_id")
    if best_pipeline_id is not None:
        pipeline_run_id = state["pipeline_run_ids"].get(best_pipeline_id)
        if pipeline_run_id:
            logger.info(
                f"Downloading artifacts for best pipeline run: {pipeline_run_id}"
            )
            state["artifacts"]["best_pipeline"] = _download_artifacts(
                pipeline_run_id,
                out_path / "best_pipeline",
            )

    if not state["artifacts"]:
        logger.info("No best run/pipeline artifacts available to download.")

    return state


state_graph = StateGraph(EvaluationAgentState)

state_graph.add_edge(START, "get_best_run_per_pipeline")
state_graph.add_sequence(
    [
        get_best_run_per_pipeline,
        get_best_run_across_pipelines,
        download_artifacts,
    ]
)
state_graph.add_edge("download_artifacts", END)


evaluation_agent: CompiledStateGraph = state_graph.compile()

print(evaluation_agent.get_graph().draw_mermaid())
