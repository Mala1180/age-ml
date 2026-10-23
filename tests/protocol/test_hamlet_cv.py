"""Match sklearn/HAMLET splits and scoring; keep selection CV out of test results."""

import json

import numpy as np
import pandas as pd
import pytest
from sklearn.datasets import make_classification
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import balanced_accuracy_score, root_mean_squared_error
from sklearn.model_selection import KFold, StratifiedKFold, cross_validate
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor

from ageml.fitting import evaluate_candidate, fit_seeded_model
from ageml.protocol import prepare, select_and_evaluate, write_json


@pytest.mark.parametrize("task", ["classification", "regression"])
def test_frozen_folds_match_sklearn_and_ignore_seed(tmp_path, task):
    source = tmp_path / "source.csv"
    y = [0, 1] * 51 + [0] if task == "classification" else np.arange(103) / 3
    pd.DataFrame({"x": range(103), "y": y}).to_csv(source, index=False)
    df, p = prepare(source, "y", task, evaluation_protocol="hamlet_cv")
    splitter = StratifiedKFold(10) if task == "classification" else KFold(10)
    expected = [
        {"train": a.tolist(), "validation": b.tolist()}
        for a, b in splitter.split(df[["x"]], df.y)
    ]
    assert p["cv_folds"] == expected
    assert sorted(i for fold in expected for i in fold["validation"]) == list(
        range(103)
    )
    assert p["partitions"]["test"] == []
    _, other = prepare(source, "y", task, seed=123, evaluation_protocol="hamlet_cv")
    assert other["split_identity"] == p["split_identity"]
    manifest = tmp_path / "manifest.json"
    write_json(manifest, p)
    assert prepare(source, "y", task, manifest=manifest)[1] == p
    with pytest.raises(ValueError, match="evaluation_protocol"):
        prepare(source, "y", task, manifest=manifest, evaluation_protocol="holdout")
    p["cv_folds"][0]["validation"][0] = 102
    write_json(manifest, p)
    with pytest.raises(ValueError, match="CV manifest"):
        prepare(source, "y", task, manifest=manifest)


def test_no_silent_reduction_to_fewer_folds(tmp_path):
    source = tmp_path / "small.csv"
    pd.DataFrame({"x": range(9), "y": np.arange(9) / 3}).to_csv(source, index=False)
    with pytest.raises(ValueError):
        prepare(source, "y", "regression", evaluation_protocol="hamlet_cv")


def test_all_nested_random_states_are_set_before_fit():
    X = pd.DataFrame({"x": range(40)})
    y = pd.Series([0, 1] * 20)

    def build(X, y):
        return make_pipeline(
            StandardScaler(), RandomForestClassifier(n_estimators=4, random_state=999)
        )

    a, applied = fit_seeded_model(build, X, y, {}, 42)
    b, _ = fit_seeded_model(build, X, y, {}, 42)
    assert applied == {"randomforestclassifier__random_state": 42}
    assert a[-1].random_state == 42
    np.testing.assert_array_equal(a.predict(X), b.predict(X))


@pytest.mark.parametrize("task", ["classification", "regression"])
def test_cv_scores_match_sklearn_pipeline_without_preprocessing_leak(tmp_path, task):
    X, y = make_classification(n_samples=103, n_features=5, random_state=17)
    if task == "regression":
        y = X[:, 0] ** 2 + np.arange(103) / 40
    frame = pd.DataFrame(X)
    frame.columns = [f"x{i}" for i in range(5)]
    frame["y"] = y
    source = tmp_path / "source.csv"
    frame.to_csv(source, index=False)
    frame, p = prepare(source, "y", task, evaluation_protocol="hamlet_cv")
    cls = DecisionTreeClassifier if task == "classification" else DecisionTreeRegressor
    metric = (
        balanced_accuracy_score if task == "classification" else root_mean_squared_error
    )

    def build(X, y):
        return make_pipeline(StandardScaler(), cls(max_depth=3))

    model, evidence, predictions = evaluate_candidate(
        build, frame, frame.iloc[:0], "y", task, {}, 42, metric, p["cv_folds"]
    )
    scoring = (
        "balanced_accuracy"
        if task == "classification"
        else "neg_root_mean_squared_error"
    )
    expected = cross_validate(
        make_pipeline(StandardScaler(), cls(max_depth=3, random_state=42)),
        frame.drop(columns="y"),
        frame.y,
        cv=10,
        scoring=scoring,
    )["test_score"]
    if task == "regression":
        expected = -expected
    np.testing.assert_allclose(evidence["cv_fold_scores"], expected)
    assert evidence["validation_score"] == pytest.approx(expected.mean())
    assert len(predictions) == 103 and predictions.row_id.nunique() == 103
    # The exported estimator is fitted only on the last fold's training rows.
    last = frame.iloc[p["cv_folds"][-1]["train"]].drop(columns="y")
    np.testing.assert_allclose(model[0].mean_, last.mean())


