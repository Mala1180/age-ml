import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
# from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()


def api_key() -> str:
    return os.environ["OPENROUTER_API_KEY"]


# openrouter
model = ChatOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key,
    model="mistralai/devstral-2512:free",
)


# # google gemini
# llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-lite")
#
# # local with ollama
# llm = ChatOpenAI(
#     base_url="http://localhost:11434/v1",
#     api_key="dummy",
#     model="ministral-3:8b",
# )
