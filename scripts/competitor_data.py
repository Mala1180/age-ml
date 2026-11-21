"""Read committed summary tables and describe matched AGE-ML / MLZero outcomes."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
import re
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

CV_SCORE = "Search CV Score (selection; not independent test)"
ROLE = "selection_cv_not_independent_test"
PROTOCOL = "ageml-evaluation-v3/hamlet_cv"
METHODS = ("AGE-ML Original", "MLZero")
MISSING = "not_published"
AGE_FINAL = {"completed", "no_valid_candidate", "test_evaluation_failed"}
MLZERO_FINAL = {
    "completed",
    "no_artifact",
    "invalid_cv_export",
    "export_failed",
    "inference_failed",
    "invalid_predictions",
    "protocol_violation",
}
DATASET_ORDER = (
    "wilt",
    "texture",
    "madelon",
    "har",
    "adult",
    "mnist_784",
    "california_housing",
    "ames_housing",
    "auto_mpg",
)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def git(directory, *args, offline=False):
    environment = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    if offline:
        environment.update(GIT_NO_LAZY_FETCH="1", GIT_ALLOW_PROTOCOL="")
    result = subprocess.run(
        ["git", "-C", str(directory), *args],
        capture_output=True,
        env=environment,
    )
    if result.returncode:
        raise ValueError(result.stderr.decode(errors="replace")[-1800:].strip())
    return result.stdout


class GitSource:
    """A dedicated bare cache: never switch or modify the user's checkout."""

    def __init__(self, repository, ref, cache, offline=False):
        location = Path(repository).expanduser()
        self.repository = (
            str(location.resolve()) if location.exists() else str(repository)
        )
        self.ref = ref
        self.cache = Path(cache)
        self.offline = offline
        self.files = {}
        check(
            re.fullmatch(r"[A-Za-z0-9_./-]+", ref) is not None
            and not ref.startswith("-"),
            "Expected a Git branch, ref or commit ID",
        )
        if not self.cache.exists():
            if offline:
                raise ValueError(f"No cached source at {self.cache}; run once online")
            self.cache.mkdir(parents=True)
            git(self.cache, "init", "--bare", "--quiet")
        if git(self.cache, "rev-parse", "--is-bare-repository").strip() != b"true":
            raise ValueError(
                f"Source cache must be a dedicated bare repository: {cache}"
            )
        identity = digest((self.repository + "\0" + ref).encode())[:24]
        self.cache_ref = f"refs/competitor-analysis/{identity}"
        if not offline:
            git(self.cache, "config", "remote.origin.url", self.repository)
            git(self.cache, "config", "remote.origin.promisor", "true")
            git(self.cache, "config", "remote.origin.partialclonefilter", "blob:none")
            git(
                self.cache,
                "fetch",
                "--quiet",
                "--depth=1",
                "--filter=blob:none",
                "--no-tags",
                "origin",
                ref,
            )
            commit = git(self.cache, "rev-parse", "FETCH_HEAD").decode().strip()
            git(self.cache, "update-ref", self.cache_ref, commit)
        self.commit = git(self.cache, "rev-parse", self.cache_ref).decode().strip()
        self.paths = set(
            git(self.cache, "ls-tree", "-r", "--name-only", self.commit)
            .decode()
            .splitlines()
        )

    def read(self, path, optional=False):
        if path not in self.paths:
            if optional:
                return None
            raise ValueError(f"Missing committed input at {self.ref}: {path}")
        raw = git(self.cache, "show", f"{self.commit}:{path}", offline=self.offline)
        self.files[path] = digest(raw)
        return raw

    def provenance(self):
        return dict(
            repository=self.repository,
            requested_ref=self.ref,
            commit=self.commit,
            file_sha256=self.files,
        )


def csv_rows(raw, path):
    if raw is None:
        return []
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    rows = list(reader)
    if any(None in row or any(v is None for v in row.values()) for row in rows):
        raise ValueError(f"Malformed or partially written summary CSV: {path}")
    return rows


def number(value, context, optional=False):
    if value is None or str(value).strip() in ("", "None", "nan", "NaN"):
        if optional:
            return float("nan")
        raise ValueError(f"Missing numeric value: {context}")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"Nonfinite value: {context}")
    return result


