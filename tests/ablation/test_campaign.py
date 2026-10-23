"""Campaign orchestration with real frozen partitions and no LLM calls."""

import json
from pathlib import Path

import pandas as pd
import pytest
import yaml

from ageml.common.llm_config import resolve_llm_config
from ageml.protocol import prepare
from experiments import campaign


def configuration(tmp_path, **updates):
    values = {
        "name": "offline-test",
        "model": {
            "provider": "ollama",
            "name": "local-model",
            "base_url": "http://host:11434",
            "api_key_env": "CAMPAIGN_TEST_KEY",
        },
        "specification": str(
            Path(__file__).resolve().parents[2] / "resources/general-specification.yml"
        ),
        "output_dir": str(tmp_path / "results"),
        "repetitions": [1, 2],
        "datasets": {"classification": {"synthetic": 123}},
        "ablations": {
            "specification": ["poor", "specific"],
            "validation": ["no-semantic-retry", "no-execution-retry"],
            "no_csp": True,
        },
    }
    values.update(updates)
    return campaign.Campaign.model_validate(values)


def dataset(tmp_path):
    directory = tmp_path / "datasets/classification"
    directory.mkdir(parents=True)
    source = directory / "synthetic.csv"
    pd.DataFrame({"x": range(100), "label": [0, 1] * 50}).to_csv(source, index=False)
    source.with_suffix(".metadata.json").write_text(
        json.dumps(
            {"target_column": "label", "task": "classification", "openml_id": 123}
        )
    )
    return source


def test_plan_covers_all_axes_and_repetitions(tmp_path):
    settings = configuration(tmp_path)
    plan = campaign.build_plan(settings)
    assert [job["id"] for job in plan["jobs"]] == [
        "baseline",
        "specification-poor",
        "specification-specific",
        "validation-no-semantic-retry",
        "validation-no-execution-retry",
        "no-csp",
    ]
    assert plan["dataset_runs"] == 12
    assert plan["nominal_exploration_hours"] == 24


@pytest.mark.parametrize(
    "update",
    [
        {"repetitions": 0},
        {"repetitions": [1, 1]},
        {"repetitions": True},
        {"ablations": {"specification": ["general"]}},
        {"datasets": {"classification": {"../escape": 123}}},
        {"unexpected": 1},
    ],
)
def test_invalid_campaigns_fail_before_work(tmp_path, update):
    with pytest.raises(ValueError):
        configuration(tmp_path, **update)


def test_dry_run_has_no_credentials_downloads_or_agent_calls(tmp_path, monkeypatch):
    settings = configuration(tmp_path)
    path = tmp_path / "config.yml"
    path.write_text(yaml.safe_dump(settings.model_dump(mode="json")))
    monkeypatch.delenv("CAMPAIGN_TEST_KEY", raising=False)
    monkeypatch.setattr(
        campaign,
        "download_all_openml_datasets",
        lambda *_: pytest.fail("download during dry run"),
    )
    monkeypatch.setattr(
        campaign, "run_suite", lambda **_: pytest.fail("agent during dry run")
    )
    assert campaign.run(str(path), dry_run=True)["dataset_runs"] == 12
    assert not Path(settings.output_dir).exists()


def test_generation_uses_training_only_and_manifest_is_immutable(tmp_path, monkeypatch):
    source = dataset(tmp_path)
    monkeypatch.setattr(campaign, "RESOURCES_DIR", tmp_path)
    monkeypatch.setenv("CAMPAIGN_TEST_KEY", "test-secret-not-for-export")
    settings = configuration(tmp_path)
    llm = resolve_llm_config(
        settings.model.name,
        "ollama",
        settings.model.base_url,
        settings.model.api_key_env,
    )
    seen = []
    original = campaign.compute_meta_features_from_frame

    def spy(df, task, name, target):
        seen.append(df.copy())
        return original(df, task, name, target)

    monkeypatch.setattr(campaign, "compute_meta_features_from_frame", spy)
    plan = campaign.build_plan(settings)
    paths = campaign._prepare(settings, plan, llm)
    _, split = prepare(source, "label", "classification", manifest=paths["synthetic"])
    assert len(seen) == 1 and len(seen[0]) == 64
    assert list(seen[0].x) == split["partitions"]["train"]
    manifest = Path(settings.output_dir) / "campaign.json"
    before = manifest.read_bytes()
    campaign._prepare(settings, plan, llm)
    assert manifest.read_bytes() == before
    assert "test-secret-not-for-export" not in before.decode()
    altered = settings.model_copy(update={"repetitions": [3]})
    with pytest.raises(ValueError, match="Frozen campaign artifact differs"):
        campaign._prepare(altered, campaign.build_plan(altered), llm)
    assert manifest.read_bytes() == before


