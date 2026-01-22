from langchain.agents import create_agent

# from langchain.agents.middleware import HumanInTheLoopMiddleware
# from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph

from automlllm.model import model
from automlllm.tools import generate_computational_graph

system_prompt: str = """
    You are a helpful assistant able to craft tools in order to train models for supervised learning. 
    Your objective is to craft a tool depending on the problem and dataset provided by the user, and provide to the latter the trained model. 
"""


# checkpointer = MemorySaver()
#
# middleware = HumanInTheLoopMiddleware(
#     interrupt_on={
#         "generate_computational_graph": True,
#     }
# )

agent: CompiledStateGraph = create_agent(
    model=model,
    tools=[generate_computational_graph],
    system_prompt=system_prompt,
    # checkpointer=checkpointer,
    # middleware=[middleware],
)