def boolean(value):
    if value in (True, "True", "true", "1", 1):
        return True
    if value in (False, "False", "false", "0", 0):
        return False
    raise ValueError(f"Expected an explicit boolean, found {value!r}")


def check(condition, message):
    if not condition:
        raise ValueError(message)


def valid_score(value, metric, context):
    score = number(value, context)
    check(
        score >= 0 and (metric != "balanced_accuracy" or score <= 1),
        f"Score outside the metric domain: {context}",
    )
    return score


def read_backend(age, mlzero, backend, definition, repetitions):
    """Complete the planned grid; missing publications are not failed searches."""
    age_root = definition["age_campaign"]
    ml_root = definition["mlzero_campaign"]
    manifest_path = f"{age_root}/campaign.json"
    raw_manifest = age.read(manifest_path)
    manifest = json.loads(raw_manifest)
    age_config = manifest["config"]
    check(age_config["evaluation_protocol"] == "hamlet_cv", "AGE-ML is not HAMLET-CV")
    check(age_config["model"]["name"] == definition["model"], "AGE-ML model mismatch")
    check(age_config["run_seed"] == 42, "AGE-ML seed must be 42")
    check(age_config["model"]["seed"] == 42, "AGE-ML model seed must be 42")
    check(age_config["time_budget_seconds"] == 3600, "AGE-ML budget must be one hour")
    check(age_config["model"]["temperature"] == 0, "AGE-ML temperature must be zero")
    check(
        set(repetitions) <= set(age_config["repetitions"]),
        "Unplanned AGE-ML repetitions",
    )
    version = manifest["plan"]["protocol_version"]
    check(version == "ageml-evaluation-v3", "Unexpected AGE-ML protocol version")
    datasets = {
        name: dict(
            task=task,
            openml_id=identifier,
            metric="balanced_accuracy" if task == "classification" else "rmse",
        )
        for task, entries in age_config["datasets"].items()
        for name, identifier in entries.items()
    }
    cfg = yaml.safe_load(mlzero.read(definition["mlzero_config"]))
    check(cfg["protocol"] == PROTOCOL, "MLZero protocol mismatch")
    check(cfg["mlzero"]["search_seed"] == 42, "MLZero search seed must be 42")
    check(cfg["llm"]["model"] == definition["model"], "MLZero model mismatch")
    check(
        cfg["llm"]["settings"] == {"seed": 42, "temperature": 0.0},
        "MLZero seed or temperature mismatch",
    )
    check(
        cfg["budget"]["search_wall_seconds"] == 3600, "MLZero budget must be one hour"
    )
    check(
        cfg["age_campaign_identity"] == manifest["campaign_identity"],
        "MLZero refers to a different AGE-ML campaign",
    )
    check(
        cfg["age_manifest_sha256"] == digest(raw_manifest),
        "MLZero AGE-ML manifest hash mismatch",
    )
    check(set(repetitions) <= set(cfg["repetitions"]), "Unplanned MLZero repetitions")
    entries = {entry["key"]: entry for entry in cfg["dataset_entries"]}
    check(set(entries) == set(datasets), "Dataset sets differ between methods")
    rows, seen_age = [], set()
    for name, metadata in datasets.items():
        evidence = manifest["source_evidence"][name]
        check(
            len(evidence["manifest"]["cv_folds"]) == 10, f"Expected ten folds: {name}"
        )
        entry = entries[name]
        check(
            entry["task"] == metadata["task"]
            and entry["openml_id"] == metadata["openml_id"],
            f"MLZero dataset metadata mismatch: {name}",
        )
        check(
            entry["input_hashes"]["data.csv"] == evidence["source_sha256"],
            f"Different source data: {name}",
        )
        check(
            entry["split_identity"] == evidence["split_identity"],
            f"Different prescribed folds: {name}",
        )
    for repetition in repetitions:
        path = f"{age_root}/baseline/run-{repetition}/{version}/results.csv"
        for original in csv_rows(age.read(path, optional=True), path):
            name = original["Dataset"]
            check(name in datasets, f"Unexpected AGE-ML dataset: {name}")
            check(
                (name, repetition) not in seen_age,
                f"Duplicate AGE-ML result: {name}/{repetition}",
            )
            seen_age.add((name, repetition))
            metadata = datasets[name]
            check(
                original["Protocol Version"] == version
                and original["Evaluation Protocol"] == "hamlet_cv",
                f"Mixed AGE-ML protocol: {path}",
            )
            check(
                original["Validation Metric"] == metadata["metric"],
                f"Wrong metric: {name}",
            )
            check(
                original["Problem"] == metadata["task"]
                and int(original["OpenML ID"]) == metadata["openml_id"],
                f"AGE-ML dataset metadata mismatch: {name}",
            )
            check(
                original["Split Identity"] == entries[name]["split_identity"],
                f"AGE-ML fold mismatch: {name}",
            )
            status = original["Status"]
            check(status in AGE_FINAL, f"Unknown AGE-ML outcome: {status}")
            score = (
                valid_score(original[CV_SCORE], metadata["metric"], path)
                if status == "completed"
                else float("nan")
            )
            rows.append(
                dict(
                    backend=backend,
                    model=definition["model"],
                    method=METHODS[0],
                    dataset=name,
                    repetition=repetition,
                    status=status,
                    score=score,
                    score_role=ROLE,
                    source_sha256=entries[name]["input_hashes"]["data.csv"],
                    split_identity=entries[name]["split_identity"],
                    source_file=path,
                    search_budget_s=3600,
                    workers=number(original.get("Workers"), path, optional=True),
                    termination_reason="",
                    **metadata,
                )
            )
    path = f"{ml_root}/report/mlzero_runs.csv"
    published = mlzero.read(path, optional=True)
    seen_ml = set()
    for original in csv_rows(published, path):
        check(
            original["model"] == definition["model"], "Mixed MLZero models in summary"
        )
        check(
            original["protocol"] == PROTOCOL and original["score_role"] == ROLE,
            "MLZero summary is not selection CV; test scores cannot be substituted",
        )
        check(
            not str(original.get("test_score", "")).strip(),
            "Unexpected independent-test score in CV summary",
        )
        if not boolean(original["final"]):
            continue
        name, repetition = original["dataset"], int(original["repetition"])
        check(
            name in datasets and repetition in cfg["repetitions"],
            "Unplanned MLZero result",
        )
        check(
            (name, repetition) not in seen_ml,
            f"Duplicate MLZero final outcome: {name}/{repetition}",
        )
        seen_ml.add((name, repetition))
        check(
            original["source_sha256"] == entries[name]["input_hashes"]["data.csv"],
            f"MLZero source mismatch: {name}",
        )
        check(
            original["split_identity"] == entries[name]["split_identity"],
            f"MLZero fold mismatch: {name}",
        )
        check(
            number(original["fit_seed"], path) == 42
            and number(original["llm_seed_requested"], path) == 42,
            "MLZero run seed mismatch",
        )
        check(
            number(original["temperature"], path) == 0
            and number(original["search_budget_s"], path) == 3600,
            "MLZero run settings mismatch",
        )
        check(
            boolean(original["llm_settings_verified"]),
            "Unverified effective MLZero LLM settings",
        )
        status = original["status"]
        check(status in MLZERO_FINAL, f"Unknown MLZero final status: {status}")
        if repetition not in repetitions:
            continue
        metric = datasets[name]["metric"]
        score = (
            valid_score(original["cv_score"], metric, path)
            if status == "completed"
            else float("nan")
        )
        if status == "completed":
            folds = np.asarray(json.loads(original["cv_fold_scores"]), dtype=float)
            check(
                folds.shape == (10,) and np.isfinite(folds).all(),
                "Incomplete MLZero fold scores",
            )
            check(
                math.isclose(
                    float(folds.mean()),
                    score,
                    rel_tol=1e-6 if metric == "rmse" else 1e-10,
                    abs_tol=1e-10,
                ),
                "MLZero score disagrees with its fold scores",
            )
        rows.append(
            dict(
                backend=backend,
                model=definition["model"],
                method=METHODS[1],
                dataset=name,
                repetition=repetition,
                status=status,
                score=score,
                score_role=ROLE,
                source_sha256=original["source_sha256"],
                split_identity=original["split_identity"],
                source_file=path,
                search_budget_s=3600,
                workers=float("nan"),
                termination_reason=original.get("termination_reason", ""),
                **datasets[name],
            )
        )
    grid = {(row["method"], row["dataset"], row["repetition"]): row for row in rows}
    for method in METHODS:
        for name, metadata in datasets.items():
            for repetition in repetitions:
                key = method, name, repetition
                if key not in grid:
                    grid[key] = dict(
                        backend=backend,
                        model=definition["model"],
                        method=method,
                        dataset=name,
                        repetition=repetition,
                        status=MISSING,
                        score=float("nan"),
                        score_role=ROLE,
                        source_sha256=entries[name]["input_hashes"]["data.csv"],
                        split_identity=entries[name]["split_identity"],
                        source_file="",
                        search_budget_s=3600,
                        workers=float("nan"),
                        termination_reason="",
                        **metadata,
                    )
    audit_count = cross_check_audit(mlzero, definition, grid)
    for row in grid.values():
        row.setdefault("terminal_phase", "")
        row.setdefault("generated_nodes", float("nan"))
        row.setdefault("cv_exports", float("nan"))
    info = dict(
        backend=backend,
        label=definition["label"],
        model=definition["model"],
        datasets=datasets,
        repetitions=list(repetitions),
        mlzero_summary_published=published is not None,
        source_data_and_folds_match=True,
        audited_rows_cross_checked=audit_count,
        seed=42,
        folds=10,
        search_budget_s=3600,
        resource_equivalence="Not established: CPU allocation and AGE-ML workers are different quantities",
    )
    return pd.DataFrame(grid.values()), info


