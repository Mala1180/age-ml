from typing import Optional

import fire
from langchain_core.messages import HumanMessage

from automlllm import logger
from automlllm.agent import agent


def main(prompt: str = "", dataset_path: Optional[str] = None):
    prompt = (
        "Please help me to build a machine learning model for Adult Income Prediction."
    )
    dataset_path = "resources/datasets/adult.csv"

    messages = [
        HumanMessage(
            content=[
                {"type": "text", "text": prompt},
                {"type": "text", "text": dataset_path + " is the URI of the dataset"}
                if dataset_path
                else {},
            ]
        ),
        # AIMessage(
        #     "What kind of problem am I facing? "
        #     "Does dataset need preprocessing? "
        #     "Which are the best model and hyperparameters to solve it?"
        # ),
    ]

    for chunk in agent.stream({"messages": messages}, stream_mode="updates"):
        for step, data in chunk.items():
            logger.info(f"step: {step}")
            logger.info(f"content: {data['messages'][-1].content_blocks}")


if __name__ == "__main__":
    fire.Fire(main)
