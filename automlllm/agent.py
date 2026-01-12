import os

import mlflow
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware

# from langchain_core.tools import Tool
# from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph

from automlllm.tools import tools

load_dotenv()

mlflow.set_experiment("mattia-experiment")
mlflow.openai.autolog()
mlflow.langchain.autolog()

# google gemini
# llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-lite")

# local with ollama
# llm = ChatOpenAI(
#     base_url="http://localhost:11434/v1",
#     api_key="dummy",
#     model="ministral-3:8b",
# )

def api_key() -> str:
    return os.environ["OPENROUTER_API_KEY"]

# openrouter
llm = ChatOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key,
    model="mistralai/devstral-2512:free",
)


system_prompt: str = """
    You are a helpful assistant able to craft tools in order to train models for supervised learning. 
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

agent: CompiledStateGraph = create_agent(
    model=llm,
    tools=tools,
    system_prompt=system_prompt,
    checkpointer=checkpointer,
    middleware=[middleware],
)