def cross_check_audit(source, definition, grid):
    """Check existing audit tables against current committed campaign summaries."""
    root = definition.get("mlzero_audit")
    if not root:
        return 0
    count, seen = 0, set()
    for original in csv_rows(source.read(f"{root}/run_audit.csv", optional=True), root):
        key = original["dataset"], int(original["repetition"])
        check(key not in seen, f"Duplicate audit row: {key}")
        seen.add(key)
        ml = grid.get((METHODS[1], *key))
        if ml is None:
            continue  # A requested repetition subset need not include every audit row.
        age = grid[(METHODS[0], *key)]
        check(
            ml["status"] == original["status"],
            f"Audit and published summary disagree: {key}",
        )
        for field in ("source_sha256", "split_identity"):
            check(original[field] == ml[field], f"Audit {field} mismatch: {key}")
        for row, field in ((age, "age_cv_score"), (ml, "cv_score")):
            if row["status"] == "completed":
                check(
                    math.isclose(
                        number(original[field], root),
                        row["score"],
                        rel_tol=1e-10,
                        abs_tol=1e-10,
                    ),
                    f"Audit score disagrees with committed result: {key}/{field}",
                )
        for field in ("generated_nodes", "cv_exports"):
            ml[field] = number(original.get(field), root, optional=True)
        count += 1
    seen = set()
    for original in csv_rows(
        source.read(f"{root}/run_diagnostics.csv", optional=True), root
    ):
        key = original["dataset"], int(original["repetition"])
        check(key not in seen, f"Duplicate diagnostic row: {key}")
        seen.add(key)
        ml = grid.get((METHODS[1], *key))
        if ml is not None:
            check(
                original["status"] == ml["status"], f"Diagnostic status mismatch: {key}"
            )
            ml["terminal_phase"] = original["terminal_phase"]
    return count


