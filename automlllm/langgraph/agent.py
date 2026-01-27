from pathlib import Path
from pprint import pformat
from typing import List, Tuple, Optional, Literal, Dict

import mlflow
import networkx as nx
import pandas as pd
import yaml
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, START, MessagesState
from langgraph.graph.state import CompiledStateGraph
from networkx.classes import MultiDiGraph
from networkx.readwrite import json_graph
from pydantic import BaseModel

from automlllm import system_prompt
from automlllm.common.model import model
from automlllm.planning.validation import Validator

mlflow.set_experiment("mattia-experiment")
mlflow.openai.autolog()
mlflow.langchain.autolog()


class AgentState(MessagesState):
    user_prompt: str
    specification_path: str
    specification: str
    dataset_path: str
    dataset_info: str
    pipeline_graph: Dict[str, str]
    feedback: Tuple[bool, Optional[str]]


class PipelineGraph(BaseModel):
    nodes: List[Tuple[str, str]]
    edges: List[Tuple[str, str]]


structured_model = model.with_structured_output(PipelineGraph)
attempts: int = 0
max_attempts: int = 5


def load_dataset(state: AgentState) -> AgentState:
    df = pd.read_csv(Path(state["dataset_path"]))

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


def load_specification(state: AgentState) -> AgentState:
    content: str = Path(state["specification_path"]).read_text()
    data: Dict = yaml.safe_load(content)
    state["messages"] = state["messages"] + [
        AIMessage(content=f"Specification loaded. \n{pformat(data)}")
    ]
    state["specification"] = yaml.dump(data)
    return state


def reasoning_node(state: AgentState) -> AgentState:
    if "feedback" in state:
        state["messages"] = state["messages"] + [
            HumanMessage(content=state["feedback"][1]),
        ]
    reasoning_prompt: str = (
        "Reason on how to generate the pipeline graph."
        "Remember that the graph must comply with the specification provided "
        "and consider the previous feedbacks if any."
    )

    state["messages"] = state["messages"] + [HumanMessage(content=reasoning_prompt)]

    response = model.invoke(state["messages"])
    state["messages"] = state["messages"] + [AIMessage(content=response.content)]
    return state


def generate_pipeline_graph(state: AgentState) -> AgentState:
    local_prompt: str = (
        "Generate a directed graph where "
        "nodes are tuples of (node_id, node_value) "
        "and edges are tuples of (from_node_id, to_node_id)"
    )
    state["messages"] = state["messages"] + [HumanMessage(content=local_prompt)]
    response = structured_model.invoke(state["messages"])
    assert isinstance(response, PipelineGraph)
    response.nodes = [(k.lower(), v.lower()) for k, v in response.nodes]
    response.edges = [(f.lower(), t.lower()) for f, t in response.edges]
    graph: MultiDiGraph = nx.MultiDiGraph()
    for node_id, node_value in response.nodes:
        graph.add_node(node_id, value=node_value)
    for from_node, to_node in response.edges:
        graph.add_edge(from_node, to_node)

    state["messages"] = state["messages"] + [AIMessage(content=str(response))]
    state["pipeline_graph"] = nx.node_link_data(graph)
    return state


def validate_pipeline_graph(state: AgentState) -> AgentState:
    graph: MultiDiGraph = json_graph.node_link_graph(state["pipeline_graph"])
    validator = Validator(state["specification"])
    is_valid, message = validator.validate(graph)
    if message is None:
        message = "Graph is valid according to the specification."
    state["messages"] = state["messages"] + [HumanMessage(content=message)]
    state["feedback"] = (is_valid, message)
    return state


def should_terminate(state: AgentState) -> Literal["reasoning_node", "__end__"]:
    is_valid, _ = state["feedback"]
    global attempts
    attempts += 1
    return "__end__" if is_valid or attempts == max_attempts else "reasoning_node"


state_graph = StateGraph(AgentState)

state_graph.add_sequence(
    [
        load_dataset,
        load_specification,
        reasoning_node,
        generate_pipeline_graph,
        validate_pipeline_graph,
    ]
)
state_graph.add_edge(START, "load_dataset")
state_graph.add_conditional_edges("validate_pipeline_graph", should_terminate)


planning_agent: CompiledStateGraph = state_graph.compile()

prompt: str = (
    "Help me to build a machine learning pipeline for Adult Income Prediction."
)


def create_user_prompt(prompt: str) -> List[BaseMessage]:
    return [SystemMessage(content=system_prompt), HumanMessage(content=prompt)]


print(planning_agent.get_graph().draw_mermaid())