def test_all_jobs_use_same_imported_splits_and_backend(tmp_path, monkeypatch):
    dataset(tmp_path)
    monkeypatch.setenv("CAMPAIGN_TEST_KEY", "test-secret")
    monkeypatch.setattr(campaign, "ROOT", tmp_path)
    monkeypatch.setattr(campaign, "RESOURCES_DIR", tmp_path)
    monkeypatch.setattr(campaign, "download_all_openml_datasets", lambda *_: None)
    settings = configuration(tmp_path)
    path = tmp_path / "config.yml"
    path.write_text(yaml.safe_dump(settings.model_dump(mode="json")))
    calls = []

    def suite(**kwargs):
        calls.append(kwargs)
        return kwargs["output_dir"] / "results.csv"

    monkeypatch.setattr(campaign, "run_suite", suite)
    campaign.run(str(path))
    assert len(calls) == 12
    assert len({c["split_manifests"]["synthetic"] for c in calls}) == 1
    assert all(
        c["model_provider"] == "ollama" and c["download_datasets"] is False
        for c in calls
    )
    assert len({str(c["output_dir"]) for c in calls}) == 12
    assert sum(c.get("use_csp") is False for c in calls) == 2
    assert sum(c.get("retry_on_semantic_failure") is False for c in calls) == 2
    assert sum(c.get("retry_on_execution_failure") is False for c in calls) == 2
    campaign.run(
        str(path)
    )  # Reuses frozen manifest; run_suite owns per-dataset resume.
    assert len(calls) == 24


def test_simultaneous_campaigns_in_one_checkout_are_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(campaign, "ROOT", tmp_path)
    with (
        campaign.checkout_lock(),
        pytest.raises(RuntimeError, match="Another campaign"),
        campaign.checkout_lock(),
    ):
        pytest.fail("second lock acquired")
    with campaign.checkout_lock():
        pass


def test_output_cannot_be_deleted_with_agent_scratch(tmp_path):
    for folder in ("out", "tmp", "ageml", "resources"):
        settings = configuration(
            tmp_path, output_dir=str(campaign.ROOT / folder / "campaign")
        )
        with pytest.raises(ValueError, match="output_dir must be separate"):
            campaign.build_plan(settings)


def test_hamlet_plan_and_all_axes_share_cv_and_seed(tmp_path, monkeypatch):
    source = dataset(tmp_path)
    monkeypatch.setenv("CAMPAIGN_TEST_KEY", "test-secret")
    monkeypatch.setattr(campaign, "ROOT", tmp_path)
    monkeypatch.setattr(campaign, "RESOURCES_DIR", tmp_path)
    monkeypatch.setattr(campaign, "download_all_openml_datasets", lambda *_: None)
    settings = configuration(
        tmp_path,
        evaluation_protocol="hamlet_cv",
        run_seed=42,
        time_budget_seconds=3600,
    )
    settings.model.seed = 42
    settings.model.temperature = 0.0
    path = tmp_path / "config.yml"
    path.write_text(yaml.safe_dump(settings.model_dump(mode="json")))
    calls = []
    monkeypatch.setattr(
        campaign,
        "run_suite",
        lambda **kw: calls.append(kw) or kw["output_dir"] / "results.csv",
    )
    plan = campaign.run(str(path), dry_run=True)
    assert plan["nominal_exploration_hours"] == 12
    assert plan["cv_folds_per_candidate"] == 10
    campaign.run(str(path))
    assert len(calls) == 12
    assert all(
        c["evaluation_protocol"] == "hamlet_cv"
        and c["run_seed"] == 42
        and c["model_seed"] == 42
        and c["model_temperature"] == 0.0
        and c["time_budget_seconds"] == 3600
        for c in calls
    )
    paths = {c["split_manifests"]["synthetic"] for c in calls}
    assert len(paths) == 1
    _, split = prepare(source, "label", "classification", manifest=paths.pop())
    assert len(split["cv_folds"]) == 10
    assert split["partitions"]["test"] == []