def describe(values):
    """Descriptive intervals across successful repetitions, never across folds."""
    values = np.asarray(values, dtype=float)
    check(np.isfinite(values).all(), "Summary received a nonfinite successful score")
    n = len(values)
    result = {
        key: float("nan")
        for key in (
            "mean",
            "sd",
            "median",
            "q1",
            "q3",
            "min",
            "max",
            "ci95_half_width",
            "ci95_low",
            "ci95_high",
        )
    }
    if n:
        result.update(
            mean=float(values.mean()),
            median=float(np.median(values)),
            q1=float(np.quantile(values, 0.25)),
            q3=float(np.quantile(values, 0.75)),
            min=float(values.min()),
            max=float(values.max()),
        )
    if n > 1:
        from scipy.stats import t

        result["sd"] = float(values.std(ddof=1))
        half = float(t.ppf(0.975, n - 1)) * result["sd"] / math.sqrt(n)
        result.update(
            ci95_half_width=half,
            ci95_low=result["mean"] - half,
            ci95_high=result["mean"] + half,
        )
    return result


def summarize(frame):
    rows = []
    for (backend, dataset, method, metric), group in frame.groupby(
        ["backend", "dataset", "method", "metric"], sort=False
    ):
        success = group.status.eq("completed")
        missing = group.status.eq(MISSING)
        rows.append(
            dict(
                backend=backend,
                dataset=dataset,
                method=method,
                metric=metric,
                n_planned=len(group),
                n_recorded=int((~missing).sum()),
                n_valid=int(success.sum()),
                n_failed=int((~success & ~missing).sum()),
                n_not_published=int(missing.sum()),
                **describe(group.loc[success, "score"].to_numpy()),
            )
        )
    return pd.DataFrame(rows)


