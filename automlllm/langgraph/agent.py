from pathlib import Path
from typing import List, Literal, Dict, Tuple, Optional, TypedDict

import networkx as nx
import pandas as pd
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, START, MessagesState
from langgraph.graph.state import CompiledStateGraph
from networkx.classes import MultiDiGraph
from networkx.readwrite import json_graph
from pydantic import BaseModel

from automlllm import system_prompt
from automlllm.common.model import model
from automlllm.specification import Specification


class PlanningAgentState(MessagesState):
    user_prompt: str
    specification_path: str
    specification: str
    dataset_path: str
    dataset_info: str
    pipeline_graph: Dict[str, str]
    pipeline_feedback: Tuple[bool, Optional[str]]


class Edge(TypedDict):
    from_node: str
    to_node: str


class PipelineGraph(BaseModel):
    nodes: List[List[str]]
    edges: List[Edge]


structured_model = model.with_structured_output(PipelineGraph)
attempts: int = 0
max_attempts: int = 10


def load_dataset(state: PlanningAgentState) -> PlanningAgentState:
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
        "Reason on how to generate the pipeline graph. "
        "Remember that the graph must comply with the specification provided "
        "and consider the previous feedbacks if any. "
        "You don't need to generate any sort of code, just reason about the steps to take."
    )

    state["messages"] = state["messages"] + [HumanMessage(content=reasoning_prompt)]

    response = model.invoke(state["messages"])
    state["messages"] = state["messages"] + [AIMessage(content=response.content)]
    return state


def generate_pipeline_graph(state: PlanningAgentState) -> PlanningAgentState:
    local_prompt: str = (
        "Generate a DIRECTED graph representing the pipeline.\n"
        "Each edge must explicitly specify direction using keys:\n"
        "  from = source node\n"
        "  to = destination node\n\n"
        "Return ONLY valid JSON that matches this schema:\n"
        "{"
        '  "nodes": [[node_id, value], ...],'
        '  "edges": [{"from": "...", "to": "..."}, ...]'
        "}"
    )
    state["messages"] = state["messages"] + [HumanMessage(content=local_prompt)]
    response = structured_model.invoke(state["messages"])
    assert isinstance(response, PipelineGraph)
    response.nodes = [[k.lower(), v.lower()] for k, v in response.nodes]
    response.edges = [
        {"from_node": edge["from_node"].lower(), "to_node": edge["to_node"].lower()}
        for edge in response.edges
    ]
    graph: MultiDiGraph = nx.MultiDiGraph()
    for node_id, node_value in response.nodes:
        graph.add_node(node_id, value=node_value)
    for edge in response.edges:
        graph.add_edge(edge["from_node"], edge["to_node"])

    state["messages"] = state["messages"] + [AIMessage(content=str(response))]
    state["pipeline_graph"] = nx.node_link_data(graph)
    return state


def validate_pipeline_graph(state: PlanningAgentState) -> PlanningAgentState:
    graph: MultiDiGraph = json_graph.node_link_graph(state["pipeline_graph"])
    validator = Specification.parse(state["specification"])
    is_valid, message = validator.validate(graph)
    if message is None:
        message = "Graph is valid according to the specification."
    state["messages"] = state["messages"] + [HumanMessage(content=message)]
    state["pipeline_feedback"] = is_valid, message if not is_valid else None
    return state


def should_terminate(state: PlanningAgentState) -> Literal["reasoning_node", "__end__"]:
    terminate, _ = state["pipeline_feedback"]
    global attempts
    attempts += 1
    return "__end__" if terminate or attempts == max_attempts else "reasoning_node"


state_graph = StateGraph(PlanningAgentState)

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
