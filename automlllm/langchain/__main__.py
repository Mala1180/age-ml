# import uuid
from typing import Optional

import fire
import mlflow
from langchain_core.messages import HumanMessage

from automlllm.langchain import logger
from automlllm.langchain.agent import planning_agent

mlflow.set_experiment("mattia-experiment")
mlflow.openai.autolog()
mlflow.langchain.autolog()


def main(prompt: str = "", dataset_path: Optional[str] = None):
    dataset_path = "resources/datasets/adult.csv"
    specification_path = "resources/automl-specification.yml"
    prompt = "Help me to build a machine learning pipeline for Adult Income Prediction."
    messages = [
        HumanMessage(
            content=[
                {"type": "text", "text": prompt},
                {"type": "text", "text": dataset_path + " is the URI of the dataset. "}
                if dataset_path
                else {},
                {
                    "type": "text",
                    "text": specification_path + " is the URI of the specification. ",
                }
                if specification_path
                else {},
            ]
        )
    ]

    for mode, chunk in planning_agent.stream(
        {"messages": messages},
        stream_mode=["values"],
    ):
        assert isinstance(chunk, dict)
        for step, data in chunk.items():
            logger.info(f"step: {step}")
            logger.info(f"content: {data}")


if __name__ == "__main__":
    fire.Fire(main)
