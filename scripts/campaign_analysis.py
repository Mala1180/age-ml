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
    "input_tokens": "Input Tokens",
    "output_tokens": "Output Tokens",
    "features": "Features",
    "instances": "Instances",
    "numeric_features": "Numeric Features",
    "discrete_features": "Discrete Features",
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
                for target, source in (
                    ("actual_time_hours", "Actual Time"),
                    ("equivalent_time_hours", "Equivalent Time"),
                    ("llm_inference_hours", "LLM Inference Time"),
                    ("ml_training_hours", "ML Training Time"),
                ):
                    value = original.get(source, "")
                    row[target] = (
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
    for column in [
        *RESOURCE_COLUMNS,
        "actual_time_hours",
        "equivalent_time_hours",
        "llm_inference_hours",
        "ml_training_hours",
    ]:
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


def mean_interval(values, bounds=None):
    """95% Student-t interval across repetitions, never across CV folds.

    This is a conditional descriptive interval: independent, representative
    repetitions are not established by identical recorded seeds.
    """
    from scipy.stats import t

    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if len(values) < 2:
        low = high = float("nan")
    else:
        half = (
            float(t.ppf(0.975, len(values) - 1))
            * values.std(ddof=1)
            / math.sqrt(len(values))
        )
        low, high = float(values.mean() - half), float(values.mean() + half)
    raw_low, raw_high = low, high
    if bounds is not None and math.isfinite(low):
        low = max(bounds[0], low)
        high = min(bounds[1], high) if bounds[1] is not None else high
    return {
        "ci95_low": low,
        "ci95_high": high,
        "ci95_low_unbounded": raw_low,
        "ci95_high_unbounded": raw_high,
    }


def format_mean_interval(mean, low, high):
    """Compact mean +/- the unbounded 95% Student-t half-width.

    Do not derive a symmetric margin from range-clipped endpoints. Distinguish
    zero variability from positive margins hidden by three-decimal rounding.
    """
    if not math.isfinite(mean):
        return "N/A"
    if not math.isfinite(low) or not math.isfinite(high):
        return f"{mean:,.3f} (CI N/A)"
    half = (high - low) / 2
    if half <= 4 * np.finfo(float).eps * max(1, abs(mean)):
        margin = "0"
    elif half < 0.0005:
        margin = "<0.001"
    else:
        margin = f"{half:,.3f}"
    return f"{mean:,.3f} ± {margin}"


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
                    **mean_interval(
                        valid,
                        (0, 1)
                        if info["datasets"][name]["problem"] == "classification"
                        else (0, None),
                    ),
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
            "±": r"\ensuremath{\pm}",
            "<": r"\textless{}",
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
    from matplotlib.ticker import MaxNLocator, NullLocator, StrMethodFormatter

    directory.mkdir(parents=True, exist_ok=True)
    # Remove only figures owned by the old report that the user retired.
    for pattern in (
        "06_pipeline_activity_run-*.*",
        "07_candidate_instances_run-*.*",
        "08_instances_per_pipeline_*.*",
        "03_regression_rmse_ratio.*",
    ):
        for path in directory.glob(pattern):
            if path.suffix in {".png", ".pdf", ".svg"}:
                path.unlink()
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
    conditions = info["conditions"]
    labels = [long_labels.get(c, c) for c in conditions]
    pretty = lambda n: {"har": "HAR", "mnist_784": "MNIST", "auto_mpg": "Auto MPG"}.get(
        n, n.replace("_", " ").capitalize()
    )
    palette = dict(
        zip(
            conditions,
            ["#345995", "#8c6bb1", "#479f76", "#d79b35", "#c65f53", "#66717e"],
        )
    )

    def save(fig, name, footnote, layout=True):
        fig.text(0.01, 0.015, footnote, fontsize=8, color="#555555", va="bottom")
        if layout:
            fig.tight_layout(rect=(0, 0.08, 1, 0.98))
        for extension in formats:
            fig.savefig(directory / f"{name}.{extension}", dpi=200, bbox_inches="tight")
        plt.close(fig)

    # 01: explicit numeric row positions, aligned summary, external legend.
    part = summary.set_index("condition").reindex(conditions)
    fig, ax = plt.subplots(figsize=(11.5, 5.4))
    positions = np.arange(len(conditions))
    left = np.zeros(len(conditions))
    for field, color, label in [
        ("completed", "#479f76", "Valid result"),
        ("failed", "#c65f53", "Recorded unsuccessful outcome"),
        ("missing", "#cccccc", "Missing outcome"),
    ]:
        values = part[field].to_numpy()
        ax.barh(positions, values, left=left, label=label, color=color, height=0.64)
        for i, value in enumerate(values):
            if value:
                ax.text(
                    left[i] + value / 2,
                    i,
                    str(int(value)),
                    ha="center",
                    va="center",
                    color="white" if field != "missing" else "#222222",
                    fontsize=10,
                )
        left += values
    ax.set_yticks(positions, labels)
    ax.set_ylim(len(conditions) - 0.4, -0.6)
    ax.set_xlim(0, max(1, float(part.expected.max())) * 1.015)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_xlabel("Dataset executions")
    ax.set_title("Execution outcomes", pad=48)
    ax.legend(
        loc="lower left", bbox_to_anchor=(0, 1.015), ncol=3, frameon=False, fontsize=9
    )
    save(
        fig,
        "01_outcomes",
        "All selected repetitions. Unsuccessful outcomes include no valid candidate; missing outcomes remain separate.",
    )

    # 02: annotations keep the actual values, even below the color scale floor.
    names = [
        n
        for n in info["dataset_order"]
        if info["datasets"][n]["problem"] == "classification"
    ]
    if names:
        matrix = np.full((len(names), len(conditions)), np.nan)
        annotations = []
        for i, name in enumerate(names):
            line = []
            for j, condition in enumerate(conditions):
                cell = scores.loc[
                    scores.dataset.eq(name) & scores.condition.eq(condition)
                ].iloc[0]
                matrix[i, j] = cell.mean_score_successful
                n = int(cell.completed)
                if n:
                    value = format_mean_interval(
                        cell.mean_score_successful,
                        cell.ci95_low_unbounded,
                        cell.ci95_high_unbounded,
                    )
                    line.append(f"{value}\nn={n}/{int(cell.expected)}")
                else:
                    line.append("NO VALID SCORE" if cell.failed else "MISSING")
            annotations.append(line)
        fig, ax = plt.subplots(figsize=(13.2, max(5, len(names) * 0.95 + 1.6)))
        cmap = plt.get_cmap("Blues").with_extremes(bad="#eeeeee", under="#fff0cc")
        artist = ax.imshow(
            np.ma.masked_invalid(matrix), aspect="auto", cmap=cmap, vmin=0.8, vmax=1
        )
        ax.set_xticks(range(len(conditions)), labels, fontsize=9)
        ax.set_yticks(range(len(names)), [pretty(n) for n in names])
        ax.set_xticks(np.arange(-0.5, len(conditions), 1), minor=True)
        ax.set_yticks(np.arange(-0.5, len(names), 1), minor=True)
        ax.grid(which="minor", color="white", linewidth=2)
        ax.tick_params(which="both", length=0)
        for spine in ax.spines.values():
            spine.set_visible(False)
        for i, line in enumerate(annotations):
            for j, label in enumerate(line):
                value = matrix[i, j]
                rgb = cmap(artist.norm(value))[:3] if np.isfinite(value) else (1, 1, 1)
                luminance = sum(a * b for a, b in zip(rgb, (0.2126, 0.7152, 0.0722)))
                ax.text(
                    j,
                    i,
                    label,
                    ha="center",
                    va="center",
                    fontsize=8.5,
                    color="white" if luminance < 0.48 else "#222222",
                )
        ax.set_title("Classification | mean balanced accuracy ± 95% margin", pad=16)
        extend = (
            "min"
            if np.isfinite(matrix).any() and np.nanmin(matrix) < 0.8
            else "neither"
        )
        fig.colorbar(
            artist,
            ax=ax,
            shrink=0.8,
            extend=extend,
            label="Balanced accuracy (color range 0.8-1.0)",
        )
        save(
            fig,
            "02_classification_scores",
            "Cells: mean ± 95% Student-t margin; valid/expected repetitions. ± 0 = no observed variation; ± <0.001 = a positive margin hidden by rounding.\nSelection CV; intervals describe technical repetition variability under an independence assumption, not generalization uncertainty.",
        )

    # 03: absolute RMSE on a separate target scale for each dataset.
    regression = [
        n
        for n in info["dataset_order"]
        if info["datasets"][n]["problem"] == "regression"
    ]
    if regression:
        fig, axes = plt.subplots(
            len(regression), 1, figsize=(12, 3.1 * len(regression) + 0.8), squeeze=False
        )
        for ax, name in zip(axes.flat, regression):
            positive = []
            for j, condition in enumerate(conditions):
                values = (
                    frame.loc[
                        frame.dataset.eq(name)
                        & frame.condition.eq(condition)
                        & frame.status.eq("completed"),
                        "score",
                    ]
                    .dropna()
                    .to_numpy()
                )
                if len(values):
                    positive.extend(values)
                    ax.scatter(
                        values,
                        j + np.linspace(-0.12, 0.12, len(values)),
                        s=27,
                        color=palette[condition],
                        alpha=0.6,
                    )
                    ax.scatter(
                        [values.mean()],
                        [j],
                        marker="D",
                        s=65,
                        color=palette[condition],
                        edgecolors="white",
                        linewidths=0.7,
                        zorder=4,
                    )
                    text = f"{values.mean():,.3f}  (n={len(values)}/{len(info['repetitions'])})"
                else:
                    text = "No valid score"
                ax.text(
                    1.015,
                    j,
                    text,
                    transform=ax.get_yaxis_transform(),
                    va="center",
                    fontsize=9,
                )
            if positive and min(positive) > 0:
                ax.set_xscale("log")
                low, high = min(positive), max(positive)
                if math.isclose(low, high):
                    low, high = low / 1.02, high * 1.02
                ax.set_xticks(np.geomspace(low, high, 5))
                ax.xaxis.set_major_formatter(
                    StrMethodFormatter("{x:,.0f}" if high >= 1000 else "{x:.2f}")
                )
                ax.xaxis.set_minor_locator(NullLocator())
            ax.set_yticks(
                range(len(conditions)),
                [x.replace("\n", " ") for x in labels],
                fontsize=9,
            )
            ax.set_ylim(len(conditions) - 0.5, -0.5)
            ax.set_title(pretty(name), loc="left")
            ax.set_xlabel(
                "Absolute RMSE (lower is better; logarithmic axis when all values are positive)"
            )
            ax.text(
                1.015,
                1.04,
                "Mean RMSE and valid/expected",
                transform=ax.transAxes,
                fontsize=9,
            )
            ax.grid(axis="x", which="major", alpha=0.2)
            ax.margins(x=0.12)
        save(
            fig,
            "03_regression_rmse",
            "Dots: successful repetitions; diamonds: arithmetic means of absolute RMSE. Separate target scales for each dataset.\nSelection CV only; unsuccessful outcomes are not zero scores. No ratios to the AGE-ML baseline.",
        )

    # 04: unchanged resource totals, including recorded unsuccessful outcomes.
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.2))
    for ax, field, title in zip(
        axes,
        ("actual_time_hours", "estimated_cost_usd"),
        ("Recorded wall time (hours)", "Estimated LLM cost (USD)"),
    ):
        ax.barh(
            range(len(conditions)), part[field], color=[palette[c] for c in conditions]
        )
        ax.set_yticks(range(len(conditions)), labels)
        ax.invert_yaxis()
        ax.set_title(title)
        ax.grid(axis="x", alpha=0.15)
        ax.set_axisbelow(True)
    save(
        fig,
        "04_resources",
        "Totals across recorded outcomes, including failures. Cost is estimated; wall time includes overhead.",
    )

    # 05: separate absolute baseline strip, retaining genuinely paired deltas.
    if names and not deltas.empty:
        rows = math.ceil(len(names) / 2)
        fig = plt.figure(figsize=(17, rows * 3.6 + 0.6))
        grid = fig.add_gridspec(rows, 2, wspace=0.35, hspace=0.5)
        ablations = [c for c in conditions if c != "baseline"]
        for index, name in enumerate(names):
            inner = grid[index // 2, index % 2].subgridspec(
                1, 2, width_ratios=[1, 3.1], wspace=1.25
            )
            base_ax = fig.add_subplot(inner[0])
            ax = fig.add_subplot(inner[1])
            values = (
                frame.loc[
                    frame.dataset.eq(name)
                    & frame.condition.eq("baseline")
                    & frame.status.eq("completed"),
                    "score",
                ]
                .dropna()
                .to_numpy()
            )
            if len(values):
                base_ax.scatter(
                    values,
                    np.linspace(-0.14, 0.14, len(values)),
                    color=palette["baseline"],
                    s=30,
                    alpha=0.7,
                )
                base_ax.scatter(
                    [values.mean()],
                    [0],
                    marker="D",
                    color=palette["baseline"],
                    s=65,
                    edgecolors="white",
                    zorder=4,
                )
                base_ax.set_title(
                    f"Baseline\nmean {values.mean():.3f}\nn={len(values)}/{len(info['repetitions'])}",
                    fontsize=10,
                )
                padding = max(float(np.ptp(values)) * 0.2, 0.0005)
                base_ax.set_xlim(
                    max(0, values.min() - padding), min(1, values.max() + padding)
                )
            else:
                base_ax.text(
                    0.5,
                    0.5,
                    "No valid baseline",
                    transform=base_ax.transAxes,
                    ha="center",
                )
                base_ax.set_title("Baseline", fontsize=10)
            base_ax.set_ylim(-0.6, 0.6)
            base_ax.set_yticks([])
            base_ax.xaxis.set_major_locator(MaxNLocator(2))
            base_ax.xaxis.set_major_formatter(StrMethodFormatter("{x:.4f}"))
            base_ax.tick_params(axis="x", labelrotation=35, labelsize=8)
            base_ax.set_xlabel("Absolute BA", fontsize=9)
            base_ax.grid(axis="x", alpha=0.15)
            for j, condition in enumerate(ablations):
                paired = (
                    deltas.loc[
                        deltas.dataset.eq(name) & deltas.condition.eq(condition),
                        "improvement",
                    ]
                    .dropna()
                    .to_numpy()
                )
                if len(paired):
                    ax.scatter(
                        paired,
                        j + np.linspace(-0.12, 0.12, len(paired)),
                        s=25,
                        alpha=0.65,
                        color=palette[condition],
                    )
                    ax.scatter(
                        [paired.mean()],
                        [j],
                        s=65,
                        marker="D",
                        color=palette[condition],
                        edgecolors="white",
                        linewidths=0.7,
                        zorder=4,
                    )
                else:
                    ax.text(
                        0.98,
                        j,
                        "No valid pair",
                        transform=ax.get_yaxis_transform(),
                        ha="right",
                        va="center",
                        fontsize=8,
                    )
            ax.axvline(0, color="#777777", linewidth=0.8)
            ax.set_yticks(
                range(len(ablations)),
                [long_labels.get(c, c).replace("\n", " ") for c in ablations],
                fontsize=8,
            )
            ax.set_ylim(len(ablations) - 0.5, -0.5)
            ax.set_title(pretty(name), fontsize=12)
            ax.set_xlabel("Paired change in BA (pp)", fontsize=9)
            ax.grid(axis="x", alpha=0.15)
        fig.subplots_adjust(left=0.055, right=0.99, bottom=0.11, top=0.94)
        save(
            fig,
            "05_classification_paired_changes",
            "Left strips: actual baseline balanced accuracy in each successful repetition. Right panels: ablation minus baseline in the SAME repetition.\nDots: individual repetitions; diamonds: means. Positive paired changes are better. Technical repetitions share recorded seeds; axes vary by dataset.",
            layout=False,
        )


