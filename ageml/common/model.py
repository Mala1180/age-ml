"""Resolve the configured backend lazily, including in reused worker processes."""

import os
from functools import lru_cache

import httpx
from langchain_core.runnables import RunnableLambda

from ageml.common.llm_config import current_llm_config


class EnvironmentBearerAuth(httpx.Auth):
    """Read credentials at request time; never store a token in model kwargs."""

    def __init__(self, env_name):
        self.env_name = env_name

    def auth_flow(self, request):
        token = os.environ.get(self.env_name, "").strip()
        if not token:
            raise ValueError(
                f"Missing Ollama API key environment variable: {self.env_name}"
            )
        request.headers["Authorization"] = f"Bearer {token}"
        yield request


@lru_cache(maxsize=8)
def _build_model(config, process_id=None):
    if config.provider == "ollama":
        from langchain_ollama import ChatOllama

        kwargs = (
            {"auth": EnvironmentBearerAuth(config.api_key_env)}
            if config.api_key_env
            else {}
        )
        return ChatOllama(
            model=config.model_name,
            seed=config.seed,
            temperature=config.temperature,
            base_url=config.base_url,
            client_kwargs=kwargs,
            validate_model_on_init=False,
        )
    from langchain_google_genai import ChatGoogleGenerativeAI

    kwargs = {} if config.temperature is None else {"temperature": config.temperature}
    if config.seed is not None:
        if "seed" not in ChatGoogleGenerativeAI.model_fields:
            raise ValueError(
                "This langchain-google-genai version does not support model_seed; upgrade it or leave model_seed unset"
            )
        kwargs["seed"] = config.seed
    return ChatGoogleGenerativeAI(model=config.model_name, **kwargs)


def get_model():
    return _build_model(current_llm_config(), os.getpid())


class ConfiguredModel:
    """Keep module-level structured clients bound to the current run configuration."""

    def invoke(self, messages, **kwargs):
        return get_model().invoke(messages, **kwargs)

    def with_structured_output(self, schema, **kwargs):
        # Resolve at invocation, not agent import, so switching endpoint/model
        # in the same Python process cannot retain a previous backend.
        return RunnableLambda(
            lambda messages: (
                get_model().with_structured_output(schema, **kwargs).invoke(messages)
            )
        )


model = ConfiguredModel()
