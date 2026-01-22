from typing import Tuple, Any, List

import pandas as pd
from langchain_core.tools import tool
import networkx as nx
from networkx import Graph


@tool
def install_dependency(package_name: str) -> str:
    """Tool that installs a python package using poetry.
    The input should be the name of the package to install.
    Example: "numpy"
    """
    import subprocess

    try:
        subprocess.check_call(["poetry", "add", package_name])
        return f"Package {package_name} installed successfully."
    except subprocess.CalledProcessError as e:
        return str(e)


@tool
def load_csv(uri: str) -> str:
    """
    Load a CSV dataset from a URI and return a summary.
    The URI can be a local path or an http(s) URL.
    """
    df = pd.read_csv(uri)

    return (
        f"Loaded dataset with {len(df)} rows and {len(df.columns)} columns.\n"
        f"Columns: {list(df.columns)}\n"
        f"Preview:\n{df.head().to_markdown()}"
    )


@tool
def craft_model(code: str) -> str:
    """Execute Python code and return the output.
    The input code should be a function containing the training of a model."""
    # The input code should also include the autolog of mlflow for tracking and in particular for log the artifact."""
    import re

    def sanitize_input(query: str) -> str:
        """Sanitize input to the python REPL.
        Remove whitespace, backtick & python
        (if llm mistakes python console as terminal)
        """
        query = re.sub(r"^(\s|`)*(?i:python)?\s*", "", query)
        query = re.sub(r"(\s|`)*$", "", query)
        return query

    try:
        import mlflow

        mlflow.autolog()
        # WARNING: Using eval/exec can be dangerous. This is just for demonstration purposes.
        namespace: dict = {}
        exec(sanitize_input(code), namespace, namespace)
        return str("Model crafted and trained successfully.")
    except Exception as e:
        return str(e)


@tool
def generate_computational_graph(
    nodes: List[Tuple[str, Any]], edges: List[Tuple[str, str]]
) -> dict:
    """Generate a graph given nodes and edges.
    Nodes are tuples of (node_id, node_value).
    Edges are tuples of (from_node_id, to_node_id).
    """
    graph: Graph = nx.DiGraph()
    for node_id, node_value in nodes:
        graph.add_node(node_id, value=node_value)
    for from_node, to_node in edges:
        graph.add_edge(from_node, to_node)
    return nx.node_link_data(graph)
