"""Non-secret backend configuration shared by CLI, workers and provenance."""

import os
from dataclasses import asdict, dataclass
from urllib.parse import urlsplit

from dotenv import load_dotenv

from ageml.common import DEFAULT_MODEL_NAME


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    model_name: str
    base_url: str | None = None
    api_key_env: str | None = None

    seed: int | None = None
    temperature: float | None = None

    def public_dict(self):
        return {
            **asdict(self),
            "seed_requested": self.seed,
            "seed_support": "backend determinism is not guaranteed",
        }

    def export(self):
        os.environ["AGEML_MODEL_NAME"] = self.model_name
        os.environ["AGEML_MODEL_PROVIDER"] = self.provider
        for key, value in (
            ("AGEML_MODEL_SEED", None if self.seed is None else str(self.seed)),
            (
                "AGEML_MODEL_TEMPERATURE",
                None if self.temperature is None else str(self.temperature),
            ),
            ("AGEML_MODEL_BASE_URL", self.base_url),
            ("AGEML_MODEL_API_KEY_ENV", self.api_key_env),
        ):
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def resolve_llm_config(
    model_name=DEFAULT_MODEL_NAME,
    model_provider="gemini",
    model_base_url=None,
    model_api_key_env=None,
    model_seed=None,
    model_temperature=None,
):
    load_dotenv()
    if model_seed is not None and (
        type(model_seed) is not int or not 0 <= model_seed <= 2**32 - 1
    ):
        raise ValueError("model_seed must be an unsigned 32-bit integer")
    if model_temperature is not None and not 0 <= model_temperature <= 2:
        raise ValueError("model_temperature must be between 0 and 2")
    if model_provider not in ("gemini", "ollama"):
        raise ValueError("model_provider must be gemini or ollama")
    if model_provider == "gemini":
        if model_base_url is not None or model_api_key_env is not None:
            raise ValueError(
                "model_base_url/model_api_key_env currently require Ollama"
            )
        return LLMConfig(
            "gemini", model_name, seed=model_seed, temperature=model_temperature
        )
    if not model_name or model_name == DEFAULT_MODEL_NAME:
        raise ValueError(
            "Ollama requires an explicit installed model name via model_name"
        )
    if not model_base_url:
        raise ValueError("Ollama requires model_base_url")
    url = urlsplit(model_base_url)
    if (
        url.scheme not in ("http", "https")
        or not url.hostname
        or url.username
        or url.password
        or url.query
        or url.fragment
    ):
        raise ValueError(
            "model_base_url must be an HTTP(S) URL without credentials, query or fragment"
        )
    env_name = "OLLAMA_API_KEY" if model_api_key_env is None else model_api_key_env
    if env_name and not os.environ.get(env_name, "").strip():
        raise ValueError(
            f"Ollama API key environment variable is missing or empty: {env_name}"
        )
    return LLMConfig(
        "ollama",
        model_name,
        model_base_url.rstrip("/"),
        env_name,
        model_seed,
        model_temperature,
    )


def current_llm_config():
    return resolve_llm_config(
        os.environ.get("AGEML_MODEL_NAME", DEFAULT_MODEL_NAME),
        os.environ.get("AGEML_MODEL_PROVIDER", "gemini"),
        os.environ.get("AGEML_MODEL_BASE_URL"),
        os.environ.get("AGEML_MODEL_API_KEY_ENV"),
        int(os.environ["AGEML_MODEL_SEED"])
        if os.environ.get("AGEML_MODEL_SEED")
        else None,
        float(os.environ["AGEML_MODEL_TEMPERATURE"])
        if os.environ.get("AGEML_MODEL_TEMPERATURE")
        else None,
    )
