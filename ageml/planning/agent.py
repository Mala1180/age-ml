import json
import random
from pathlib import Path

import pandas as pd
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.constants import END
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel

from ageml import logger
from ageml.common.client import (
    enable_mlflow_llm_autologging,
)
from ageml.common.model import model
from ageml.planning.solver import (
    create_solver,
    enumerate_solutions,
)
from ageml.planning.solver.utils import convert_solution_to_pipeline
from ageml.planning.types import PlanningPipeline
from ageml.specification import Constraint, Specification
from ageml.specification.types import TrueCondition


class PlanningAgentState(MessagesState):
    specification_path: str
    run_seed: int
    specification: Specification
    train_df: pd.DataFrame
    dataset_info: str
    target_feature: str
    max_pipelines: int
    pipelines: list[PlanningPipeline]
    pipelines_found: int


class ConditionVerification(BaseModel):
    is_condition_met: bool
    explanation: str


condition_verification_model = model.with_structured_output(ConditionVerification)
attempts: int = 0
generation_attempts: int = 5


def load_dataset(state: PlanningAgentState) -> PlanningAgentState:
    enable_mlflow_llm_autologging()
    df: pd.DataFrame = state["train_df"]

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
            f"{semantic_constraint.condition!s}"
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
    state["pipelines_found"] = len(state["pipelines"])
    logger.info(f"Generated pipelines: {state['pipelines_found']}")
    return state


def select_pipelines(state: PlanningAgentState) -> PlanningAgentState:
    max_pipelines: int = state["specification"].budgets.pipelines
    all_pipelines: list[PlanningPipeline] = sorted(
        state["pipelines"],
        key=lambda p: json.dumps(p.model_dump(mode="json"), sort_keys=True),
    )
    state["pipelines"] = all_pipelines
    if len(state["pipelines"]) > max_pipelines:
        state["pipelines"] = random.Random(state.get("run_seed", 42)).sample(
            all_pipelines, k=max_pipelines
        )
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
    Evaluate dataset conditions using only the provided training data.
    Use the explicitly configured target feature for every condition; never infer another target.
"""

planning_agent: CompiledStateGraph = state_graph.compile()
