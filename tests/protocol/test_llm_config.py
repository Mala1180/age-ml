"""Backend configuration and authenticated Ollama requests, all offline."""

import json
from dataclasses import replace

import httpx
import pytest
from pydantic import BaseModel

from ageml.common.llm_config import resolve_llm_config
from ageml.common.model import ConfiguredModel, EnvironmentBearerAuth, _build_model


def test_provider_validation_and_public_provenance(monkeypatch):
    monkeypatch.setenv("TEST_OLLAMA_KEY", "sentinel-credential")
    config = resolve_llm_config(
        "local-model", "ollama", "http://host:11434/", "TEST_OLLAMA_KEY"
    )
    assert config.base_url == "http://host:11434"
    assert "sentinel-credential" not in json.dumps(config.public_dict())
    assert config.public_dict()["api_key_env"] == "TEST_OLLAMA_KEY"
    assert resolve_llm_config().provider == "gemini"
    with pytest.raises(ValueError, match="missing or empty"):
        resolve_llm_config(
            "local-model", "ollama", "http://host:11434", "UNDEFINED_AGE_ML_TEST_KEY"
        )
    for url in (
        "ftp://host",
        "http://user:secret@host",
        "http://host?key=secret",
        "http://host#secret",
    ):
        with pytest.raises(ValueError):
            resolve_llm_config("local-model", "ollama", url, "TEST_OLLAMA_KEY")


def test_bearer_key_is_read_at_request_time(monkeypatch):
    auth = EnvironmentBearerAuth("TEST_OLLAMA_KEY")
    observed = []
    transport = httpx.MockTransport(
        lambda request: (
            observed.append(request.headers["Authorization"])
            or httpx.Response(200, json={})
        )
    )
    with httpx.Client(auth=auth, transport=transport) as client:
        for token in ("first-test-key", "rotated-test-key"):
            monkeypatch.setenv("TEST_OLLAMA_KEY", token)
            client.get("http://host:11434/api/tags")
    assert observed == ["Bearer first-test-key", "Bearer rotated-test-key"]
    assert "rotated-test-key" not in repr(auth)


def test_structured_clients_follow_endpoint_switches(monkeypatch):
    for proxy in (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    ):
        monkeypatch.delenv(proxy, raising=False)
    import langchain_ollama

    real_client = langchain_ollama.ChatOllama
    observed = []

    def response(request):
        observed.append((str(request.url), request.headers["Authorization"]))
        return httpx.Response(
            200,
            json={
                "model": "local-model",
                "done": True,
                "message": {"role": "assistant", "content": '{"answer":"ok"}'},
            },
        )

    def create(**kwargs):
        kwargs["client_kwargs"]["transport"] = httpx.MockTransport(response)
        return real_client(**kwargs)

    monkeypatch.setattr(langchain_ollama, "ChatOllama", create)
    _build_model.cache_clear()
    monkeypatch.setenv("TEST_OLLAMA_KEY_12", "test-key-12")
    monkeypatch.setenv("TEST_OLLAMA_KEY_13", "test-key-13")
    # monkeypatch saves/restores the process configuration modified by export().
    for key in (
        "AGEML_MODEL_PROVIDER",
        "AGEML_MODEL_NAME",
        "AGEML_MODEL_BASE_URL",
        "AGEML_MODEL_API_KEY_ENV",
    ):
        monkeypatch.setenv(key, "")

    class Answer(BaseModel):
        answer: str

    structured = ConfiguredModel().with_structured_output(Answer, method="json_schema")
    for host, env in (
        ("192.168.15.12", "TEST_OLLAMA_KEY_12"),
        ("192.168.15.13", "TEST_OLLAMA_KEY_13"),
    ):
        config = resolve_llm_config(
            "local-model", "ollama", f"http://{host}:11434", env
        )
        config.export()
        assert structured.invoke("Reply with an answer").answer == "ok"
    assert observed == [
        ("http://192.168.15.12:11434/api/chat", "Bearer test-key-12"),
        ("http://192.168.15.13:11434/api/chat", "Bearer test-key-13"),
    ]
    assert "test-key-13" not in repr(_build_model(config))
    assert config != replace(config, base_url="http://another-host:11434")
    _build_model.cache_clear()


