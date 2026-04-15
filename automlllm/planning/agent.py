import random
from pathlib import Path
from typing import List

import pandas as pd
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.constants import END
from langgraph.graph import StateGraph, START, MessagesState
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel

from automlllm import logger
from automlllm.common.client import (
    enable_mlflow_llm_autologging,
)
from automlllm.common.model import model
from automlllm.planning.solver import (
    create_solver,
    enumerate_solutions,
    convert_solution_to_pipeline,
)
from automlllm.planning.types import PlanningPipeline
from automlllm.specification import Specification, Constraint
from automlllm.specification.types import TrueCondition


class PlanningAgentState(MessagesState):
    specification_path: str
    specification: Specification
    dataset_path: str
    dataset_info: str
    target_feature: str
    max_pipelines: int
    pipelines: List[PlanningPipeline]


class ConditionVerification(BaseModel):
    is_condition_met: bool
    explanation: str


condition_verification_model = model.with_structured_output(ConditionVerification)
attempts: int = 0
generation_attempts: int = 5


def load_dataset(state: PlanningAgentState) -> PlanningAgentState:
    enable_mlflow_llm_autologging()
    df: pd.DataFrame = pd.read_csv(Path(state["dataset_path"]))

    dataset_info: str = f"""
        Loaded dataset with {len(df)} rows and {len(df.columns)} columns
        Columns:\n{list(df.columns)}
        Target feature: {state["target_feature"]}
        Data Types:\n{df.dtypes.to_markdown()}
        Description:\n{df.describe().to_markdown()}
        Preview:\n{df.head().to_markdown()}
    """
    state["messages"] = state["messages"] + [
        SystemMessage(content=system_prompt),
        AIMessage(content=f"Dataset loaded. \n{dataset_info}"),
    ]
    state["dataset_info"] = dataset_info
    return state


def load_specification(state: PlanningAgentState) -> PlanningAgentState:
    content: str = Path(state["specification_path"]).read_text()
    state["specification"] = Specification.parse(content)
    return state


def translate_semantic_conditions(state: PlanningAgentState) -> PlanningAgentState:
    for semantic_constraint in state["specification"].semantic_constraints:
        prompt: str = (
            "Given the following condition, determine if the condition is met.\n"
            "If the condition is met, return 'is_condition_met' as True, otherwise False. "
            "Constraint Condition:\n"
            f"{semantic_constraint.condition}\n"
        )

        state["messages"] = state["messages"] + [HumanMessage(content=prompt)]
        response = condition_verification_model.invoke(state["messages"])
        assert isinstance(response, ConditionVerification)
        state["messages"] = state["messages"] + [
            AIMessage(content=response.explanation)
        ]
        if response.is_condition_met:
            state["specification"].constraints.append(
                Constraint(
                    condition=TrueCondition(),
                    require=semantic_constraint.require,
                    forbid=semantic_constraint.forbid,
                )
            )
    return state


def generate_pipelines(state: PlanningAgentState) -> PlanningAgentState:
    solver = create_solver(state["specification"])
    state["pipelines"] = []
    for solution in enumerate_solutions(solver):
        pipeline: PlanningPipeline = convert_solution_to_pipeline(
            solution, state["specification"]
        )
        state["pipelines"].append(pipeline)
    logger.info(f"Generated pipelines: {len(state['pipelines'])}")
    return state


def select_pipelines(state: PlanningAgentState) -> PlanningAgentState:
    max_pipelines: int = state["specification"].budgets.pipelines
    all_pipelines: List[PlanningPipeline] = state["pipelines"]
    if len(state["pipelines"]) > max_pipelines:
        state["pipelines"] = random.sample(all_pipelines, k=max_pipelines)
    logger.info(
        f"Picked {len(state['pipelines'])} pipelines out of {len(all_pipelines)} candidates (budget was {max_pipelines})"
    )
    return state


state_graph: StateGraph = StateGraph(PlanningAgentState)

state_graph.add_sequence(
    [
        load_dataset,
        load_specification,
        translate_semantic_conditions,
        generate_pipelines,
        select_pipelines,
    ]
)
state_graph.add_edge(START, "load_dataset")
state_graph.add_edge("select_pipelines", END)

system_prompt: str = """
    You are an agent that evaluates whether dataset conditions are satisfied.
    Before evaluating any condition you MUST:
    
    1. Determine the most likely target feature of the dataset.
    2. Explain why it is the target feature.
    3. Use ONLY that target feature when evaluating the condition.
    
    Important rules:
    - The target feature is usually the column representing the prediction label.
    - Column names like "target", "label", "class", "y", "outcome" are strong indicators.
    - Once the target feature is chosen, do NOT change it across different conditions.
"""


planning_agent: CompiledStateGraph = state_graph.compile()

print(planning_agent.get_graph().draw_mermaid())
