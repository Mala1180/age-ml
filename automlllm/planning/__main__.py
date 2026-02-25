from typing import Optional, List

import fire
import mlflow
from langchain_core.messages import BaseMessage

from automlllm import logger
from automlllm.planning.agent import planning_agent, create_user_prompt

mlflow.set_experiment("mattia-experiment")
mlflow.openai.autolog()
mlflow.langchain.autolog()


def main(prompt: str = "", dataset_path: Optional[str] = None):
    dataset_path = "resources/datasets/adult.csv"
    specification_path = "resources/adult-specification.yml"
    prompt = "Help me to build a machine learning pipeline for Adult Income Prediction."
    messages: List[BaseMessage] = create_user_prompt(prompt)

    for mode, chunk in planning_agent.stream(
        {
            "messages": messages,
            "user_prompt": prompt,
            "specification_path": specification_path,
            "dataset_path": dataset_path,
        },
        stream_mode=["values"],
    ):
        assert isinstance(chunk, dict)
        for step, data in chunk.items():
            logger.info(f"step: {step}")
            logger.info(f"content: {data}")


if __name__ == "__main__":
    fire.Fire(main)