def test_fold_failure_rejects_whole_candidate(tmp_path):
    source = tmp_path / "source.csv"
    pd.DataFrame({"x": range(100), "y": [0, 1] * 50}).to_csv(source, index=False)
    frame, p = prepare(source, "y", "classification", evaluation_protocol="hamlet_cv")
    seen = []

    def build(X, y):
        seen.append(len(X))
        if len(seen) == 3:
            raise RuntimeError("fold failed")
        return DecisionTreeClassifier()

    with pytest.raises(RuntimeError, match="fold failed"):
        evaluate_candidate(
            build,
            frame,
            frame,
            "y",
            "classification",
            {},
            42,
            balanced_accuracy_score,
            p["cv_folds"],
        )
    assert len(seen) == 3


def test_cv_selection_never_calls_test_provider_or_exports_test_score(tmp_path):
    source = tmp_path / "source.csv"
    pd.DataFrame({"x": range(100), "y": [0, 1] * 50}).to_csv(source, index=False)
    frame, p = prepare(source, "y", "classification", evaluation_protocol="hamlet_cv")
    p.update(run_identity="run", metric="balanced_accuracy", maximize=True)
    write_json(tmp_path / "out/protocol.json", p)
    model = DecisionTreeClassifier(random_state=42).fit(frame[["x"]], frame.y)
    candidate = {
        "candidate_key": "key",
        "pipeline_id": 0,
        "run_id": "candidate",
        "validation_score": 0.5,
        "cv_fold_scores": [0.5] * 10,
        "model_sha256": "model",
        "code_sha256": "code",
        "fit_succeeded": True,
        "run_identity": "run",
        "metric": "balanced_accuracy",
        "maximize": True,
        "validation_split_hash": p["split_hashes"]["validation"],
    }
    result = select_and_evaluate(
        [candidate],
        p,
        tmp_path / "out",
        lambda _: model,
        frame[["x"]].head(3),
        lambda: pytest.fail("CV has no independent test"),
        balanced_accuracy_score,
        [0, 1],
    )
    assert result["status"] == "completed"
    assert result["search_cv_score"] == 0.5
    assert result["test_score"] is result["best_test_score"] is None
    assert not (tmp_path / "out/test_predictions.csv").exists()
    assert json.loads((tmp_path / "out/selection.json").read_text())["selected"]


@pytest.mark.parametrize("scores", [[0.5] * 9, [0.5] * 9 + [float("nan")], [0.8] * 10])
def test_incomplete_or_inconsistent_cv_scores_are_ineligible(tmp_path, scores):
    source = tmp_path / "source.csv"
    pd.DataFrame({"x": range(100), "y": [0, 1] * 50}).to_csv(source, index=False)
    frame, p = prepare(source, "y", "classification", evaluation_protocol="hamlet_cv")
    p.update(run_identity="run", metric="balanced_accuracy", maximize=True)
    write_json(tmp_path / "protocol.json", p)
    c = {
        "candidate_key": "key",
        "pipeline_id": 0,
        "run_id": "c",
        "validation_score": 0.5,
        "cv_fold_scores": scores,
        "model_sha256": "m",
        "code_sha256": "c",
        "fit_succeeded": True,
        "run_identity": "run",
        "metric": "balanced_accuracy",
        "maximize": True,
        "validation_split_hash": p["split_hashes"]["validation"],
    }
    result = select_and_evaluate(
        [c],
        p,
        tmp_path,
        lambda _: pytest.fail("invalid evidence must be rejected before loading"),
        frame[["x"]].head(3),
        lambda: pytest.fail("test"),
        balanced_accuracy_score,
        [0, 1],
    )
    assert result["status"] == "no_valid_candidate"


def test_planner_sampling_is_seeded_and_independent_of_enumeration_order():
    from types import SimpleNamespace

    from ageml.common.types import Step
    from ageml.planning.agent import select_pipelines
    from ageml.planning.types import PlanningPipeline

    pipelines = [
        PlanningPipeline(
            steps=[Step(name="model", candidate=f"model{i}", hyperparameters={})]
        )
        for i in range(8)
    ]
    spec = SimpleNamespace(budgets=SimpleNamespace(pipelines=3))

    def selected(values, seed):
        result = select_pipelines(
            {"specification": spec, "pipelines": values, "run_seed": seed}
        )
        return [p.model_dump(mode="json") for p in result["pipelines"]]

    assert selected(pipelines, 42) == selected(list(reversed(pipelines)), 42)
    assert selected(pipelines, 42) != selected(pipelines, 123)
