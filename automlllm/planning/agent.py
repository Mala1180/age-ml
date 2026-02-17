from pathlib import Path
from typing import List, Literal, Dict, Tuple, Optional, TypedDict

import networkx as nx
import pandas as pd
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, START, MessagesState
from langgraph.graph.state import CompiledStateGraph
from matplotlib import pyplot as plt
from networkx.classes import MultiDiGraph
from networkx.readwrite import json_graph
from pydantic import BaseModel

from automlllm.common.model import model
from automlllm.specification import Specification
from automlllm.specification.validation import SpecificationValidator


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
        "Generate a DIRECTED ACYCLIC GRAPH representing few pipeline paths, those you consider better for this specific problem.\n"
        "Graph can have multiple roots and multiple leaves, but it is not a constraint.\n"
        "The graph must not have cycles.\n"
        "Each edge must explicitly specify direction using keys:\n"
        "  from = source node\n"
        "  to = destination node\n\n"
        "Return ONLY valid JSON that matches this schema:\n"
        "{"
        '  "nodes": [[node_id, value], ...],'
        '  "edges": [{"from_node": "...", "to_node": "..."}, ...]'
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

    plt.figure(figsize=(6, 6))
    pos = nx.spring_layout(graph)
    nx.draw(
        graph,
        pos,
        with_labels=True,
        node_size=2000,
        node_color="lightblue",
        arrowstyle="->",
    )
    plt.show()
    state["messages"] = state["messages"] + [AIMessage(content=str(response))]
    state["pipeline_graph"] = nx.node_link_data(graph)
    return state


def validate_pipeline_graph(state: PlanningAgentState) -> PlanningAgentState:
    graph: MultiDiGraph = json_graph.node_link_graph(state["pipeline_graph"])
    spec = Specification.parse(state["specification"])
    validator = SpecificationValidator(spec)
    is_valid, message = validator.validate_graph(graph)
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

system_prompt: str = """
    You are a helpful assistant able to design pipeline of steps.
    Your task is to create a directed acyclic graph (DAG) representing pipelines of tasks based on the provided specification.
    These pipelines are represented by all the possible paths from roots to leaves in the graph.
    The graph should not represent all the possible pipelines (combinatorial explosion) but only the best ones depending on the specific problem.
    The graph of pipelines must respect the specification provided in natural language.
    It is not necessary to include all types of steps in the graph (except for the mandatory ones)
    Terminal nodes should be the leaf nodes in valid paths
    Initial nodes should be the root nodes in valid paths
    The generated graph is always validated and a feedback is provided.
"""

# Pipeline task names are provided as the keys in the 'steps' section of the specification, under the 'pipeline' key.
# These step names should be the node keys in the graph.
# Values for each step should be chosen among the admissible values defined inside the step object.
# The output should be a comprehensive graph representing all possible pipeline paths.


def create_user_prompt(prompt: str) -> List[BaseMessage]:
    return [SystemMessage(content=system_prompt), HumanMessage(content=prompt)]


print(planning_agent.get_graph().draw_mermaid())
