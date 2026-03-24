from typing import Optional, Dict

import pandas as pd
from langgraph.constants import START, END
from langgraph.graph import MessagesState
from langgraph.graph.state import CompiledStateGraph, StateGraph

from automlllm import logger
from automlllm.common.client import get_best_pipeline_run, get_model_from_run_id
from automlllm.execution.utils import get_metric


class EvaluationAgentState(MessagesState):
    experiment_id: str
    pipeline_run_ids: Dict[int, Optional[str]]
    best_run_per_pipeline: Dict[int, str]
    specification_path: str
    validation_metric: str
    maximize: bool
    test_df: pd.DataFrame
    target_feature: str
    best_pipeline_id: Optional[int]
    best_run_id: Optional[str]
    best_test_score: Optional[float]
    test_scores: Dict[int, float]


def get_best_run_per_pipeline(state: EvaluationAgentState) -> EvaluationAgentState:
    state["best_run_per_pipeline"] = {}

    for pipeline_id, pipeline_run_id in state["pipeline_run_ids"].items():
        if pipeline_run_id:
            best_run_id = get_best_pipeline_run(
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
    best_pipeline_id = None

    for pipeline_id, run_id in state["best_run_per_pipeline"].items():
        model = get_model_from_run_id(run_id)
        y_pred = model.predict(X_test)
        score = metric_fn(y_test, y_pred)
        state["test_scores"][pipeline_id] = score
        logger.info(
            f"Pipeline {pipeline_id} (run {run_id}): {state['validation_metric']} = {score}"
        )

        if best_score is None:
            best_score = score
            best_run_id = run_id
            best_pipeline_id = pipeline_id
        elif state["maximize"] and score > best_score:
            best_score = score
            best_run_id = run_id
            best_pipeline_id = pipeline_id
        elif not state["maximize"] and score < best_score:
            best_score = score
            best_run_id = run_id
            best_pipeline_id = pipeline_id

    state["best_run_id"] = best_run_id
    state["best_test_score"] = best_score
    state["best_pipeline_id"] = best_pipeline_id
    return state


state_graph = StateGraph(EvaluationAgentState)

state_graph.add_edge(START, "get_best_run_per_pipeline")
state_graph.add_sequence([get_best_run_per_pipeline, get_best_run_across_pipelines])
state_graph.add_edge("get_best_run_across_pipelines", END)


evaluation_agent: CompiledStateGraph = state_graph.compile()

print(evaluation_agent.get_graph().draw_mermaid())
