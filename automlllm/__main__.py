import uuid
from typing import Optional, List

import fire
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from langchain_core.runnables import RunnableConfig
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
    print(agent.get_graph().draw_mermaid())

    config: RunnableConfig = {"configurable": {"thread_id": str(uuid.uuid4())}}

    # Stream agent progress and LLM tokens until interrupt
    agent_streaming(messages, config)


def agent_streaming(messages: List, config: RunnableConfig):
    inputs = {"messages": messages}
    while inputs:
        for mode, chunk in agent.stream(
            inputs,
            config=config,
            stream_mode=["values"],
        ):
            for step, data in chunk.items():
                logger.info(f"step: {step}")
                logger.info(f"content: {data}")

        state = agent.get_state(config)
        if not state.next:
            inputs = None
            continue

        print("\nAgent interrupted. Actions requiring review:")
        resume_payload = get_user_decision()
        inputs = Command(resume=resume_payload)


def get_user_decision() -> dict:
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