def test_no_auth_mode(monkeypatch):
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    config = resolve_llm_config("local-model", "ollama", "http://host:11434", "")
    assert config.api_key_env == ""


def test_suite_resume_distinguishes_servers_without_serializing_keys(
    tmp_path, monkeypatch
):
    from pathlib import Path

    import pandas as pd

    from ageml.protocol import VERSION
    from experiments import suite

    monkeypatch.setenv("TEST_OLLAMA_KEY", "sentinel-never-export-this-value")
    dataset_dir = tmp_path / "datasets/classification"
    dataset_dir.mkdir(parents=True)
    pd.DataFrame({"x": range(100), "label": [0, 1] * 50}).to_csv(
        dataset_dir / "synthetic.csv", index=False
    )
    (dataset_dir / "synthetic.metadata.json").write_text(
        json.dumps({"target_column": "label", "task": "classification"})
    )
    monkeypatch.setattr(suite, "RESOURCES_DIR", tmp_path)
    monkeypatch.setattr(suite, "download_all_openml_datasets", lambda _: None)
    monkeypatch.setattr(suite, "copy_out_artifacts", lambda **kwargs: None)
    monkeypatch.chdir(tmp_path)
    calls = []

    def fake_main(**kwargs):
        calls.append(kwargs)
        return {
            "protocol_version": VERSION,
            "status": "completed",
            "run_identity": "mock-invocation",
        }

    monkeypatch.setattr(suite, "main", fake_main)
    spec = Path(__file__).resolve().parents[2] / "resources/general-specification.yml"
    args = {
        "model_name": "local-model",
        "spec_path": spec,
        "output_dir": tmp_path / "results",
        "datasets": {"classification": {"synthetic": 123}},
        "model_provider": "ollama",
        "model_api_key_env": "TEST_OLLAMA_KEY",
    }
    suite.run_suite(**args, model_base_url="http://192.168.15.12:11434")
    suite.run_suite(**args, model_base_url="http://192.168.15.12:11434")
    csv = suite.run_suite(**args, model_base_url="http://192.168.15.13:11434")
    assert len(calls) == 2
    assert calls[0]["model_provider"] == "ollama"
    assert calls[0]["model_api_key_env"] == "TEST_OLLAMA_KEY"
    assert calls[0]["model_base_url"] != calls[1]["model_base_url"]
    assert pd.read_csv(csv)["Resume Identity"].nunique() == 2
    assert "sentinel-never-export-this-value" not in csv.read_text()


def test_ollama_payload_contains_seed_and_temperature(monkeypatch):
    import langchain_ollama

    for proxy in (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    ):
        monkeypatch.delenv(proxy, raising=False)
    for key in (
        "AGEML_MODEL_PROVIDER",
        "AGEML_MODEL_NAME",
        "AGEML_MODEL_BASE_URL",
        "AGEML_MODEL_API_KEY_ENV",
        "AGEML_MODEL_SEED",
        "AGEML_MODEL_TEMPERATURE",
    ):
        monkeypatch.setenv(key, "")
    real_client = langchain_ollama.ChatOllama
    payloads = []

    def response(request):
        payloads.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "model": "local-model",
                "done": True,
                "message": {"role": "assistant", "content": "ok"},
            },
        )

    def create(**kwargs):
        kwargs["client_kwargs"]["transport"] = httpx.MockTransport(response)
        return real_client(**kwargs)

    monkeypatch.setattr(langchain_ollama, "ChatOllama", create)
    _build_model.cache_clear()
    for seed in (42, 123):
        config = resolve_llm_config(
            "local-model", "ollama", "http://host:11434", "", seed, 0.0
        )
        config.export()
        assert ConfiguredModel().invoke("reply").content == "ok"
    assert [p["options"]["seed"] for p in payloads] == [42, 123]
    assert all(p["options"]["temperature"] == 0 for p in payloads)
    _build_model.cache_clear()
