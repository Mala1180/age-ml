# import uuid
from typing import Optional, List, Dict, Any

import fire
import mlflow
from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from automlllm import logger
from automlllm.planning.agent import planning_agent, create_user_prompt

# from automlllm.executingagent import executing_agent

mlflow.set_experiment("mattia-experiment")
mlflow.openai.autolog()
mlflow.langchain.autolog()


def main(prompt: str = "", dataset_path: Optional[str] = None):
    prompt = "Help me to build a machine learning pipeline for Adult Income Prediction."
    messages: List[BaseMessage] = create_user_prompt(prompt)
    dataset_path = "resources/datasets/adult.csv"
    specification_path = "resources/automl-specification.yml"

    # config: RunnableConfig = {"configurable": {"thread_id": str(uuid.uuid4())}}
    config: RunnableConfig = {}

    for mode, chunk in planning_agent.stream(
        {
            "messages": messages,
            "user_prompt": prompt,
            "specification_path": specification_path,
            "dataset_path": dataset_path,
        },
        config=config,
        stream_mode=["values"],
    ):
        assert isinstance(chunk, dict)
        for step, data in chunk.items():
            logger.info(f"step: {step}")
            logger.info(f"content: {data}")


def agent_streaming(messages: List, config: RunnableConfig):
    inputs: Optional[Dict | Command] = {"messages": messages}
    while inputs:
        for mode, chunk in planning_agent.stream(
            inputs,
            config=config,
            stream_mode=["values"],
        ):
            assert isinstance(chunk, dict)
            for step, data in chunk.items():
                logger.info(f"step: {step}")
                logger.info(f"content: {data}")

        state = planning_agent.get_state(config)
        if not state.next:
            inputs = None
            continue

        print("\nAgent interrupted. Actions requiring review:")
        resume_payload: Dict[str, Any] = get_user_decision()
        inputs = Command(resume=resume_payload)


def get_user_decision() -> Dict[str, Any]:
    import json

    while True:
        choice = input("\nDecision [a]pprove, [r]eject, [e]dit: ").strip().lower()

        if choice in ["a", "approve", ""]:
            return {"decisions": [{"type": "approve"}]}

        elif choice in ["r", "reject"]:
            reason = input("Rejection reason: ")
            return {"decisions": [{"type": "reject", "message": reason}]}

        elif choice in ["e", "edit"]:
            print("Enter new arguments as JSON:")
            try:
                args_str = input("Args: ")
                new_args = json.loads(args_str)

                tool_name = input("Tool name (press enter to guess current): ").strip()

                if not tool_name:
                    print("Tool name is required for edit.")
                    continue

                return {
                    "decisions": [
                        {
                            "type": "edit",
                            "edited_action": {"name": tool_name, "args": new_args},
                        }
                    ]
                }
            except json.JSONDecodeError:
                print("Invalid JSON.")
                continue
        else:
            print("Invalid choice.")


if __name__ == "__main__":
    fire.Fire(main)