def paired_results(frame):
    rows = []
    for (backend, dataset, repetition), group in frame.groupby(
        ["backend", "dataset", "repetition"], sort=False
    ):
        age = group[group.method.eq(METHODS[0])].iloc[0]
        mlzero = group[group.method.eq(METHODS[1])].iloc[0]
        eligible = age.status == "completed" and mlzero.status == "completed"
        advantage = float("nan")
        if eligible:
            if age.metric == "balanced_accuracy":
                advantage = 100 * (mlzero.score - age.score)
            elif age.score != 0:
                advantage = 100 * (age.score - mlzero.score) / age.score
        rows.append(
            dict(
                backend=backend,
                dataset=dataset,
                repetition=repetition,
                metric=age.metric,
                age_status=age.status,
                mlzero_status=mlzero.status,
                age_score=age.score,
                mlzero_score=mlzero.score,
                both_valid=eligible,
                mlzero_advantage=advantage,
                advantage_unit="percentage_points"
                if age.metric == "balanced_accuracy"
                else "percent_rmse_reduction",
            )
        )
    return pd.DataFrame(rows)


def summarize_pairs(pairs):
    rows = []
    for (backend, dataset, metric), group in pairs.groupby(
        ["backend", "dataset", "metric"], sort=False
    ):
        valid = group[group.both_valid]
        defined = valid[valid.mlzero_advantage.notna()]
        age_values, ml_values = (
            valid.age_score.to_numpy(),
            valid.mlzero_score.to_numpy(),
        )
        ml_better = (
            ml_values > age_values
            if metric == "balanced_accuracy"
            else ml_values < age_values
        )
        rows.append(
            dict(
                backend=backend,
                dataset=dataset,
                metric=metric,
                n_planned=len(group),
                n_pairs=len(valid),
                n_defined_advantages=len(defined),
                mlzero_wins=int(ml_better.sum()),
                age_wins=int((~ml_better & (ml_values != age_values)).sum()),
                ties=int((ml_values == age_values).sum()),
                age_mean_on_pairs=float(age_values.mean())
                if len(valid)
                else float("nan"),
                mlzero_mean_on_pairs=float(ml_values.mean())
                if len(valid)
                else float("nan"),
                **describe(defined.mlzero_advantage.to_numpy()),
            )
        )
    return pd.DataFrame(rows)


def dataset_order(names):
    return sorted(
        names,
        key=lambda name: (
            DATASET_ORDER.index(name) if name in DATASET_ORDER else len(DATASET_ORDER),
            name,
        ),
    )


def label(name):
    return {"har": "HAR", "mnist_784": "MNIST", "auto_mpg": "Auto MPG"}.get(
        name, name.replace("_", " ").title()
    )


def parse_repetitions(text):
    check(
        re.fullmatch(r"[1-5](,[1-5])*", text) is not None,
        "Use distinct repetitions from 1 to 5, e.g. 1,2,3,4,5",
    )
    values = [int(value) for value in text.split(",")]
    check(len(set(values)) == len(values), "Duplicate repetition requested")
    return sorted(values)
