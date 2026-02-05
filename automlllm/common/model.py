import os

from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

load_dotenv()


api_key = SecretStr(os.getenv("OPENROUTER_API_KEY", ""))

# model_name: str = "deepseek/deepseek-r1-0528:free"
model_name: str = "openai/gpt-oss-120b:free"

# openrouter
# model = ChatOpenAI(
#     base_url="https://openrouter.ai/api/v1",
#     api_key=api_key,
#     model=model_name,
# )

# # google gemini
# model = ChatGoogleGenerativeAI(model="gemini-2.0-flash-lite")
#
# local with ollama
model = ChatOllama(
    model="llama3.1:8b",
    temperature=0.0,
    # num_ctx=3072,
    num_predict=-2,  # fill context
)
