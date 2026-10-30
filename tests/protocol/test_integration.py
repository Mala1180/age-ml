"""Exercise the actual app, executor, MLflow artifacts and evaluator offline."""

import importlib
import json
import sys
import types
from pathlib import Path
from unittest.mock import Mock

import mlflow
import pandas as pd
import pytest


class ImmediatePool:
    def __init__(self, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def apply_async(self, fn, args):
        value = fn(*args)
        return types.SimpleNamespace(get=lambda **kwargs: value)


@pytest.mark.parametrize(
    "task,fail_fit,evaluation_protocol,worker_timeout",
    [
        (task, fail, mode, False)
        for mode in ("holdout", "hamlet_cv")
        for task, fail in [
            ("classification", False),
            ("regression", False),
            ("classification", True),
        ]
    ]
    + [("classification", False, "hamlet_cv", True)],
)
def test_app_smoke(
    task, fail_fit, evaluation_protocol, worker_timeout, tmp_path, monkeypatch
):
    cv = evaluation_protocol == "hamlet_cv"
    train_size = 100 if cv else 64
    fit_size = 90 if cv else 64
    # Inject a model factory before importing model-bound agent modules.
    fake = types.ModuleType("ageml.common.model")
    fake.model = Mock()
    monkeypatch.setitem(sys.modules, "ageml.common.model", fake)
    for name in ("ageml.execution.agent", "ageml.planning.agent"):
        monkeypatch.delitem(sys.modules, name, raising=False)
    execution = importlib.import_module("ageml.execution.agent")
    planning = importlib.import_module("ageml.planning.agent")
    app = importlib.import_module("ageml.app")
    from ageml.common.types import Step
    from ageml.planning.types import PlanningPipeline
    from ageml.protocol import file_hash

    monkeypatch.chdir(tmp_path)
    mlflow.set_tracking_uri("sqlite:///" + str(tmp_path / "mlflow.db"))
    import ageml.common.client as common_client

    monkeypatch.setattr(common_client, "client", mlflow.MlflowClient())
    source = tmp_path / "source.csv"
    pd.DataFrame({"feature": range(100), "label": [0, 1] * 50}).to_csv(
        source, index=False
    )
    repo = Path(__file__).resolve().parents[2]
    # Same application interface and specification, small smoke budgets.
    text = (repo / "resources/general-specification.yml").read_text()
    spec = tmp_path / "spec.yml"
    spec.write_text(text)
    observed = []

    def plan(inputs):
        assert "dataset_path" not in inputs
        assert len(inputs["train_df"]) == train_size
        assert list(inputs["train_df"].index) == list(range(train_size))
        observed.append(inputs["train_df"].copy())
        return {
            "pipelines": [
                PlanningPipeline(
                    steps=[
                        Step(
                            name="model", candidate=f"dummy{index}", hyperparameters={}
                        )
                    ]
                )
                for index in range(2)
            ],
            "pipelines_found": 2,
        }

    monkeypatch.setattr(planning.planning_agent, "invoke", plan)
    model_type = "DummyClassifier" if task == "classification" else "DummyRegressor"
    code = f"from sklearn.dummy import {model_type}\ndef build_model(X_train, y_train):\n    assert len(X_train) == len(y_train) == {fit_size}\n    assert list(X_train.index) == list(range({fit_size}))\n    return {model_type}()\n"
    if fail_fit:
        code = "def build_model(X_train, y_train):\n    raise ValueError('deliberate smoke fit failure')\n"
    monkeypatch.setattr(
        execution,
        "code_model",
        types.SimpleNamespace(invoke=lambda _: execution.CodeResponse(code=code)),
    )
    monkeypatch.setattr(
        execution,
        "judge_model",
        types.SimpleNamespace(
            invoke=lambda _: execution.JudgeResponse(is_compliant=True, feedback="ok")
        ),
    )
    monkeypatch.setattr(
        execution,
        "explanation_model",
        types.SimpleNamespace(
            invoke=lambda _: execution.ExplanationResponse(
                markdown_text="Dummy smoke pipeline"
            )
        ),
    )
    original_invoke = app.invoke_agent
    worker_views = []

    def spy_worker(inputs, session):
        assert "dataset_path" not in inputs and "test_df" not in inputs
        worker_views.append((inputs["train_df"].copy(), inputs["validation_df"].copy()))
        result = original_invoke(inputs, session)
        assert "dataset_path" not in result and "test_df" not in result
        return result

    monkeypatch.setattr(app, "invoke_agent", spy_worker)

    class CompletedCandidateThenTimeout(ImmediatePool):
        def apply_async(self, fn, args):
            fn(*args)  # Candidate evidence is complete, but the worker return is lost.

            def timeout(**kwargs):
                raise app.multiprocessing.TimeoutError()

            return types.SimpleNamespace(get=timeout)

    monkeypatch.setattr(
        app, "Pool", CompletedCandidateThenTimeout if worker_timeout else ImmediatePool
    )
    monkeypatch.setattr(app, "enable_mlflow_llm_autologging", lambda: None)
    monkeypatch.setattr(execution, "enable_mlflow_llm_autologging", lambda: None)
    monkeypatch.setattr(app, "get_nested_runs_total_llm_latency", lambda *args: 0)
    monkeypatch.setattr(
        app,
        "get_session_total_token_usage",
        lambda *args: {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "input_cost": 0,
            "output_cost": 0,
            "total_cost": 0,
        },
    )
    result = app.main(
        str(spec),
        str(source),
        target_column="label",
        task=task,
        evaluation_protocol=evaluation_protocol,
        protocol_output_dir=str(tmp_path / "protocol"),
        retry_on_execution_failure=False,
    )
    assert observed
    assert len(worker_views) == 2
    pd.testing.assert_frame_equal(worker_views[0][0], worker_views[1][0])
    pd.testing.assert_frame_equal(worker_views[0][1], worker_views[1][1])
    if fail_fit:
        assert result["status"] == "no_valid_candidate"
        assert result["best_run_id"] is None and result["test_score"] is None
        out = tmp_path / "protocol"
        assert not (out / "test_predictions.csv").exists()
        failures = pd.read_csv(out / "validation_candidates.csv")
        assert len(failures) == 2 and not failures.eligible.any()
        assert failures.failure.str.contains("deliberate smoke fit failure").all()
        return
    assert result["status"] == "completed"
    # This grid has no explicit hyperparameters. Estimator defaults must not be
    # autologged into the candidate run, where they can collide with grid values.
    assert mlflow.MlflowClient().get_run(result["best_run_id"]).data.params == {}
    out = tmp_path / "protocol"
    selection = json.loads((out / "selection.json").read_text())
    evidence = pd.read_csv(out / "validation_candidates.csv")
    assert (
        result["best_run_id"]
        == selection["selected"]["run_id"]
        == evidence.loc[evidence.run_id == result["best_run_id"]].iloc[0].run_id
    )
    assert result["selection_sha256"] == file_hash(out / "selection.json")
    if cv:
        assert result["search_cv_score"] is not None and result["test_score"] is None
        assert len(result["cv_fold_scores"]) == 10
        assert not (out / "test_predictions.csv").exists()
        assert all(
            len(json.loads(p.read_text())["cv_fold_scores"]) == 10
            for p in (out / "candidate_journal").glob("*.json")
        )
    else:
        assert len(pd.read_csv(out / "test_predictions.csv")) == 20
    assert result["artifacts"]["best_run"]
    assert (
        json.loads((out / "protocol.json").read_text())["access_boundary"][
            "filesystem_isolation"
        ]
        is False
    )
