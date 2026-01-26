import pandas as pd
from langchain_core.tools import tool


@tool
def load_dataset(uri: str) -> str:
    """
    Load a CSV dataset from a URI and return a summary.
    The URI can be a local path or an http(s) URL.
    """
    df = pd.read_csv(uri)

    return (
        f"Loaded dataset with {len(df)} rows and {len(df.columns)} columns.\n"
        f"Columns:\n{list(df.columns)}\n"
        f"Data Types:\n{df.dtypes.to_markdown()}\n"
        f"Description:\n{df.describe().to_markdown()}\n"
        f"Preview:\n{df.head().to_markdown()}"
    )
