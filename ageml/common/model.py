import os

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

from ageml.common import DEFAULT_MODEL_NAME

load_dotenv()

# `ageml.app.main` exports AGEML_MODEL_NAME from its --model_name before
# importing the agents, so that the backend can be picked per invocation.
model_name: str = os.environ.get("AGEML_MODEL_NAME", DEFAULT_MODEL_NAME)

# google gemini
model = ChatGoogleGenerativeAI(model=model_name)
