"""Coordinator-owned holdout and HAMLET-style CV protocols. No LLM imports."""

import hashlib
import json
import math
import os
import platform
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import KFold, StratifiedKFold, train_test_split

VERSION = "ageml-evaluation-v3"
MODES = ("holdout", "hamlet_cv")


def digest(value):
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value, exclusive=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x" if exclusive else "w") as stream:
        json.dump(value, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def prepare(source, target, task, seed=42, manifest=None, evaluation_protocol=None):
    """All CSV rows are eligible, in parsed source order; no filtering occurs."""
    if task not in ("classification", "regression") or not target:
        raise ValueError("Explicit target_column and task are required")
    df = pd.read_csv(source)
    if target not in df or df[target].isna().any() or len(df.columns) < 2:
        raise ValueError("Invalid/missing target, missing labels, or no features")
    if manifest:
        imported = json.loads(Path(manifest).read_text())
        mode = (
            imported.get("evaluation_protocol")
            if evaluation_protocol is None
            else evaluation_protocol
        )
    else:
        mode = evaluation_protocol or "holdout"
    if mode not in MODES:
        raise ValueError(f"evaluation_protocol must be one of {MODES}")
    identity = {
        "evaluation_protocol": mode,
        "protocol_version": VERSION,
        "source_sha256": file_hash(source),
        "source_row_count": len(df),
        "target_column": target,
        "task": task,
        "row_identity": "zero-based parsed CSV source position; all rows eligible",
    }
    if manifest:
        p = json.loads(Path(manifest).read_text())
        for key, value in identity.items():
            if p.get(key) != value:
                raise ValueError(f"Manifest conflict: {key}")
        if seed is not None and seed != p["split_seed"]:
            raise ValueError("Manifest conflict: split_seed")
    elif mode == "hamlet_cv":
        # sklearn cross_validate(cv=10) uses these unshuffled splitters.
        # Do not stratify continuous regression targets or silently reduce K.
        splitter = (
            StratifiedKFold(n_splits=10, shuffle=False)
            if task == "classification"
            else KFold(n_splits=10, shuffle=False)
        )
        folds = [
            {"train": a.tolist(), "validation": b.tolist()}
            for a, b in splitter.split(df.drop(columns=[target]), df[target])
        ]
        rows = list(range(len(df)))
        p = dict(
            identity,
            dataset_id=Path(source).stem,
            dataset_version=identity["source_sha256"],
            split_seed=42 if seed is None else seed,
            splitter={
                "class": type(splitter).__name__,
                "n_splits": 10,
                "shuffle": False,
                "random_state": None,
            },
            cv_folds=folds,
            partitions={"train": rows, "validation": rows, "test": []},
            stratification=[
                {
                    "stage": "search_cv",
                    "stratified": task == "classification",
                    "reason": None,
                }
            ],
        )
    else:
        seed = 42 if seed is None else seed
        decisions = []

        def split(rows, stage):
            stratify = df.iloc[rows][target] if task == "classification" else None
            try:
                a, b = train_test_split(
                    rows, test_size=0.2, random_state=seed, stratify=stratify
                )
                decisions.append(
                    {"stage": stage, "stratified": stratify is not None, "reason": None}
                )
            except ValueError as exc:
                if stratify is None:
                    raise
                a, b = train_test_split(rows, test_size=0.2, random_state=seed)
                decisions.append(
                    {"stage": stage, "stratified": False, "reason": str(exc)}
                )
            return sorted(a), sorted(b)

        development, test = split(list(range(len(df))), "outer")
        train, validation = split(development, "inner")
        p = dict(
            identity,
            dataset_id=Path(source).stem,
            dataset_version=identity["source_sha256"],
            split_seed=seed,
            partitions={"train": train, "validation": validation, "test": test},
            stratification=decisions,
        )
    parts = p["partitions"]
    if set(parts) != {"train", "validation", "test"}:
        raise ValueError("Invalid partition names")
    flat = []
    for rows in parts.values():
        if (
            (not rows and not (mode == "hamlet_cv" and rows == parts["test"]))
            or any(type(i) is not int for i in rows)
            or rows != sorted(rows)
        ):
            raise ValueError(
                "Partitions must contain nonempty, ordered integer row IDs"
            )
        flat.extend(rows)
    if mode == "holdout":
        if sorted(flat) != list(range(len(df))):
            raise ValueError(
                "Partitions must be disjoint and cover source rows exactly"
            )
    else:
        expected_rows = list(range(len(df)))
        if parts != {"train": expected_rows, "validation": expected_rows, "test": []}:
            raise ValueError(
                "CV partitions must describe the whole search dataset and no external test"
            )
        splitter = (
            StratifiedKFold(n_splits=10, shuffle=False)
            if task == "classification"
            else KFold(n_splits=10, shuffle=False)
        )
        expected_folds = [
            {"train": a.tolist(), "validation": b.tolist()}
            for a, b in splitter.split(df.drop(columns=[target]), df[target])
        ]
        expected_splitter = {
            "class": type(splitter).__name__,
            "n_splits": 10,
            "shuffle": False,
            "random_state": None,
        }
        if (
            p.get("cv_folds") != expected_folds
            or p.get("splitter") != expected_splitter
        ):
            raise ValueError(
                "CV manifest differs from the declared unshuffled ten-fold splitter"
            )
    hashes = {k: digest(v) for k, v in parts.items()}
    if mode == "hamlet_cv":
        hashes["validation"] = digest(p["cv_folds"])
    if manifest and p.get("split_hashes") != hashes:
        raise ValueError("Partition hash mismatch")
    p["split_hashes"] = hashes
    split_identity = digest(
        dict(identity, partitions=parts, cv_folds=p.get("cv_folds"))
    )
    if manifest and p.get("split_identity") != split_identity:
        raise ValueError("Split identity mismatch")
    p["split_identity"] = split_identity
    return df, p


def candidate_key(structure, hyperparameters, code, fit_seed=42):
    return digest(
        {
            "structure": structure,
            "hyperparameters": hyperparameters,
            "code_sha256": hashlib.sha256(code.encode()).hexdigest(),
            "fit_seed": fit_seed,
        }
    )


def checked_predictions(model, X, task, classes=None):
    raw = model.predict(X)
    if isinstance(raw, (pd.Series, pd.DataFrame)) and not raw.index.equals(X.index):
        raise ValueError("Prediction index does not match feature row order")
    values = np.asarray(raw)
    if values.ndim != 1 or len(values) != len(X) or pd.isna(values).any():
        raise ValueError("Expected one nonmissing scalar prediction per ordered row")
    if task == "regression" and not np.isfinite(values.astype(float)).all():
        raise ValueError("Nonfinite regression predictions")
    if (
        task == "classification"
        and classes is not None
        and not pd.Series(values).isin(classes).all()
    ):
        raise ValueError("Classification predictions must use training label encoding")
    return values


def select_and_evaluate(
    candidates,
    protocol,
    output,
    load_model,
    development_X,
    test_provider,
    metric_fn,
    classes=None,
):
    """Commit selection before invoking the coordinator's test data provider.

    Artifact verification uses development data only. Test prediction is called
    once, including on failure; no repair, substitution, or refit is possible.
    """
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    if (output / "selection.json").exists():
        raise FileExistsError("Selection already frozen; choose a fresh run directory")
    evidence, usable = [], {}
    for candidate in candidates:
        c = dict(candidate, eligible=False)
        try:
            if any(
                c.get(k) != v
                for k, v in {
                    "run_identity": protocol["run_identity"],
                    "validation_split_hash": protocol["split_hashes"]["validation"],
                    "metric": protocol["metric"],
                    "maximize": protocol["maximize"],
                }.items()
            ):
                raise ValueError("Candidate provenance mismatch")
            if (
                not c.get("fit_succeeded")
                or not c.get("model_sha256")
                or not math.isfinite(c["validation_score"])
            ):
                raise ValueError(
                    "Failed fit, missing artifact identity or nonfinite score"
                )
            if protocol.get("evaluation_protocol") == "hamlet_cv":
                scores = c.get("cv_fold_scores")
                if (
                    not isinstance(scores, list)
                    or len(scores) != 10
                    or not all(math.isfinite(v) for v in scores)
                ):
                    raise ValueError("Candidate requires ten finite CV fold scores")
                if not math.isclose(
                    float(np.mean(scores)),
                    c["validation_score"],
                    rel_tol=1e-12,
                    abs_tol=1e-12,
                ):
                    raise ValueError("CV mean does not match candidate score")
            model = load_model(c)
            checked_predictions(model, development_X, protocol["task"], classes)
            c["eligible"] = True
            # Identical semantic keys with different evidence are rejected below.
            usable[c["run_id"]] = model
        except Exception as exc:  # noqa: BLE001 - artifact and model failures are terminal evidence
            c["eligibility_failure"] = str(exc)
            c.setdefault("failure", str(exc))
        evidence.append(c)
    groups = {}
    for c in evidence:
        if c["eligible"]:
            groups.setdefault(c["candidate_key"], []).append(c)
    for group in groups.values():
        if len({(c["model_sha256"], c["validation_score"]) for c in group}) > 1:
            for c in group:
                c.update(eligible=False, failure="Conflicting duplicate candidate key")
    # Identical duplicates choose the earliest declared fit slot, never completion order or MLflow IDs.
    for group in groups.values():
        group.sort(
            key=lambda c: (
                str(c["pipeline_id"]),
                c.get("fit_attempt", 0),
                c.get("grid_position", 0),
            )
        )
        slots = [
            (str(c["pipeline_id"]), c.get("fit_attempt", 0), c.get("grid_position", 0))
            for c in group
        ]
        if len(set(slots)) != len(slots) and len({c["run_id"] for c in group}) > 1:
            for c in group:
                c.update(eligible=False, failure="Ambiguous duplicate fit slots")
        for duplicate in group[1:]:
            duplicate.update(
                eligible=False,
                failure="Duplicate fit; canonical declared slot retained",
            )
    eligible = [c for c in evidence if c["eligible"]]
    eligible.sort(
        key=lambda c: (
            (-1 if protocol["maximize"] else 1) * c["validation_score"],
            c["candidate_key"],
        )
    )
    winner = eligible[0] if eligible else None
    # Duplicate identical keys are equivalent fits; keep all references, canonicalize by semantic evidence.
    selected = (
        None
        if winner is None
        else {
            k: winner[k]
            for k in (
                "candidate_key",
                "pipeline_id",
                "run_id",
                "validation_score",
                "model_sha256",
                "code_sha256",
            )
        }
    )
    if selected is not None:
        selected["pipeline_run_id"] = winner.get("pipeline_run_id")
    selection = {
        "protocol_version": VERSION,
        "run_identity": protocol["run_identity"],
        "protocol_sha256": file_hash(output / "protocol.json"),
        "split_identity": protocol["split_identity"],
        "selected": selected,
        "rule": "finite usable candidates; validation metric then ascending canonical candidate key",
        "duplicate_policy": "conflicts excluded; identical fits use ascending declared pipeline ID and fit attempt",
    }
    frame = (
        pd.DataFrame(evidence)
        if evidence
        else pd.DataFrame(
            columns=[
                "candidate_key",
                "pipeline_id",
                "run_id",
                "eligible",
                "validation_score",
                "validation_split_hash",
                "model_sha256",
                "code_sha256",
                "failure",
            ]
        )
    )
    frame.to_csv(output / "validation_candidates.csv", index=False)
    write_json(output / "selection.json", selection, exclusive=True)
    result = {
        "status": "no_valid_candidate" if winner is None else "test_evaluation_failed",
        "protocol_version": VERSION,
        "run_identity": protocol["run_identity"],
        "protocol_sha256": file_hash(output / "protocol.json"),
        "selection_sha256": file_hash(output / "selection.json"),
        "split_identity": protocol["split_identity"],
        "selected_candidate_key": None if winner is None else winner["candidate_key"],
        "best_pipeline_id": None if winner is None else winner["pipeline_id"],
        "best_run_id": None if winner is None else winner["run_id"],
        "best_run_name": None,
        "selection_validation_score": None
        if winner is None
        else winner["validation_score"],
        "test_score": None,
        "validation_metric": protocol["metric"],
        "artifacts": {},
    }
    result["evaluation_protocol"] = protocol.get("evaluation_protocol", "holdout")
    result["search_cv_score"] = None
    if protocol.get("evaluation_protocol") == "hamlet_cv":
        # Selection CV is not an independent generalization estimate.
        result.update(
            status="completed" if winner is not None else "no_valid_candidate",
            search_cv_score=None if winner is None else winner["validation_score"],
            cv_fold_scores=None if winner is None else winner.get("cv_fold_scores"),
            score_role="selection_cv_not_independent_test",
            model_role="representative_last_cv_fold_model_not_full_data_refit",
        )
    elif winner is not None:
        try:
            X, y, rows = test_provider()
            if (
                list(rows) != protocol["partitions"]["test"]
                or len(X) != len(rows)
                or not X.index.equals(y.index)
            ):
                raise ValueError("Test row alignment mismatch")
            predictions = checked_predictions(
                usable[winner["run_id"]], X, protocol["task"], classes
            )
            pd.DataFrame({"row_id": rows, "prediction": predictions}).to_csv(
                output / "test_predictions.csv", index=False
            )
            score = float(metric_fn(y, predictions))
            if not math.isfinite(score):
                raise ValueError("Nonfinite test score")
            result.update(status="completed", test_score=score)
        except Exception as exc:  # noqa: BLE001 - artifact and model failures are terminal evidence
            result["test_failure"] = str(exc)
    result["best_test_score"] = result[
        "test_score"
    ]  # compatibility alias, validation-selected
    result["artifact_references"] = {
        p.name: str(p) for p in output.iterdir() if p.is_file()
    }
    write_json(output / "result.json", result)
    return result


def environment_identity():
    from importlib.metadata import distributions

    return {
        "python": sys.version,
        "python_hash_seed": os.environ.get("PYTHONHASHSEED"),
        "platform": platform.platform(),
        "packages": sorted(
            (d.metadata["Name"], d.version)
            for d in distributions()
            if d.metadata["Name"]
        ),
    }
