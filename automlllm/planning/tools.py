from pathlib import Path
from typing import Tuple, Any, List, Dict

import networkx as nx
import yaml
from langchain_core.tools import tool
from networkx import MultiDiGraph
from networkx.readwrite import json_graph

from automlllm.planning.validation import Validator


@tool
def load_yaml(uri: str) -> str:
    """Load a YAML file from a URI and return its content as a string.
    The URI can be a local path or an http(s) URL.
    """
    content = Path(uri).read_text()
    data = yaml.safe_load(content)
    return yaml.dump(data)


@tool
def generate_pipeline_graph(
    nodes: List[Tuple[str, Any]], edges: List[Tuple[str, str]]
) -> Dict:
    """Generate a MultiDiGraph given nodes and edges.
    Nodes are tuples of (node_id, node_value).
    Edges are tuples of (from_node_id, to_node_id).
    """
    graph: MultiDiGraph = nx.MultiDiGraph()
    for node_id, node_value in nodes:
        graph.add_node(node_id, value=node_value)
    for from_node, to_node in edges:
        graph.add_edge(from_node, to_node)
    return nx.node_link_data(graph)


@tool
def validate_pipeline_graph(graph_data: dict, spec: str) -> str:
    """Validate a pipeline graph against a specification.
    The graph is provided in node-link format as a dictionary.
    The specification is a YAML string defining the validation rules.
    """
    graph: MultiDiGraph = json_graph.node_link_graph(graph_data)
    validator = Validator(spec)
    is_valid, message = validator.validate(graph)
    if is_valid:
        return "Graph is valid according to the specification."
    else:
        return f"Graph validation failed: {message}"
