from pathlib import Path
from typing import Any, List, Literal, Optional, Tuple

import pandas as pd
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, START, MessagesState
from langgraph.graph.state import CompiledStateGraph
from typing_extensions import override

from automlllm.common.model import model
from automlllm.common.types import Pipeline, Step
from automlllm.specification import Specification
from automlllm.specification.validation import SpecificationValidator


class PlanningPipeline(Pipeline):
    @override
    def __str__(self) -> str:
        str_value: str = "Planning Pipeline:\n"
        for i, step in enumerate(self.steps):
            str_value += f"Step {i + 1}: {step.name}"
            if step.content:
                str_value += f" with value {step.content}"
            str_value += "\n"
        return str_value


class PlanningAgentState(MessagesState):
    user_prompt: str
    specification_path: str
    specification: str
    dataset_path: str
    dataset_info: str
    pipeline: PlanningPipeline
    pipeline_feedback: Tuple[bool, Optional[str]]


structured_model = model.with_structured_output(PlanningPipeline)
attempts: int = 0
max_attempts: int = 5


def load_dataset(state: PlanningAgentState) -> PlanningAgentState:
    df: pd.DataFrame = pd.read_csv(Path(state["dataset_path"]))

    dataset_info: str = f"""
        Loaded dataset with {len(df)} rows and {len(df.columns)} columns
        Columns:\n{list(df.columns)}
        Data Types:\n{df.dtypes.to_markdown()}
        Description:\n{df.describe().to_markdown()}
        Preview:\n{df.head().to_markdown()}
    """
    state["messages"] = state["messages"] + [
        AIMessage(content=f"Dataset loaded. \n{dataset_info}")
    ]
    state["dataset_info"] = dataset_info
    return state


def load_specification(state: PlanningAgentState) -> PlanningAgentState:
    content: str = Path(state["specification_path"]).read_text()
    # data: Dict = yaml.safe_load(content)
    # state["messages"] = state["messages"] + [
    #     AIMessage(content=f"Specification loaded. \n{pformat(data)}")
    # ]
    # state["specification"] = yaml.dump(data)
    nl_spec: str = Specification.parse(content).to_natural_language()
    state["messages"] = state["messages"] + [
        AIMessage(content=f"Specification loaded. \n{nl_spec}")
    ]
    state["specification"] = content
    return state


def reasoning_node(state: PlanningAgentState) -> PlanningAgentState:
    reasoning_prompt: str = (
        "Reason on how to generate the pipeline. "
        "Remember that the pipeline must comply with the specification provided "
        "and consider the previous feedbacks if any. "
        "You don't need to generate any sort of code, just reason about the steps to take."
    )

    state["messages"] = state["messages"] + [HumanMessage(content=reasoning_prompt)]

    response: Any = model.invoke(state["messages"])
    state["messages"] = state["messages"] + [AIMessage(content=response.content)]
    return state


def generate_pipeline(state: PlanningAgentState) -> PlanningAgentState:
    local_prompt: str = (
        "Generate the pipeline you consider best for this specific problem.\n"
        "For each step, set 'name' to the step name defined in the specification "
        "and 'content' to the candidate value you choose for that step."
    )
    state["messages"] = state["messages"] + [HumanMessage(content=local_prompt)]
    response = structured_model.invoke(state["messages"])
    assert isinstance(response, PlanningPipeline)
    response.steps = [
        Step(
            name=step.name.lower(),
            content=step.content.lower() if step.content else None,
        )
        for step in response.steps
    ]

    state["messages"] = state["messages"] + [AIMessage(content=str(response))]
    state["pipeline"] = response
    return state


def validate_pipeline(state: PlanningAgentState) -> PlanningAgentState:
    spec: Specification = Specification.parse(state["specification"])
    validator: SpecificationValidator = SpecificationValidator(spec)
    is_valid: bool
    message: Optional[str]
    is_valid, message = validator.validate_pipeline(state["pipeline"].steps)
    if message is None:
        message = "Pipeline is valid according to the specification."
    state["messages"] = state["messages"] + [HumanMessage(content=message)]
    state["pipeline_feedback"] = is_valid, message if not is_valid else None
    return state


def should_terminate(state: PlanningAgentState) -> Literal["reasoning_node", "__end__"]:
    terminate: bool
    terminate, _ = state["pipeline_feedback"]
    global attempts
    attempts += 1
    return "__end__" if terminate or attempts == max_attempts else "reasoning_node"


state_graph: StateGraph = StateGraph(PlanningAgentState)

state_graph.add_sequence(
    [
        load_dataset,
        load_specification,
        reasoning_node,
        generate_pipeline,
        validate_pipeline,
    ]
)
state_graph.add_edge(START, "load_dataset")
state_graph.add_conditional_edges("validate_pipeline", should_terminate)


planning_agent: CompiledStateGraph = state_graph.compile()

prompt: str = (
    "Help me to build a machine learning pipeline for Adult Income Prediction."
)

system_prompt: str = """
    You are a helpful assistant able to design pipelines of steps.
    Your task is to create an ordered pipeline of tasks based on the provided specification.
    A pipeline is a sequence of steps, each with an id and a chosen value.
    The pipeline must respect the specification provided in natural language.
    It is not necessary to include all types of steps in the pipeline (except for the mandatory ones).
    Terminal steps should be the last step in the pipeline.
    Initial steps should be the first step in the pipeline.
    The generated pipeline is always validated and a feedback is provided.
"""


def create_user_prompt(prompt: str) -> List[BaseMessage]:
    return [SystemMessage(content=system_prompt), HumanMessage(content=prompt)]


print(planning_agent.get_graph().draw_mermaid())
