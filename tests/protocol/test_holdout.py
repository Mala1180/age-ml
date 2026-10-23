"""Offline protocol regression checks and two synthetic smoke campaigns."""

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.metrics import balanced_accuracy_score, mean_squared_error

from ageml.protocol import (
    candidate_key,
    checked_predictions,
    prepare,
    select_and_evaluate,
    write_json,
)


class CountingModel:
    def __init__(self, value=0, fail=False):
        self.value, self.fail, self.calls = value, fail, []

    def predict(self, X):
        self.calls.append(list(X.index))
        if self.fail and len(X) == 20:
            raise RuntimeError("test failure")
        return np.repeat(self.value, len(X))


class HoldoutTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = self.root / "source.csv"
        pd.DataFrame({"x": range(100), "y": [0, 1] * 50}).to_csv(
            self.source, index=False
        )
        self.df, self.p = prepare(self.source, "y", "classification")
        self.p.update(
            run_identity="test-run", metric="balanced_accuracy", maximize=True
        )
        self.models = {"a": CountingModel(), "b": CountingModel(1)}

    def tearDown(self):
        self.tmp.cleanup()

    def candidate(self, key, score):
        return {
            "candidate_key": key,
            "pipeline_id": key,
            "run_id": key,
            "validation_score": score,
            "model_sha256": key,
            "code_sha256": key,
            "fit_succeeded": True,
            "run_identity": "test-run",
            "metric": self.p["metric"],
            "maximize": self.p["maximize"],
            "validation_split_hash": self.p["split_hashes"]["validation"],
        }

    def run_selection(self, candidates, name="run", labels=None, metric=None):
        out = self.root / name
        write_json(out / "protocol.json", self.p)

        def provider():
            self.assertTrue((out / "selection.json").exists())
            rows = self.p["partitions"]["test"]
            heldout = self.df.iloc[rows]
            return heldout[["x"]], heldout.y if labels is None else labels, rows

        result = select_and_evaluate(
            candidates,
            self.p,
            out,
            lambda c: self.models[c["run_id"]],
            self.df[["x"]].head(3),
            provider,
            metric or balanced_accuracy_score,
            [0, 1],
        )
        return result, json.loads((out / "selection.json").read_text())

    def test_partitions_and_round_trip(self):
        self.assertEqual(
            [len(self.p["partitions"][k]) for k in ("train", "validation", "test")],
            [64, 16, 20],
        )
        write_json(self.root / "manifest.json", self.p)
        _, imported = prepare(
            self.source, "y", "classification", manifest=self.root / "manifest.json"
        )
        self.assertEqual(imported, self.p)
        with self.assertRaises(ValueError):
            prepare(
                self.source,
                "y",
                "classification",
                seed=43,
                manifest=self.root / "manifest.json",
            )

    def test_invalid_manifest_and_source(self):
        for mutation in ("overlap", "order", "checksum"):
            p = json.loads(json.dumps(self.p))
            if mutation == "overlap":
                p["partitions"]["train"][0] = p["partitions"]["test"][0]
            elif mutation == "order":
                p["partitions"]["train"].reverse()
            else:
                p["source_sha256"] = "bad"
            write_json(self.root / "bad.json", p)
            with self.assertRaises(ValueError):
                prepare(
                    self.source, "y", "classification", manifest=self.root / "bad.json"
                )

    def test_explicit_configuration(self):
        for target, task in (
            (None, "classification"),
            ("absent", "classification"),
            ("y", None),
        ):
            with self.assertRaises(ValueError):
                prepare(self.source, target, task)

    def test_validation_wins_and_one_final_prediction(self):
        result, _ = self.run_selection(
            [self.candidate("a", 0.9), self.candidate("b", 0.5)]
        )
        self.assertEqual(result["best_run_id"], "a")
        test = self.p["partitions"]["test"]
        self.assertEqual(self.models["a"].calls.count(test), 1)
        self.assertEqual(self.models["b"].calls.count(test), 0)
        self.assertEqual(result["status"], "completed")

    def test_minimize_and_test_ranking_cannot_select(self):
        self.p.update(task="regression", metric="rmse", maximize=False)
        self.df.loc[self.p["partitions"]["test"], "y"] = 1  # b is perfect on test
        r, _ = self.run_selection(
            [self.candidate("a", 0.1), self.candidate("b", 1)],
            metric=lambda y, p: float(np.sqrt(mean_squared_error(y, p))),
        )
        self.assertEqual(r["best_run_id"], "a")
        self.assertEqual(r["test_score"], 1)

    def test_test_labels_do_not_change_selection(self):
        candidates = [self.candidate("a", 0.9), self.candidate("b", 0.5)]
        _, before = self.run_selection(candidates)
        labels = self.df.iloc[self.p["partitions"]["test"]].y.copy()
        labels.iloc[:] = labels.iloc[::-1].values
        _, after = self.run_selection(candidates, "permuted", labels=labels)
        self.assertEqual(before, after)

    def test_ties_ignore_candidate_order(self):
        candidates = [self.candidate("b", 0.5), self.candidate("a", 0.5)]
        _, a = self.run_selection(candidates)
        _, b = self.run_selection(list(reversed(candidates)), "reversed")
        self.assertEqual(a, b)
        self.assertEqual(a["selected"]["candidate_key"], "a")

    def test_no_fallback_after_test_failure(self):
        self.models["a"].fail = True
        r, s = self.run_selection([self.candidate("a", 0.9), self.candidate("b", 0.5)])
        self.assertEqual(r["status"], "test_evaluation_failed")
        self.assertEqual(r["best_run_id"], s["selected"]["run_id"])
        self.assertIsNone(r["test_score"])
        self.assertNotIn(self.p["partitions"]["test"], self.models["b"].calls)

    def test_scoring_failure_retains_selection_and_cached_predictions(self):
        def fail(y, p):
            raise ValueError("scoring failed")

        r, _ = self.run_selection([self.candidate("a", 0.9)], metric=fail)
        self.assertEqual(r["best_run_id"], "a")
        self.assertEqual(r["status"], "test_evaluation_failed")
        self.assertTrue((self.root / "run/test_predictions.csv").exists())

    def test_no_eligible_candidate(self):
        for index, candidates in enumerate(
            (
                [],
                [self.candidate("a", float("nan"))],
                [dict(self.candidate("a", 0.9), model_sha256=None)],
                [dict(self.candidate("a", 0.9), run_identity="old")],
            )
        ):
            r, _ = self.run_selection(candidates, str(index))
            self.assertEqual(r["status"], "no_valid_candidate")
            self.assertIsNone(r["test_score"])
            self.assertIsNone(r["best_run_id"])
        self.assertEqual(self.models["a"].calls, [])

    def test_unusable_model(self):
        self.models["a"] = object()
        r, _ = self.run_selection([self.candidate("a", 0.9)])
        self.assertEqual(r["status"], "no_valid_candidate")

    def test_prediction_schema(self):
        for value, task, classes in (
            (float("nan"), "regression", None),
            (2, "classification", [0, 1]),
        ):
            with self.assertRaises(ValueError):
                checked_predictions(CountingModel(value), self.df[["x"]], task, classes)

    def test_key_canonicalization(self):
        self.assertEqual(
            candidate_key([], {"b": 2, "a": 1}, "code"),
            candidate_key([], {"a": 1, "b": 2}, "code"),
        )

    def test_regression_not_stratified_and_class_fallback(self):
        _, p = prepare(self.source, "y", "regression")
        self.assertTrue(
            all(
                not d["stratified"] and d["reason"] is None for d in p["stratification"]
            )
        )
        df = self.df.copy()
        df.y = 0
        df.loc[0, "y"] = 1
        df.to_csv(self.source, index=False)
        _, p = prepare(self.source, "y", "classification")
        self.assertTrue(p["stratification"][0]["reason"])

    def test_duplicate_keys_use_declared_slots(self):
        a = self.candidate("a", 0.5)
        b = dict(a, run_id="b", pipeline_id="b")
        _, before = self.run_selection([b, a])
        _, after = self.run_selection([a, b], "duplicates-reversed")
        self.assertEqual(before, after)
        self.assertEqual(before["selected"]["run_id"], "a")

    def test_selection_cannot_be_overwritten(self):
        candidates = [self.candidate("a", 0.9)]
        self.run_selection(candidates)
        with self.assertRaises(FileExistsError):
            self.run_selection(candidates)

    def test_synthetic_smoke_campaigns_and_exports(self):
        for task in ("classification", "regression"):
            df, p = prepare(self.source, "y", task)
            p.update(
                run_identity="test-run",
                metric="balanced_accuracy" if task == "classification" else "rmse",
                maximize=task == "classification",
            )
            self.p = p
            train = df.iloc[p["partitions"]["train"]]
            val = df.iloc[p["partitions"]["validation"]]
            model = DummyClassifier() if task == "classification" else DummyRegressor()
            model.fit(train[["x"]], train.y)
            metric = (
                balanced_accuracy_score
                if task == "classification"
                else lambda y, p: float(np.sqrt(mean_squared_error(y, p)))
            )
            self.models["a"] = model
            c = self.candidate("a", float(metric(val.y, model.predict(val[["x"]]))))
            result, selected = self.run_selection([c], task, metric=metric)
            self.assertEqual(result["status"], "completed")
            predictions = pd.read_csv(self.root / task / "test_predictions.csv")
            self.assertEqual(list(predictions.row_id), p["partitions"]["test"])
            self.assertEqual(selected["selected"]["run_id"], result["best_run_id"])
            self.assertEqual(result["split_identity"], p["split_identity"])


if __name__ == "__main__":
    unittest.main()
