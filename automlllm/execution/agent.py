from pathlib import Path
from typing import Literal, Dict, List

import networkx as nx
from langchain_core.messages import AIMessage
from langgraph.graph import StateGraph, START, MessagesState
from langgraph.graph.state import CompiledStateGraph
from networkx import MultiDiGraph
from networkx.readwrite import json_graph

from automlllm.execution.code_generation_agent import (
    code_generation_agent,
)
from automlllm.execution.pipeline import Step, Pipeline


class ExecutionAgentState(MessagesState):
    dataset_path: str
    dataset_info: str
    pipeline_graph: Dict[str, str]
    planned_pipelines: List[Pipeline]
    current_pipeline: int
    generated_code: str


def load_pipelines(state: ExecutionAgentState) -> ExecutionAgentState:
    graph: MultiDiGraph = json_graph.node_link_graph(state["pipeline_graph"])
    roots = [n for n, d in graph.in_degree() if d == 0]
    leaves = [n for n, d in graph.out_degree() if d == 0]
    all_paths: List[Pipeline] = []
    index: int = 1
    for root in roots:
        for leaf in leaves:
            for path in nx.all_simple_paths(graph, root, leaf):
                path_with_values: List[Step] = list(
                    map(
                        lambda node: Step(
                            name=node, content=graph.nodes[node]["value"]
                        ),
                        path,
                    )
                )
                all_paths.append(Pipeline(id=index, steps=path_with_values))
                index += 1

    state["planned_pipelines"] = all_paths
    return state


def generate_code_for_pipeline(state: ExecutionAgentState) -> ExecutionAgentState:
    if "current_pipeline" not in state:
        state["current_pipeline"] = 0

    pipeline: Pipeline = state["planned_pipelines"][state["current_pipeline"]]
    code_gen_state: Dict = code_generation_agent.invoke(
        {
            "dataset_path": state["dataset_path"],
            "dataset_info": state["dataset_info"],
            "pipeline": pipeline,
        }
    )
    pipeline = code_gen_state["pipeline"]
    out_dir = Path(f"out/pipeline_{pipeline.id}")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "code.py").write_text(pipeline.code, encoding="utf-8")
    (out_dir / "explanation.md").write_text(pipeline.explanation, encoding="utf-8")
    return state


def iterate_over_pipelines(
    state: ExecutionAgentState,
) -> Literal["generate_code_for_pipeline", "__end__"]:
    if state["current_pipeline"] + 1 < len(state["planned_pipelines"]):
        state["current_pipeline"] += 1
        return "generate_code_for_pipeline"
    else:
        # return "execute_code"
        return "__end__"


def execute_code(state: ExecutionAgentState) -> ExecutionAgentState:
    try:
        import mlflow

        mlflow.autolog()
        # WARNING: Using eval/exec can be dangerous. This is just for demonstration purposes.
        namespace: dict = {}
        exec(state["generated_code"], namespace, namespace)
    except Exception as e:
        state["messages"] = state["messages"] + [
            AIMessage(content=f"Error during code execution: {str(e)}")
        ]

    return state


# def should_terminate(
#     state: ExecutionAgentState,
# ) -> Literal["generate_code_for_step", "__end__"]:
#     return "__end__"


state_graph = StateGraph(ExecutionAgentState)

state_graph.add_sequence(
    [
        load_pipelines,
        generate_code_for_pipeline,
    ]
)
state_graph.add_edge(START, "load_pipelines")
state_graph.add_conditional_edges("generate_code_for_pipeline", iterate_over_pipelines)
# state_graph.add_node("execute_code", execute_code)
# state_graph.add_conditional_edges("execute_code", should_terminate)

# state_graph.add_edge("execute_code", END)

execution_agent: CompiledStateGraph = state_graph.compile()


system_prompt: str = """
    You are an expert of machine learning and data science.
    Your task is to help the user to generate a machine learning pipeline in python.
    You will be provided with a dataset and a graph representing the pipeline to implement.
    You must ensure that the generated machine learning code is compliant with the provided graph.
    You will generate the code step by step, i.e. node by node of the graph.
"""


print(execution_agent.get_graph().draw_mermaid())
