"""Snapshot and describe campaign results without importing the experiment runtime.

Examples:
  python scripts/campaign_analysis.py snapshot --campaign PATH --repetitions 1 --outdir snapshots/run-1
  python scripts/campaign_analysis.py report --campaign snapshots/run-1 --outdir reports/run-1
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

CV_SCORE = "Search CV Score (selection; not independent test)"
TEST_SCORE = "Test-set Score (validation-selected)"
FINAL_STATUSES = {"completed", "no_valid_candidate", "test_evaluation_failed"}
RESOURCE_COLUMNS = {
    "pipelines_found": "Pipelines Found",
    "pipeline_budget": "Pipeline Budget",
    "semantic_validation_failures": "Semantic Validation Failures",
    "estimated_cost_usd": "Putative Cost ($)",
    "total_tokens": "Total Tokens",
    "workers": "Workers",
    "actual_pipelines": "Actual Pipelines",
}
EVIDENCE_FILES = (
    "selection.json",
    "result.json",
    "validation_candidates.csv",
    "exploration_failures.json",
    "storage_cleanup.json",
)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def parse_repetitions(value, available):
    if value == "all":
        return list(available)
    values = [int(item) for item in str(value).split(",")]
    if (
        not values
        or len(values) != len(set(values))
        or not set(values) <= set(available)
    ):
        raise ValueError(f"Repetitions must be distinct members of {available}")
    return values


def metadata(root):
    path = root / "campaign.json"
    frozen = json.loads(path.read_text(encoding="utf-8"))
    config = frozen["config"]
    available = config["repetitions"]
    if isinstance(available, int):
        available = list(range(1, available + 1))
    jobs = [job["id"] for job in frozen["plan"]["jobs"]]
    if len(jobs) != len(set(jobs)) or "baseline" not in jobs:
        raise ValueError("Expected distinct conditions including baseline")
    datasets = {
        name: {"problem": problem, "id": identifier}
        for problem, values in config["datasets"].items()
        for name, identifier in values.items()
    }
    for name in jobs + list(datasets):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", name) or name in (".", ".."):
            raise ValueError("Unsafe dataset/condition name")
    protocol = config["evaluation_protocol"]
    if protocol not in ("hamlet_cv", "holdout"):
        raise ValueError(f"Unsupported evaluation protocol: {protocol}")
    return {
        "frozen": frozen,
        "available": available,
        "conditions": jobs,
        "datasets": datasets,
        "version": frozen["plan"]["protocol_version"],
        "protocol": protocol,
        "score_column": CV_SCORE if protocol == "hamlet_cv" else TEST_SCORE,
        "score_role": "selection_cv_not_independent_test"
        if protocol == "hamlet_cv"
        else "held_out_test",
    }


def _number(value):
    if value is None or str(value).strip() in ("", "nan", "NaN", "None"):
        return float("nan")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"Nonfinite numeric value: {value}")
    return number


def _verify_snapshot(root):
    manifest_path = root / "snapshot.json"
    if not manifest_path.exists():
        return None
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for relative, expected in manifest["files"].items():
        path = (root / relative).resolve()
        if (
            not path.is_relative_to(root.resolve())
            or sha256(path.read_bytes()) != expected
        ):
            raise ValueError(f"Snapshot file missing or changed: {relative}")
    return manifest


def load_campaign(root, repetitions="1", allow_incomplete=False):
    """Read only exact requested result files; fail on duplicates or mixed roles."""
    root = Path(root).resolve()
    snapshot = _verify_snapshot(root)
    info = metadata(root)
    selected = parse_repetitions(repetitions, info["available"])
    if snapshot is not None and not set(selected) <= set(snapshot["repetitions"]):
        raise ValueError("Requested repetitions are not included in this snapshot")
    rows, inputs, seen, order = [], {}, set(), []
    for condition in info["conditions"]:
        for repetition in selected:
            relative = (
                Path(condition) / f"run-{repetition}" / info["version"] / "results.csv"
            )
            path = root / relative
            if not path.exists():
                continue
            if snapshot is not None and relative.as_posix() not in snapshot["files"]:
                raise ValueError(
                    f"Unlisted result file added to immutable snapshot: {relative}"
                )
            raw = path.read_bytes()
            inputs[relative.as_posix()] = raw
            reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
            required = {
                "Dataset",
                "OpenML ID",
                "Problem",
                "Status",
                "Protocol Version",
                "Evaluation Protocol",
                "Validation Metric",
                info["score_column"],
                "Run Identity",
                "Resume Identity",
                "Split Identity",
            }
            if not required <= set(reader.fieldnames or []):
                raise ValueError(f"Missing current-protocol columns in {relative}")
            for original in reader:
                if None in original or any(
                    value is None for value in original.values()
                ):
                    raise ValueError(
                        f"Incomplete CSV row in {relative}; try again after the write"
                    )
                name = original["Dataset"]
                key = (condition, repetition, name)
                if key in seen:
                    raise ValueError(f"Duplicate result identity: {key}")
                seen.add(key)
                expected = info["datasets"].get(name)
                if expected is None:
                    raise ValueError(f"Unexpected dataset: {name}")
                if (
                    original["Problem"] != expected["problem"]
                    or _number(original["OpenML ID"]) != expected["id"]
                ):
                    raise ValueError(f"Dataset metadata mismatch: {key}")
                if (
                    original["Protocol Version"] != info["version"]
                    or original["Evaluation Protocol"] != info["protocol"]
                ):
                    raise ValueError(f"Mixed protocol/version: {relative}")
                metric = (
                    "balanced_accuracy"
                    if expected["problem"] == "classification"
                    else "rmse"
                )
                if original["Validation Metric"] != metric:
                    raise ValueError(f"Unexpected metric for {key}")
                status = original["Status"]
                if status not in FINAL_STATUSES:
                    raise ValueError(f"Nonfinal/unknown status: {status}")
                for identity_column in (
                    "Run Identity",
                    "Resume Identity",
                    "Split Identity",
                ):
                    if not re.fullmatch(r"[a-f0-9]{64}", original[identity_column]):
                        raise ValueError(f"Missing/invalid {identity_column}: {key}")
                frozen_split = info["frozen"]["source_evidence"][name]["split_identity"]
                if original["Split Identity"] != frozen_split:
                    raise ValueError(f"Frozen split mismatch: {key}")
                score = (
                    _number(original[info["score_column"]])
                    if status == "completed"
                    else float("nan")
                )
                if status == "completed" and not math.isfinite(score):
                    raise ValueError(f"Completed row has no finite score: {key}")
                if status == "completed" and (
                    score < 0 or (metric == "balanced_accuracy" and score > 1)
                ):
                    raise ValueError(f"Score outside metric range: {key}")
                if (
                    info["protocol"] == "hamlet_cv"
                    and TEST_SCORE in original
                    and math.isfinite(_number(original[TEST_SCORE]))
                ):
                    raise ValueError(
                        "CV campaign unexpectedly contains a test score; do not mix score roles"
                    )
                row = {
                    "condition": condition,
                    "repetition": repetition,
                    "dataset": name,
                    "problem": expected["problem"],
                    "metric": metric,
                    "status": status,
                    "score": score,
                    "score_role": info["score_role"],
                    "source_csv": relative.as_posix(),
                    "run_identity": original["Run Identity"],
                    "resume_identity": original["Resume Identity"],
                    "split_identity": original["Split Identity"],
                }
                for target, source in RESOURCE_COLUMNS.items():
                    row[target] = _number(original.get(source))
                value = original.get("Actual Time", "")
                row["actual_time_hours"] = (
                    pd.to_timedelta(value).total_seconds() / 3600
                    if value
                    else float("nan")
                )
                rows.append(row)
                if name not in order:
                    order.append(name)
    order += [name for name in info["datasets"] if name not in order]
    missing = [
        (condition, repetition, name)
        for condition in info["conditions"]
        for repetition in selected
        for name in order
        if (condition, repetition, name) not in seen
    ]
    if missing and not allow_incomplete:
        raise ValueError(
            f"Selected repetitions are incomplete: {len(missing)} missing outcomes; use --allow-incomplete explicitly"
        )
    for condition, repetition, name in missing:
        problem = info["datasets"][name]["problem"]
        rows.append(
            {
                "condition": condition,
                "repetition": repetition,
                "dataset": name,
                "problem": problem,
                "metric": "balanced_accuracy"
                if problem == "classification"
                else "rmse",
                "status": "missing",
                "score": float("nan"),
                "score_role": info["score_role"],
            }
        )
    info.update(repetitions=selected, dataset_order=order, root=root, missing=missing)
    frame = pd.DataFrame(rows)
    for column in [*RESOURCE_COLUMNS, "actual_time_hours"]:
        if column not in frame:
            frame[column] = float("nan")
    return frame, info, inputs


def exploration_counts(frame, info):
    """Observed candidate records, never inferred from pipeline counts or fold budget.

    validation_candidates.csv can omit interrupted/unreturned attempts. These
    counts describe recorded evidence, not all work started by killed workers.
    """
    records, by_pipeline = [], []
    fields = (
        "candidate_records",
        "unique_candidates",
        "successful_candidate_records",
        "eligible_candidates",
    )
    for row in frame.itertuples():
        entry = {
            key: getattr(row, key)
            for key in ("condition", "repetition", "dataset", "status")
        }
        entry.update(
            {
                key: getattr(row, key, float("nan"))
                for key in (
                    "pipelines_found",
                    "pipeline_budget",
                    "actual_pipelines",
                    "semantic_validation_failures",
                )
            }
        )
        entry.update(dict.fromkeys(fields, float("nan")))
        entry.update(
            evidence_source="",
            evidence_note="No candidate evidence available; counts unknown",
        )
        if row.status != "missing":
            warnings = []
            sources = [
                p
                for p in _evidence_paths(info["root"], row, warnings)
                if p.name == "validation_candidates.csv"
            ]
            if sources:
                path = sources[0]
                data = pd.read_csv(path)
                required = {"candidate_key", "pipeline_id", "run_id", "eligible"}
                if not required <= set(data.columns):
                    raise ValueError(f"Missing candidate evidence columns: {path}")
                if data.run_id.isna().any() or data.run_id.duplicated().any():
                    raise ValueError(f"Missing/duplicate candidate run_id: {path}")

                def truth(series, evidence_path=path):
                    values = series.astype(str).str.lower()
                    if not values.isin(["true", "false"]).all():
                        raise ValueError(
                            f"Invalid candidate boolean in {evidence_path}"
                        )
                    return values.eq("true")

                eligible = truth(data.eligible)
                successes = (
                    truth(data.fit_succeeded) if "fit_succeeded" in data else None
                )
                entry.update(
                    candidate_records=len(data),
                    unique_candidates=data.candidate_key.nunique(),
                    eligible_candidates=int(eligible.sum()),
                    evidence_source=path.relative_to(info["root"]).as_posix(),
                    evidence_note="Recorded candidates only; interrupted/unreturned work can be absent",
                )
                if successes is not None:
                    entry["successful_candidate_records"] = int(successes.sum())
                for pipeline_id, part in data.groupby("pipeline_id"):
                    by_pipeline.append(
                        {
                            **{
                                key: entry[key]
                                for key in ("condition", "repetition", "dataset")
                            },
                            "pipeline_id": pipeline_id,
                            "candidate_records": len(part),
                            "unique_candidates": part.candidate_key.nunique(),
                            "eligible_candidates": int(eligible.loc[part.index].sum()),
                            "evidence_source": entry["evidence_source"],
                        }
                    )
        records.append(entry)
    details = pd.DataFrame(
        by_pipeline,
        columns=[
            "condition",
            "repetition",
            "dataset",
            "pipeline_id",
            "candidate_records",
            "unique_candidates",
            "eligible_candidates",
            "evidence_source",
        ],
    )
    return pd.DataFrame(records), details


def _evidence_paths(root, row, warnings):
    base = Path(row.source_csv).parent
    protocol_root = root / base / "protocol" / row.dataset / row.resume_identity
    matches = []
    for result_path in sorted(protocol_root.rglob("result.json")):
        result = json.loads(result_path.read_text(encoding="utf-8"))
        if (
            result.get("run_identity") != row.run_identity
            or result.get("status") != row.status
        ):
            continue
        score = (
            result.get("search_cv_score")
            if row.score_role.startswith("selection_cv")
            else result.get("test_score")
        )
        if row.status == "completed" and (
            score is None
            or not math.isclose(float(score), row.score, rel_tol=1e-10, abs_tol=1e-12)
        ):
            continue
        selection = result_path.parent / "selection.json"
        if not selection.exists() or sha256(selection.read_bytes()) != result.get(
            "selection_sha256"
        ):
            raise ValueError(f"Selection checksum mismatch: {result_path}")
        matches.append((result_path.parent, result))
    if len(matches) == 1:
        directory, _ = matches[0]
        for name in EVIDENCE_FILES:
            path = directory / name
            if path.is_file():
                yield path
    else:
        warnings.append(
            f"{row.condition}/run-{row.repetition}/{row.dataset}: {len(matches)} matching evidence directories; CSV retained, detailed evidence not copied"
        )
    winner = (
        root / base / "artifacts" / row.dataset / row.resume_identity / "best_pipeline"
    )
    for name in ("code.py", "pipeline.md"):
        path = winner / name
        if path.is_file():
            yield path


def snapshot_campaign(root, outdir, repetitions="1", allow_incomplete=False):
    frame, info, inputs = load_campaign(root, repetitions, allow_incomplete)
    root, outdir = info["root"], Path(outdir).resolve()
    if outdir.exists() or outdir.is_relative_to(root):
        raise ValueError("Snapshot needs a new directory outside the live campaign")
    blobs = {"campaign.json": (root / "campaign.json").read_bytes(), **inputs}
    for path in sorted((root / "specifications").rglob("*.yml")):
        blobs[path.relative_to(root).as_posix()] = path.read_bytes()
    base_spec = Path(info["frozen"]["config"]["specification"])
    if not base_spec.is_absolute():
        base_spec = Path(__file__).resolve().parents[1] / base_spec
    warnings = []
    if base_spec.exists():
        raw = base_spec.read_bytes()
        if sha256(raw) != info["frozen"]["base_specification_sha256"]:
            raise ValueError("Live base specification differs from the frozen campaign")
        blobs["base-specification.yml"] = raw
    else:
        warnings.append(
            "Base specification unavailable; its frozen hash remains in campaign.json"
        )
    for row in frame.loc[frame.status.ne("missing")].itertuples():
        for path in _evidence_paths(root, row, warnings):
            if not path.resolve().is_relative_to(root):
                raise ValueError("Evidence path escapes campaign directory")
            blobs[path.relative_to(root).as_posix()] = path.read_bytes()
    manifest = {
        "snapshot_version": 1,
        "snapshot_script_sha256": sha256(Path(__file__).read_bytes()),
        "created_utc": datetime.now(UTC).isoformat(),
        "campaign_identity": info["frozen"]["campaign_identity"],
        "repetitions": info["repetitions"],
        "recorded_outcomes": int(frame.status.ne("missing").sum()),
        "completed": int(frame.status.eq("completed").sum()),
        "files": {name: sha256(raw) for name, raw in sorted(blobs.items())},
        "evidence_warnings": warnings,
        "omitted": "No serialized models, tracking database, prediction arrays or duplicated full protocol/fold files. Frozen folds remain in campaign.json source_evidence. This is an analysis snapshot, not a complete model archive.",
    }
    outdir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".snapshot-", dir=outdir.parent
    ) as temporary:
        staging = Path(temporary) / "data"
        staging.mkdir()
        for name, raw in blobs.items():
            path = staging / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        (staging / "snapshot.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        # No replace/overwrite: completed snapshots are immutable inputs.
        if outdir.exists():
            raise FileExistsError(outdir)
        os.rename(staging, outdir)
    return manifest


def summarize(frame, info):
    summary, scores, deltas = [], [], []
    for condition in info["conditions"]:
        part = frame.loc[frame.condition.eq(condition)]
        succeeded = int(part.status.eq("completed").sum())
        missing = int(part.status.eq("missing").sum())
        recorded = len(part) - missing
        summary.append(
            {
                "condition": condition,
                "expected": len(part),
                "recorded": recorded,
                "completed": succeeded,
                "failed": recorded - succeeded,
                "missing": missing,
                "success_rate_recorded": succeeded / recorded
                if recorded
                else float("nan"),
                "recording_coverage": recorded / len(part),
                **{
                    column: part[column].sum(min_count=1)
                    for column in (
                        "actual_time_hours",
                        "estimated_cost_usd",
                        "total_tokens",
                    )
                },
            }
        )
        for name in info["dataset_order"]:
            cell = part.loc[part.dataset.eq(name)]
            valid = cell.loc[cell.status.eq("completed"), "score"]
            missing_count = int(cell.status.eq("missing").sum())
            scores.append(
                {
                    "dataset": name,
                    "problem": info["datasets"][name]["problem"],
                    "condition": condition,
                    "expected": len(cell),
                    "completed": len(valid),
                    "failed": len(cell) - len(valid) - missing_count,
                    "missing": missing_count,
                    "mean_score_successful": valid.mean(),
                    "std_score_successful": valid.std(ddof=1),
                }
            )
    baseline = frame.loc[frame.condition.eq("baseline")].set_index(
        ["repetition", "dataset"]
    )
    for row in frame.loc[frame.condition.ne("baseline")].itertuples():
        reference = baseline.loc[(row.repetition, row.dataset)]
        paired = row.status == "completed" and reference.status == "completed"
        improvement = ratio = float("nan")
        reason = "not jointly successful"
        if paired:
            if row.problem == "classification":
                improvement = 100 * (row.score - reference.score)
                reason = ""
            elif reference.score > 0:
                ratio = row.score / reference.score
                improvement = 100 * (1 - ratio)
                reason = ""
            else:
                reason = "baseline RMSE is zero; relative change undefined"
        deltas.append(
            {
                "condition": row.condition,
                "repetition": row.repetition,
                "dataset": row.dataset,
                "problem": row.problem,
                "baseline_status": reference.status,
                "candidate_status": row.status,
                "jointly_successful": paired,
                "baseline_score": reference.score,
                "candidate_score": row.score,
                "improvement": improvement,
                "rmse_ratio": ratio,
                "improvement_unit": "balanced_accuracy_percentage_points"
                if row.problem == "classification"
                else "RMSE_reduction_percent",
                "exclusion_reason": reason,
            }
        )
    return pd.DataFrame(summary), pd.DataFrame(scores), pd.DataFrame(deltas)


def _display(value):
    if isinstance(value, (float, np.floating)):
        return "—" if not math.isfinite(value) else f"{value:.6g}"
    return str(value)


def markdown_table(frame):
    def escape(value):
        return _display(value).replace("|", "\\|").replace("\n", " ")

    lines = [
        "| " + " | ".join(map(str, frame.columns)) + " |",
        "| " + " | ".join(["---"] * len(frame.columns)) + " |",
    ]
    lines += [
        "| " + " | ".join(escape(value) for value in row) + " |"
        for row in frame.itertuples(index=False, name=None)
    ]
    return "\n".join(lines)


def latex_table(frame):
    def escape(value):
        text = _display(value)
        replacements = {
            "\\": r"\textbackslash{}",
            "_": r"\_",
            "%": r"\%",
            "&": r"\&",
            "#": r"\#",
            "$": r"\$",
            "{": r"\{",
            "}": r"\}",
        }
        return "".join(replacements.get(character, character) for character in text)

    lines = [r"\begin{tabular}{" + "l" * len(frame.columns) + "}", r"\hline"]
    lines.append(" & ".join(escape(column) for column in frame.columns) + r" \\")
    lines.append(r"\hline")
    lines += [
        " & ".join(escape(value) for value in row) + r" \\"
        for row in frame.itertuples(index=False, name=None)
    ]
    return "\n".join(lines + [r"\hline", r"\end{tabular}"]) + "\n"


def _figures(frame, info, summary, scores, deltas, directory, formats, counts, details):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import TwoSlopeNorm

    directory.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titlesize": 13,
            "axes.labelsize": 10,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "savefig.facecolor": "white",
        }
    )
    long_labels = {
        "baseline": "Baseline",
        "specification-poor": "Poor\nspecification",
        "specification-specific": "Specific\nspecification",
        "validation-no-semantic-retry": "No semantic\nretry",
        "validation-no-execution-retry": "No execution\nretry",
        "no-csp": "No CSP",
    }
    labels = [long_labels.get(name, name) for name in info["conditions"]]
    pretty = lambda name: (
        name.replace("_", " ")
        .replace("mnist 784", "MNIST")
        .replace("har", "HAR")
        .replace("ames housing", "Ames housing")
        .replace("california housing", "California housing")
    )
    palette = ["#345995", "#8c6bb1", "#479f76", "#d79b35", "#c65f53", "#66717e"]

    def save(fig, name, footnote):
        fig.text(0.01, 0.015, footnote, fontsize=8, color="#555555", va="bottom")
        fig.tight_layout(rect=(0, 0.07, 1, 0.98))
        for extension in formats:
            fig.savefig(directory / f"{name}.{extension}", dpi=200, bbox_inches="tight")
        plt.close(fig)

    def heat(ax, matrix, annotations, names, title, cmap, norm=None, limits=None):
        cmap = plt.get_cmap(cmap).with_extremes(bad="#eeeeee")
        args = (
            {"norm": norm}
            if norm is not None
            else {"vmin": limits[0], "vmax": limits[1]}
        )
        artist = ax.imshow(
            np.ma.masked_invalid(matrix), aspect="auto", cmap=cmap, **args
        )
        ax.set_xticks(range(len(labels)), labels, fontsize=9)
        ax.set_yticks(range(len(names)), [pretty(name) for name in names])
        ax.set_title(title, pad=15)
        ax.set_xticks(np.arange(-0.5, len(labels), 1), minor=True)
        ax.set_yticks(np.arange(-0.5, len(names), 1), minor=True)
        ax.grid(which="minor", color="white", linewidth=2)
        ax.tick_params(which="both", length=0)
        for spine in ax.spines.values():
            spine.set_visible(False)
        for i, line in enumerate(annotations):
            for j, label in enumerate(line):
                value = matrix[i, j]
                color = "#222222"
                if np.isfinite(value):
                    rgb = cmap(artist.norm(value))[:3]
                    color = (
                        "white"
                        if sum(a * b for a, b in zip(rgb, (0.2126, 0.7152, 0.0722)))
                        < 0.48
                        else "#222222"
                    )
                ax.text(j, i, label, ha="center", va="center", fontsize=9, color=color)
        return artist

    def status_label(cell):
        return (
            "FAIL"
            if cell.failed and not cell.completed
            else "MISSING"
            if cell.missing and not cell.completed
            else "N/A"
        )

    fig, ax = plt.subplots(figsize=(10, 4.8))
    left = np.zeros(len(summary))
    for field, color in (
        ("completed", "#479f76"),
        ("failed", "#c65f53"),
        ("missing", "#cccccc"),
    ):
        values = summary[field].to_numpy()
        ax.barh(
            labels, values, left=left, label=field.title(), color=color, height=0.68
        )
        for i, v in enumerate(values):
            if v:
                ax.text(
                    left[i] + v / 2,
                    i,
                    str(v),
                    ha="center",
                    va="center",
                    color="white" if field != "missing" else "#222222",
                )
        left += values
    ax.invert_yaxis()
    ax.set_xlabel("Dataset executions")
    ax.set_title("Execution outcomes")
    ax.legend(loc="lower right", frameon=False)
    save(
        fig,
        "01_outcomes",
        "All selected repetitions. Missing outcomes are not failures.",
    )

    for problem, stem in (
        ("classification", "02_classification_scores"),
        ("regression", "03_regression_rmse_ratio"),
    ):
        names = [
            n
            for n in info["dataset_order"]
            if info["datasets"][n]["problem"] == problem
        ]
        if not names:
            continue
        matrix = np.full((len(names), len(labels)), np.nan)
        annotations = []
        for i, name in enumerate(names):
            line = []
            for j, condition in enumerate(info["conditions"]):
                cell = scores.loc[
                    scores.dataset.eq(name) & scores.condition.eq(condition)
                ].iloc[0]
                value, n = cell.mean_score_successful, int(cell.completed)
                if problem == "regression":
                    if condition == "baseline":
                        ref = frame.loc[
                            frame.dataset.eq(name) & frame.condition.eq("baseline")
                        ]
                        n = int((ref.status.eq("completed") & ref.score.gt(0)).sum())
                        value = 1.0 if n else float("nan")
                    else:
                        pairs = deltas.loc[
                            deltas.dataset.eq(name) & deltas.condition.eq(condition),
                            "rmse_ratio",
                        ]
                        value, n = pairs.mean(), int(pairs.notna().sum())
                matrix[i, j] = value
                line.append(
                    f"{value:.3f}"
                    + ("x" if problem == "regression" else "")
                    + f"\nn={n}/{int(cell.expected)}"
                    if pd.notna(value)
                    else status_label(cell)
                )
            annotations.append(line)
        fig, ax = plt.subplots(figsize=(11.5, max(3.8, len(names) * 0.66 + 1.6)))
        if problem == "classification":
            artist = heat(
                ax,
                matrix,
                annotations,
                names,
                "Classification",
                "Blues",
                limits=(0, 1),
            )
            fig.colorbar(
                artist, ax=ax, shrink=0.8, label="Balanced accuracy"
            )
        else:
            # Symmetric log-ratios put neutral white exactly at 1x. A 6.55x outlier
            # cannot shift the baseline into the green end of a linear palette.
            logs = np.log2(np.where(matrix > 0, matrix, np.nan))
            span = max(
                0.15, float(np.nanmax(np.abs(logs))) if np.isfinite(logs).any() else 1
            )
            artist = heat(
                ax,
                logs,
                annotations,
                names,
                "Regression | RMSE relative to AGE-ML baseline",
                "BrBG_r",
                norm=TwoSlopeNorm(vmin=-span, vcenter=0, vmax=span),
            )
            bar = fig.colorbar(
                artist,
                ax=ax,
                shrink=0.8,
                label="RMSE ratio (log scale; lower is better)",
            )
            ticks = np.linspace(-span, span, 5)
            bar.set_ticks(ticks, labels=[f"{2**x:.2g}x" for x in ticks])
        save(
            fig,
            stem,
            "Selection CV, not independent test. Means use successful observations; regression ratios use matched repetitions.\nn = valid observations / expected; FAIL is not zero. See paired changes for small differences.",
        )

    fig, axes = plt.subplots(1, 2, figsize=(12, 5.2))
    for ax, field, title in zip(
        axes,
        ("actual_time_hours", "estimated_cost_usd"),
        ("Recorded wall time (hours)", "Estimated LLM cost (USD)"),
    ):
        ax.barh(labels, summary[field], color=palette[: len(labels)])
        ax.invert_yaxis()
        ax.set_title(title)
        ax.grid(axis="x", alpha=0.15)
        ax.set_axisbelow(True)
    save(
        fig,
        "04_resources",
        "Totals across recorded outcomes, including failures. Cost is estimated; wall time includes overhead.",
    )

    names = [
        n
        for n in info["dataset_order"]
        if info["datasets"][n]["problem"] == "classification"
    ]
    if names and not deltas.empty:
        rows = math.ceil(len(names) / 3)
        fig, axes = plt.subplots(rows, 3, figsize=(13, rows * 3.6), squeeze=False)
        conditions = [c for c in info["conditions"] if c != "baseline"]
        for ax, name in zip(axes.flat, names):
            for j, condition in enumerate(conditions):
                values = (
                    deltas.loc[
                        deltas.dataset.eq(name) & deltas.condition.eq(condition),
                        "improvement",
                    ]
                    .dropna()
                    .to_numpy()
                )
                if len(values):
                    offsets = (
                        np.linspace(-0.1, 0.1, len(values)) if len(values) > 1 else [0]
                    )
                    ax.scatter(
                        values,
                        j + np.array(offsets),
                        s=24,
                        alpha=0.65,
                        color=palette[j + 1],
                    )
                    ax.scatter(
                        [np.mean(values)],
                        [j],
                        s=70,
                        marker="D",
                        color=palette[j + 1],
                        edgecolors="white",
                        linewidths=0.8,
                    )
                else:
                    ax.text(
                        0.97,
                        j,
                        "No valid pair",
                        transform=ax.get_yaxis_transform(),
                        ha="right",
                        va="center",
                        fontsize=8,
                        color="#777777",
                    )
            ax.axvline(0, color="#777777", linewidth=0.8)
            ax.set_yticks(
                range(len(conditions)),
                [long_labels.get(c, c).replace("\n", " ") for c in conditions],
                fontsize=8,
            )
            ax.invert_yaxis()
            ax.set_title(pretty(name))
            ax.set_xlabel("Change in balanced accuracy (pp)")
            ax.grid(axis="x", alpha=0.15)
        for ax in list(axes.flat)[len(names) :]:
            ax.set_visible(False)
        fig.suptitle("Classification | paired changes from baseline", fontsize=15)
        save(
            fig,
            "05_classification_paired_changes",
            "Dots: individual matched repetitions. Diamonds: mean; positive is better. No confidence intervals.\nSelection CV only. Identical points can overlap; technical repetitions share the recorded seeds.",
        )

    for repetition in info["repetitions"]:
        part = counts.loc[counts.repetition.eq(repetition)]
        for stem, fields, titles, note in (
            (
                "06_pipeline_activity",
                ("pipelines_found", "pipeline_budget", "actual_pipelines"),
                (
                    "Enumerated structures",
                    "Configured pipeline budget",
                    "Completed pipeline-agent runs",
                ),
                "Counts per dataset and condition. Completed pipeline-agent runs come from returned worker states, not all starts or successful fits.\nNo CSP proposes one structure; the configured budget is an upper bound, not the number evaluated.",
            ),
            (
                "07_candidate_instances",
                ("candidate_records", "eligible_candidates"),
                ("Recorded candidate attempts", "Candidates eligible for selection"),
                "One candidate = pipeline code + hyperparameters + execution attempt. Counts exclude unrecorded/interrupted work.\nN/A = detailed evidence unavailable; it never means zero. Ten CV folds are not ten hyperparameter instances.",
            ),
        ):
            fig, axes = plt.subplots(
                1, len(fields), figsize=(6.4 * len(fields), 8), squeeze=False
            )
            for ax, field, title in zip(axes.flat, fields, titles):
                matrix = np.full((len(info["dataset_order"]), len(labels)), np.nan)
                annotations = []
                for i, name in enumerate(info["dataset_order"]):
                    line = []
                    for j, condition in enumerate(info["conditions"]):
                        cell = part.loc[
                            part.dataset.eq(name) & part.condition.eq(condition)
                        ].iloc[0]
                        value = cell[field]
                        matrix[i, j] = value
                        line.append(
                            f"{value:.0f}"
                            if pd.notna(value)
                            else "MISSING"
                            if cell.status == "missing"
                            else "N/A"
                        )
                    annotations.append(line)
                vmax = (
                    max(1, float(np.nanmax(matrix))) if np.isfinite(matrix).any() else 1
                )
                heat(
                    ax,
                    matrix,
                    annotations,
                    info["dataset_order"],
                    title,
                    "Blues",
                    limits=(0, vmax),
                )
            fig.suptitle(f"Exploration activity | repetition {repetition}", fontsize=15)
            save(fig, f"{stem}_run-{repetition}", note)
        subset = details.loc[details.repetition.eq(repetition)]
        if not subset.empty:
            # Pipeline IDs are local to a dataset/condition/run. Each panel has
            # one condition; IDs are never treated as matched across conditions.
            for condition in info["conditions"]:
                local = subset.loc[subset.condition.eq(condition)]
                if local.empty:
                    continue
                wide = local.pivot(
                    index="dataset", columns="pipeline_id", values="candidate_records"
                ).reindex(info["dataset_order"])
                fig, ax = plt.subplots(figsize=(max(9, len(wide.columns) * 0.35), 6))
                artist = ax.imshow(
                    np.ma.masked_invalid(wide.to_numpy(dtype=float)),
                    aspect="auto",
                    cmap=plt.get_cmap("Blues").with_extremes(bad="#eeeeee"),
                    vmin=0,
                )
                ax.set_xticks(range(len(wide.columns)), wide.columns)
                ax.set_yticks(range(len(wide.index)), [pretty(n) for n in wide.index])
                ax.set_xlabel("Local pipeline ID")
                ax.set_title(
                    f"Candidate records per pipeline | {condition} | repetition {repetition}"
                )
                fig.colorbar(artist, ax=ax, label="Recorded candidate attempts")
                save(
                    fig,
                    f"08_instances_per_pipeline_{condition}_run-{repetition}",
                    "Grey = no recorded candidate for this local pipeline ID; not evidence of zero attempts. IDs are not matched across conditions.",
                )


def make_report(
    root, outdir, repetitions="1", allow_incomplete=False, formats=("png", "pdf")
):
    frame, info, inputs = load_campaign(root, repetitions, allow_incomplete)
    outdir = Path(outdir).resolve()
    if outdir.is_relative_to(info["root"]):
        raise ValueError("Report output must be outside the live campaign/snapshot")
    if any(extension not in ("png", "pdf", "svg") for extension in formats):
        raise ValueError("Formats must be png, pdf or svg")
    outdir.mkdir(parents=True, exist_ok=True)
    summary, scores, deltas = summarize(frame, info)
    counts, details = exploration_counts(frame, info)
    tables = outdir / "tables"
    tables.mkdir(exist_ok=True)
    frame.to_csv(tables / "run_metrics.csv", index=False)
    counts.to_csv(tables / "exploration_counts.csv", index=False)
    details.to_csv(tables / "pipeline_instances.csv", index=False)
    summary.to_csv(tables / "condition_summary.csv", index=False)
    scores.to_csv(tables / "dataset_scores.csv", index=False)
    deltas.to_csv(tables / "paired_deltas.csv", index=False)
    failures = frame.loc[~frame.status.isin(["completed", "missing"])]
    failures.to_csv(tables / "failed_runs.csv", index=False)
    status_matrix = frame.pivot(
        index=["dataset", "repetition"], columns="condition", values="status"
    ).reindex(columns=info["conditions"])
    status_matrix.to_csv(tables / "status_matrix.csv")
    wide = scores.pivot(
        index=["problem", "dataset"],
        columns="condition",
        values="mean_score_successful",
    ).reindex(columns=info["conditions"])
    wide.to_csv(tables / "score_matrix.csv")
    for name, table in (
        ("condition_summary", summary),
        ("score_matrix", wide.reset_index()),
        ("failed_runs", failures[["condition", "repetition", "dataset", "status"]]),
    ):
        (tables / f"{name}.md").write_text(
            markdown_table(table) + "\n", encoding="utf-8"
        )
        (tables / f"{name}.tex").write_text(latex_table(table), encoding="utf-8")
    _figures(
        frame,
        info,
        summary,
        scores,
        deltas,
        outdir / "figures",
        formats,
        counts,
        details,
    )
    recorded = int(frame.status.ne("missing").sum())
    completed = int(frame.status.eq("completed").sum())
    workers = sorted(frame.workers.dropna().unique().tolist())
    text = [
        f"# {info['frozen']['config']['name']} — repetitions {info['repetitions']}",
        f"Recorded outcomes: {recorded}/{len(frame)}; valid candidates: {completed}; failures: {len(failures)}; missing: {len(info['missing'])}.",
        f"Score role: **{info['score_role']}**. The CSV Baseline field is a protocol/reference label, never a HAMLET numeric score.",
        "This is descriptive analysis. No p-values or confidence intervals are inferred from CV folds or a single repetition. The campaign uses the recorded seeds; repetitions with the same seed are technical repetitions, not different seeds.",
        "Performance means/std use successful observations only. Missing outcomes are distinct from failures. Paired deltas require both conditions to succeed; exclusions remain in paired_deltas.csv. Regression RMSE is never averaged across datasets with different target scales.",
        f"Recorded worker settings: {workers}."
        + (" Resource settings differ across rows." if len(workers) > 1 else ""),
        "Failure status alone does not establish whether the cause was generated code, timeout or infrastructure. Detailed evidence must be inspected before attributing causes.",
        "## Exploration counts",
        "Pipelines Found counts enumerated structures; Pipeline Budget is the configured upper bound. Actual Pipelines counts completed execution-agent states with a tracking ID, not all started structures or fitted instances. Timed-out/failed agents can still have candidate records. In no-csp the planner proposes one structure. Candidate records require validation_candidates.csv with matching provenance. Their counts include only recorded evidence; killed workers can leave unrecorded work. Missing evidence is N/A, not zero. A candidate is a code/hyperparameter/execution-attempt combination; ten CV folds are not ten candidate instances. Local pipeline IDs are not comparable across conditions. See exploration_counts.csv and pipeline_instances.csv.",
        "## Outcomes and recorded resources",
        markdown_table(summary),
        "## Unsuccessful executions",
        markdown_table(failures[["condition", "repetition", "dataset", "status"]]),
        "## Scores by dataset",
        markdown_table(wide.reset_index()),
        "Figures and CSV/LaTeX tables are in figures/ and tables/. Figures omit no failure from the outcome counts; a failed score cell is not zero.",
    ]
    (outdir / "report.md").write_text("\n\n".join(text) + "\n", encoding="utf-8")
    provenance = {
        "campaign_identity": info["frozen"]["campaign_identity"],
        "repetitions": info["repetitions"],
        "analysis_script_sha256": sha256(Path(__file__).read_bytes()),
        "campaign_json_sha256": sha256((info["root"] / "campaign.json").read_bytes()),
        "input_csv_sha256": {name: sha256(raw) for name, raw in inputs.items()},
        "candidate_evidence_sha256": {
            name: sha256((info["root"] / name).read_bytes())
            for name in counts.evidence_source
            if name
        },
        "recorded": recorded,
        "completed": completed,
        "failed": len(failures),
        "missing": len(info["missing"]),
        "score_role": info["score_role"],
    }
    (outdir / "analysis_manifest.json").write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
    )
    return provenance


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    for command in ("snapshot", "report"):
        subparser = subcommands.add_parser(command)
        subparser.add_argument("--campaign", required=True, type=Path)
        subparser.add_argument("--outdir", required=True, type=Path)
        subparser.add_argument(
            "--repetitions", default="1", help="Comma-separated IDs or all; default: 1"
        )
        subparser.add_argument("--allow-incomplete", action="store_true")
        if command == "report":
            subparser.add_argument("--formats", nargs="+", default=["png", "pdf"])
    args = parser.parse_args(argv)
    try:
        if args.command == "snapshot":
            result = snapshot_campaign(
                args.campaign, args.outdir, args.repetitions, args.allow_incomplete
            )
            print(
                f"Snapshot: {args.outdir}; {result['recorded_outcomes']} outcomes, {result['completed']} completed"
            )
            for warning in result["evidence_warnings"]:
                print("Evidence warning:", warning)
        else:
            result = make_report(
                args.campaign,
                args.outdir,
                args.repetitions,
                args.allow_incomplete,
                args.formats,
            )
            print(
                f"Report: {args.outdir}; {result['recorded']} outcomes, {result['failed']} failures, {result['missing']} missing"
            )
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(2, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
