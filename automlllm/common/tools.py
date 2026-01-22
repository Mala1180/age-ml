import pandas as pd
from langchain_core.tools import tool


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
