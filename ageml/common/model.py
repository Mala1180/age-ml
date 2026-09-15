import os

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import SecretStr

load_dotenv()


api_key = SecretStr(os.getenv("OPENROUTER_API_KEY", ""))

model_name: str = os.environ["AGEML_MODEL_NAME"]

# google gemini
model = ChatGoogleGenerativeAI(model=model_name)