def _paper_tables(frame, info, scores, directory):
    """Generate the paper's table layouts using current recorded observations.

    Historical reference scores and the qualitative comparison are explicitly
    sourced from the supplied draft; they are not current experimental results.
    """
    reference_path = (
        Path(__file__).resolve().parents[1] / "resources/paper-analysis-reference.json"
    )
    reference = json.loads(reference_path.read_text(encoding="utf-8"))
    names = info["dataset_order"]
    pretty = lambda n: {
        "har": "HAR",
        "mnist_784": "MNIST_784",
        "auto_mpg": "Auto MPG",
    }.get(n, n.replace("_", " ").title())

    def export(name, table):
        table.to_csv(directory / f"{name}.csv", index=False)
        (directory / f"{name}.md").write_text(
            markdown_table(table) + "\n", encoding="utf-8"
        )
        (directory / f"{name}.tex").write_text(latex_table(table), encoding="utf-8")

    datasets, discrepancies = [], []
    for name in names:
        entry = {
            "Dataset": pretty(name),
            "Problem": "C"
            if info["datasets"][name]["problem"] == "classification"
            else "R",
        }
        for field, title in [
            ("features", "Features"),
            ("instances", "Instances"),
            ("numeric_features", "Numeric"),
            ("discrete_features", "Discrete"),
        ]:
            observed = frame.loc[frame.dataset.eq(name), field].dropna().unique()
            if len(observed) > 1:
                raise ValueError(
                    f"Inconsistent dataset metadata: {name}.{field}: {observed}"
                )
            current = int(observed[0]) if len(observed) else float("nan")
            entry[title] = current
            historical = reference.get("dataset_table", {}).get(name, {}).get(field)
            if historical is not None and pd.notna(current) and current != historical:
                discrepancies.append(
                    {
                        "dataset": name,
                        "field": field,
                        "paper_value": historical,
                        "campaign_value": current,
                    }
                )
        datasets.append(entry)
    export("paper_table_1_datasets", pd.DataFrame(datasets))
    pd.DataFrame(
        discrepancies, columns=["dataset", "field", "paper_value", "campaign_value"]
    ).to_csv(directory / "paper_dataset_differences.csv", index=False)

    def duration(value):
        if pd.isna(value):
            return "N/A"
        seconds = round(value * 3600)
        return f"{seconds // 3600}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"

    resource_fields = [
        ("actual_time_hours", "Actual Time"),
        ("equivalent_time_hours", "Equivalent Time"),
        ("llm_inference_hours", "LLM Inference Time"),
        ("ml_training_hours", "ML Training Time"),
        ("actual_pipelines", "Actual P."),
        ("input_tokens", "Input Tokens"),
        ("output_tokens", "Output Tokens"),
        ("total_tokens", "Total Tokens"),
        ("estimated_cost_usd", "Putative Cost ($)"),
    ]
    for condition in info["conditions"]:
        presentation, numeric = [], []
        for name in names:
            part = frame.loc[frame.dataset.eq(name) & frame.condition.eq(condition)]
            cell = scores.loc[
                scores.dataset.eq(name) & scores.condition.eq(condition)
            ].iloc[0]
            n = int(cell.completed)
            historical = reference.get("performance_references", {}).get(name, {})
            score = float(cell.mean_score_successful)
            entry = {
                "Dataset": pretty(name),
                "Selected Score (mean ± 95% margin)": format_mean_interval(
                    score, cell.ci95_low_unbounded, cell.ci95_high_unbounded
                )
                if n
                else "N/A",
                "Valid/Expected": f"{n}/{int(cell.expected)}",
                "Historical Reference": f"{historical['score']:,.3f}"
                if historical
                else "N/A",
            }
            raw = {
                "dataset": name,
                "condition": condition,
                "model": info["frozen"]["config"]
                .get("model", {})
                .get("name", "unknown"),
                "score_role": info["score_role"],
                "expected": int(cell.expected),
                "completed": n,
                "failed": int(cell.failed),
                "missing": int(cell.missing),
                "mean_score_successful": score,
                "ci95_low": cell.ci95_low,
                "ci95_high": cell.ci95_high,
                "ci95_low_unbounded": cell.ci95_low_unbounded,
                "ci95_high_unbounded": cell.ci95_high_unbounded,
                "historical_reference_score": historical.get("score"),
                "historical_reference_source": historical.get("source", ""),
            }
            for field, label in resource_fields:
                values = part.loc[part.status.ne("missing"), field].dropna()
                mean = values.mean()
                raw[field + "_mean_recorded"] = mean
                raw[field + "_n_recorded"] = len(values)
                if field.endswith("_hours"):
                    entry[label] = duration(mean)
                elif pd.isna(mean):
                    entry[label] = "N/A"
                elif field == "estimated_cost_usd":
                    entry[label] = f"{mean:.3f}"
                elif field == "actual_pipelines":
                    entry[label] = f"{mean:.1f}"
                else:
                    entry[label] = f"{mean:,.0f}"
            presentation.append(entry)
            numeric.append(raw)
        table = pd.DataFrame(presentation)
        export(f"paper_results_{condition}", table)
        pd.DataFrame(numeric).to_csv(
            directory / f"paper_results_{condition}_statistics.csv", index=False
        )
        if condition == "baseline":
            model_name = info["frozen"]["config"].get("model", {}).get("name", "")
            number = (
                2
                if model_name.startswith("gemini-3.1-flash-lite")
                else 3
                if model_name.startswith("gemini-2.5-flash")
                else None
            )
            if number:
                export(f"paper_table_{number}_results", table)
    qualitative = pd.DataFrame(reference["qualitative_comparison"]).map(
        lambda v: "Yes" if v is True else "No" if v is False else v
    )
    export("paper_table_4_qualitative", qualitative)
    (directory / "paper_reference_used.json").write_text(
        json.dumps(reference, indent=2) + "\n", encoding="utf-8"
    )
    return {
        "paper_reference_sha256": sha256(reference_path.read_bytes()),
        "dataset_metadata_differences": discrepancies,
    }


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
    paper_provenance = _paper_tables(frame, info, scores, tables)
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
        "This is descriptive analysis. No p-values are computed. 95% Student-t intervals are calculated across successful repetitions (n >= 2), never across CV folds. They assume independent representative repetitions and describe technical variability here, not uncertainty on generalization or different data splits. Compact annotations use mean ± the original symmetric t margin. CSVs retain both original endpoints and endpoints intersected with the known metric range ([0,1] for BA and [0,infinity) for RMSE). The ± notation is a 95% margin, not a standard deviation; it may extend beyond the metric bounds. Zero-width intervals indicate identical observed values, not guaranteed reproducibility. The campaign uses the recorded seeds; repetitions with the same seed are technical repetitions, not different seeds.",
        "Performance means/std use successful observations only. Missing outcomes are distinct from failures. Paired deltas require both conditions to succeed; exclusions remain in paired_deltas.csv. Regression RMSE is never averaged across datasets with different target scales.",
        f"Recorded worker settings: {workers}."
        + (" Resource settings differ across rows." if len(workers) > 1 else ""),
        "Failure status alone does not establish whether the cause was generated code, timeout or infrastructure. Detailed evidence must be inspected before attributing causes.",
        "## Paper tables",
        "paper_table_1_datasets uses current recorded metadata. paper_dataset_differences.csv lists discrepancies from the supplied paper; historical values are never substituted for observed values. paper_results_<condition> mirrors Tables 2/3 and adds intervals and valid/expected counts. For the full AGE-ML baseline condition, paper_table_2_results or paper_table_3_results is also generated according to the model. Score means use successful runs; resource means include all recorded outcomes, including unsuccessful ones. Numeric statistics retain resource-specific denominators. Actual P. counts returned completed execution-agent states, not every attempted pipeline or successful fit.",
        "Historical Reference is transcribed from Tables 2/3: HAMLET for classification and Kaggle notebooks for regression. It is separate from the AGE-ML baseline condition. Protocol and dataset comparability must be checked before making claims. Table 4 is a static transcription of the paper's qualitative comparison, not a recomputed experiment or an independently verified current assessment. Reference provenance is saved in tables/paper_reference_used.json.",
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
        **paper_provenance,
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
