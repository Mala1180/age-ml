from typing import Dict

import fire
import mlflow
import networkx as nx
import pandas as pd
from networkx import MultiDiGraph

from automlllm.execution.agent import execution_agent
from automlllm.planning import logger
from resources import get_resource_path

mlflow.set_experiment("mattia-experiment")
mlflow.openai.autolog()
mlflow.langchain.autolog()


def main():
    dataset_path = "datasets/adult.csv"
    # prompt = "Help me to build a machine learning pipeline for Adult Income Prediction."
    df = pd.read_csv(get_resource_path(dataset_path))
    dataset_info: str = f"""
            Loaded dataset with {len(df)} rows and {len(df.columns)} columns
            Columns:\n{list(df.columns)} 
            Data Types:\n{df.dtypes.to_markdown()} 
            Description:\n{df.describe().to_markdown()} 
            Preview:\n{df.head().to_markdown()}
        """

    pipeline_mock: MultiDiGraph = MultiDiGraph()
    pipeline_mock.add_node("imputation", value="simple_imputer")
    pipeline_mock.add_node("classification", value="rf")
    pipeline_mock.add_edge("imputation", "classification")
    pipeline_mock_dict = nx.node_link_data(pipeline_mock)

    initial_state: Dict = {
        "dataset_path": dataset_path,
        "dataset_info": dataset_info,
        "pipeline_graph": pipeline_mock_dict,
        "current_node": None,
        "generate_code": "",
    }
    for mode, chunk in execution_agent.stream(
        initial_state,
        stream_mode=["values"],
    ):
        assert isinstance(chunk, dict)
        for step, data in chunk.items():
            logger.info(f"step: {step}")
            logger.info(f"content: {data}")


if __name__ == "__main__":
    fire.Fire(main)
