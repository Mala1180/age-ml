from typing import List

from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain_core.tools import BaseTool

# from langchain_core.tools import Tool
# from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph

from automlllm.common.model import model
from automlllm.common.tools import install_dependency, craft_model, load_csv

# google gemini
# llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-lite")

# local with ollama
# llm = ChatOpenAI(
#     base_url="http://localhost:11434/v1",
#     api_key="dummy",
#     model="ministral-3:8b",
# )


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

tools: List[BaseTool] = [install_dependency, load_csv, craft_model]


executing_agent: CompiledStateGraph = create_agent(
    model=model,
    tools=tools,
    system_prompt=system_prompt,
    checkpointer=checkpointer,
    middleware=[middleware],
)
