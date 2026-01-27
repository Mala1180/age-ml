from typing import List

from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain_core.tools import BaseTool

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph

from automlllm.common.model import model
from automlllm.common.tools import load_dataset
from automlllm.executing.tools import install_dependency, craft_model


system_prompt: str = """
    You are a helpful assistant able to craft models for supervised learning. 
    Your objective is to craft a tool depending on the problem and dataset provided by the user, and provide to the latter the trained model. 
"""


checkpointer = MemorySaver()

middleware = HumanInTheLoopMiddleware(
    interrupt_on={
        "install_dependency": False,
        "load_csv": False,
        "craft_model": True,
    }
)

tools: List[BaseTool] = [install_dependency, load_dataset, craft_model]


executing_agent: CompiledStateGraph = create_agent(
    model=model,
    tools=tools,
    system_prompt=system_prompt,
    checkpointer=checkpointer,
    middleware=[middleware],
)

# config: RunnableConfig = {"configurable": {"thread_id": str(uuid.uuid4())}}
# agent_streaming(messages, config)
#
# def agent_streaming(messages: List, config: RunnableConfig):
#     inputs: Optional[Dict | Command] = {"messages": messages}
#     while inputs:
#         for mode, chunk in planning_agent.stream(
#             inputs,
#             config=config,
#             stream_mode=["values"],
#         ):
#             assert isinstance(chunk, dict)
#             for step, data in chunk.items():
#                 logger.info(f"step: {step}")
#                 logger.info(f"content: {data}")
#
#         state = planning_agent.get_state(config)
#         if not state.next:
#             inputs = None
#             continue
#
#         print("\nAgent interrupted. Actions requiring review:")
#         resume_payload: Dict[str, Any] = get_user_decision()
#         inputs = Command(resume=resume_payload)
#
#
# def get_user_decision() -> Dict[str, Any]:
#     import json
#
#     while True:
#         choice = input("\nDecision [a]pprove, [r]eject, [e]dit: ").strip().lower()
#
#         if choice in ["a", "approve", ""]:
#             return {"decisions": [{"type": "approve"}]}
#
#         elif choice in ["r", "reject"]:
#             reason = input("Rejection reason: ")
#             return {"decisions": [{"type": "reject", "message": reason}]}
#
#         elif choice in ["e", "edit"]:
#             print("Enter new arguments as JSON:")
#             try:
#                 args_str = input("Args: ")
#                 new_args = json.loads(args_str)
#
#                 tool_name = input("Tool name (press enter to guess current): ").strip()
#
#                 if not tool_name:
#                     print("Tool name is required for edit.")
#                     continue
#
#                 return {
#                     "decisions": [
#                         {
#                             "type": "edit",
#                             "edited_action": {"name": tool_name, "args": new_args},
#                         }
#                     ]
#                 }
#             except json.JSONDecodeError:
#                 print("Invalid JSON.")
#                 continue
#         else:
#             print("Invalid choice.")
