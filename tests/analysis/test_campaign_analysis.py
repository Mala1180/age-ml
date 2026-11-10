"""Exercise the real campaign layout, first-repetition export and failure counts."""

import copy
import csv
import json
import runpy
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from scripts import campaign_analysis as analysis

CONDITIONS = [
    "baseline",
    "specification-poor",
    "specification-specific",
    "validation-no-semantic-retry",
    "validation-no-execution-retry",
    "no-csp",
]
DATASETS = [
    ("wilt", "classification", 40983),
    ("texture", "classification", 40499),
    ("madelon", "classification", 1485),
    ("har", "classification", 1478),
    ("adult", "classification", 1590),
    ("mnist_784", "classification", 554),
    ("california_housing", "regression", 43939),
    ("ames_housing", "regression", 42165),
    ("auto_mpg", "regression", 196),
]
FAILURES = {
    ("validation-no-execution-retry", "california_housing"),
    ("no-csp", "adult"),
    ("no-csp", "ames_housing"),
}


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


@pytest.fixture
def campaign(tmp_path):
    root = tmp_path / "live-campaign"
    root.mkdir()
    spec = tmp_path / "spec.yml"
    spec.write_text("budgets:\n  workers: 8\n")
    datasets = {
        problem: {
            name: identifier for name, task, identifier in DATASETS if task == problem
        }
        for problem in ("classification", "regression")
    }
    frozen = {
        "campaign_identity": "c" * 64,
        "config": {
            "name": "test-campaign",
            "datasets": datasets,
            "repetitions": [1, 2, 3, 4, 5],
            "specification": str(spec),
            "evaluation_protocol": "hamlet_cv",
            "run_seed": 42,
        },
        "plan": {
            "jobs": [{"id": name} for name in CONDITIONS],
            "protocol_version": "ageml-evaluation-v3",
        },
        "source_evidence": {
            name: {
                "split_identity": analysis.sha256(name.encode()),
                "manifest": {"seed": 42},
            }
            for name, _, _ in DATASETS
        },
        "base_specification_sha256": analysis.sha256(spec.read_bytes()),
    }
    (root / "campaign.json").write_text(json.dumps(frozen))
    for index, condition in enumerate(CONDITIONS):
        rows = []
        for position, (name, problem, identifier) in enumerate(DATASETS):
            status = (
                "no_valid_candidate" if (condition, name) in FAILURES else "completed"
            )
            score = (
                0.8 + index * 0.01
                if problem == "classification"
                else (position + 1) * 100 * (1 + index * 0.05)
            )
            identity = analysis.sha256(f"{condition}:{name}".encode())
            row = {
                "Dataset": name,
                "OpenML ID": identifier,
                "Problem": problem,
                "Status": status,
                "Protocol Version": "ageml-evaluation-v3",
                "Evaluation Protocol": "hamlet_cv",
                "Validation Metric": "balanced_accuracy"
                if problem == "classification"
                else "rmse",
                analysis.CV_SCORE: score if status == "completed" else "",
                analysis.TEST_SCORE: "",
                "Run Identity": identity,
                "Resume Identity": identity,
                "Split Identity": frozen["source_evidence"][name]["split_identity"],
                "Baseline": "hamlet",
                "Actual Time": "0:01:00",
                "Putative Cost ($)": "0.01",
                "Total Tokens": "100",
                "Workers": "8",
                "Actual Pipelines": "30",
            }
            rows.append(row)
            base = root / condition / "run-1/ageml-evaluation-v3"
            protocol = base / "protocol" / name / identity
            protocol.mkdir(parents=True)
            selection = {
                "selected": {"run_id": identity[:32]} if status == "completed" else None
            }
            (protocol / "selection.json").write_text(json.dumps(selection))
            (protocol / "result.json").write_text(
                json.dumps(
                    {
                        "run_identity": identity,
                        "status": status,
                        "search_cv_score": score if status == "completed" else None,
                        "selection_sha256": analysis.sha256(
                            (protocol / "selection.json").read_bytes()
                        ),
                    }
                )
            )
            (protocol / "exploration_failures.json").write_text("[]")
            winner = base / "artifacts" / name / identity / "best_pipeline"
            winner.mkdir(parents=True)
            (winner / "code.py").write_text("# generated model factory\n")
            (winner / "pipeline.md").write_text("Pipeline description\n")
            (winner / "model.pkl").write_bytes(
                b"binary must not enter analysis snapshot"
            )
        write_csv(root / condition / "run-1/ageml-evaluation-v3/results.csv", rows)
    # Exactly the user's state: first 54 outcomes plus eight from repetition 2.
    baseline = (
        pd.read_csv(root / "baseline/run-1/ageml-evaluation-v3/results.csv")
        .astype(object)
        .fillna("")
    )
    write_csv(
        root / "baseline/run-2/ageml-evaluation-v3/results.csv",
        baseline.iloc[:8].to_dict("records"),
    )
    return root


def test_first_repetition_excludes_active_second_repetition_and_counts_failures(
    campaign,
):
    frame, info, _ = analysis.load_campaign(campaign)
    assert len(frame) == 54
    assert frame.repetition.unique().tolist() == [1]
    assert frame.status.eq("completed").sum() == 51
    summary, scores, deltas = analysis.summarize(frame, info)
    assert summary.set_index("condition").loc["no-csp", "completed"] == 7
    assert summary.failed.sum() == 3 and summary.missing.sum() == 0
    assert summary.estimated_cost_usd.sum() == pytest.approx(0.54)
    failure = scores.loc[
        scores.dataset.eq("adult") & scores.condition.eq("no-csp")
    ].iloc[0]
    assert failure.completed == 0 and pd.isna(failure.mean_score_successful)
    assert len(deltas) == 45 and deltas.jointly_successful.sum() == 42
    assert frame.score_role.eq("selection_cv_not_independent_test").all()


def test_paired_deltas_keep_direction_and_do_not_average_raw_regression_scales(
    campaign,
):
    frame, info, _ = analysis.load_campaign(campaign)
    _, _, deltas = analysis.summarize(frame, info)
    classification = deltas.loc[
        deltas.condition.eq("specification-poor") & deltas.problem.eq("classification")
    ]
    regression = deltas.loc[
        deltas.condition.eq("specification-poor") & deltas.problem.eq("regression")
    ]
    assert classification.improvement.tolist() == pytest.approx([1] * 6)
    assert regression.rmse_ratio.tolist() == pytest.approx([1.05] * 3)
    assert regression.improvement.tolist() == pytest.approx([-5] * 3)


def test_snapshot_is_lightweight_immutable_and_preserves_source_bytes(
    campaign, tmp_path
):
    before = {
        str(p.relative_to(campaign)): p.read_bytes()
        for p in campaign.rglob("*")
        if p.is_file()
    }
    destination = tmp_path / "snapshot"
    manifest = analysis.snapshot_campaign(campaign, destination)
    assert manifest["recorded_outcomes"] == 54 and manifest["completed"] == 51
    assert not manifest["evidence_warnings"]
    assert len(list(destination.rglob("results.csv"))) == 6
    assert not list(destination.rglob("model.pkl"))
    assert not list(destination.rglob("run-2"))
    assert len(list(destination.rglob("exploration_failures.json"))) == 54
    assert analysis.load_campaign(destination)[0].status.eq("completed").sum() == 51
    assert before == {
        str(p.relative_to(campaign)): p.read_bytes()
        for p in campaign.rglob("*")
        if p.is_file()
    }
    with pytest.raises(ValueError, match="new directory"):
        analysis.snapshot_campaign(campaign, destination)


def test_snapshot_tampering_is_rejected(campaign, tmp_path):
    destination = tmp_path / "snapshot"
    analysis.snapshot_campaign(campaign, destination)
    csv_path = next(destination.rglob("results.csv"))
    csv_path.write_bytes(csv_path.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="Snapshot file"):
        analysis.load_campaign(destination)


def test_incomplete_repetitions_require_explicit_opt_in(campaign):
    with pytest.raises(ValueError, match="incomplete"):
        analysis.load_campaign(campaign, "2")
    frame, _, _ = analysis.load_campaign(campaign, "2", allow_incomplete=True)
    assert len(frame) == 54 and frame.status.eq("missing").sum() == 46


def test_missing_outcomes_are_not_classified_as_failed(campaign):
    frame, info, _ = analysis.load_campaign(campaign, "2", allow_incomplete=True)
    summary, _, _ = analysis.summarize(frame, info)
    assert summary.failed.sum() == 0
    assert summary.missing.sum() == 46
    assert summary.completed.sum() == 8


@pytest.mark.parametrize(
    "kind", ["duplicate", "protocol", "score", "split", "test-score"]
)
def test_malformed_or_incompatible_rows_are_rejected(campaign, kind):
    path = campaign / "baseline/run-1/ageml-evaluation-v3/results.csv"
    with path.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    if kind == "duplicate":
        rows.append(copy.deepcopy(rows[0]))
    elif kind == "protocol":
        rows[0]["Evaluation Protocol"] = "holdout"
    elif kind == "score":
        rows[0][analysis.CV_SCORE] = ""
    elif kind == "split":
        rows[0]["Split Identity"] = "f" * 64
    else:
        rows[0][analysis.TEST_SCORE] = "0.9"
    write_csv(path, rows)
    with pytest.raises(ValueError):
        analysis.load_campaign(campaign)


def test_zero_baseline_rmse_has_no_infinite_percentage_change(campaign):
    frame, info, _ = analysis.load_campaign(campaign)
    frame.loc[
        frame.condition.eq("baseline") & frame.problem.eq("regression"), "score"
    ] = 0
    _, _, deltas = analysis.summarize(frame, info)
    regression = deltas.loc[deltas.problem.eq("regression")]
    assert regression.rmse_ratio.isna().all()
    assert regression.improvement.isna().all()
    assert regression.exclusion_reason.str.contains("zero").any()


def test_snapshot_and_reports_cannot_write_inside_live_campaign(campaign):
    with pytest.raises(ValueError):
        analysis.snapshot_campaign(campaign, campaign / "snapshot")
    with pytest.raises(ValueError):
        analysis.make_report(campaign, campaign / "report")


def test_real_report_generates_csv_markdown_latex_and_headless_figures(
    campaign, tmp_path
):
    output = tmp_path / "report"
    figures = output / "figures"
    figures.mkdir(parents=True)
    for name in ("06_pipeline_activity_run-1.png", "03_regression_rmse_ratio.pdf"):
        (figures / name).write_text("retired output")
    result = analysis.make_report(campaign, output, formats=("png", "pdf"))
    assert not (figures / "06_pipeline_activity_run-1.png").exists()
    assert not (figures / "03_regression_rmse_ratio.pdf").exists()
    assert (
        result["recorded"] == 54 and result["completed"] == 51 and result["failed"] == 3
    )
    assert len(list((output / "figures").glob("*.png"))) == 5
    assert len(list((output / "figures").glob("*.pdf"))) == 5
    for name in ("score_matrix", "condition_summary", "failed_runs"):
        assert (
            (output / "tables" / f"{name}.tex")
            .read_text()
            .startswith(r"\begin{tabular}")
        )
    assert len(pd.read_csv(output / "tables/failed_runs.csv")) == 3
    text = (output / "report.md").read_text()
    assert "not_independent_test" in text
    assert "No p-values" in text
    assert "HAMLET numeric score" in text


def test_legacy_entry_point_delegates_current_layout(campaign, tmp_path, monkeypatch):
    import subprocess
    import sys

    legacy = (
        Path(__file__).resolve().parents[2]
        / "old-results/generate_experiment_figures.py"
    )
    namespace = runpy.run_path(str(legacy))
    commands = []
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda command: commands.append(command) or SimpleNamespace(returncode=0),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(legacy),
            str(campaign),
            "--outdir",
            str(tmp_path / "report"),
            "--formats",
            "png",
        ],
    )
    with pytest.raises(SystemExit) as result:
        namespace["main"]()
    assert result.value.code == 0
    assert commands[0][2] == "report" and "--repetitions" in commands[0]


def test_legacy_csv_loader_keeps_historical_score_and_numeric_baseline(tmp_path):
    legacy = (
        Path(__file__).resolve().parents[2]
        / "old-results/generate_experiment_figures.py"
    )
    namespace = runpy.run_path(str(legacy))
    path = tmp_path / "old.csv"
    pd.DataFrame(
        {"Dataset": ["wilt"], "Best Test-set Score": [0.9], "Baseline": [0.8]}
    ).to_csv(path, index=False)
    frame = namespace["load_results"](path)
    assert frame["Best Test-set Score"].iloc[0] == 0.9
    assert frame.Baseline.iloc[0] == 0.8


def test_new_result_file_cannot_be_injected_into_incomplete_snapshot(
    campaign, tmp_path
):
    destination = tmp_path / "snapshot"
    analysis.snapshot_campaign(campaign, destination, "2", allow_incomplete=True)
    source = campaign / "specification-poor/run-1/ageml-evaluation-v3/results.csv"
    extra = destination / "specification-poor/run-2/ageml-evaluation-v3/results.csv"
    extra.parent.mkdir(parents=True)
    extra.write_bytes(source.read_bytes())
    with pytest.raises(ValueError, match="Unlisted result"):
        analysis.load_campaign(destination, "2", allow_incomplete=True)


def test_candidate_counts_are_unknown_without_detailed_evidence(campaign):
    frame, info, _ = analysis.load_campaign(campaign)
    counts, details = analysis.exploration_counts(frame, info)
    assert len(counts) == 54
    assert counts.candidate_records.isna().all()
    assert counts.eligible_candidates.isna().all()
    assert counts.actual_pipelines.eq(30).all()
    assert details.empty


def add_candidate_evidence(campaign, rows):
    frame, info, _ = analysis.load_campaign(campaign)
    first = frame.loc[frame.condition.eq("baseline") & frame.dataset.eq("wilt")].iloc[0]
    path = (
        campaign
        / Path(first.source_csv).parent
        / "protocol"
        / "wilt"
        / first.resume_identity
        / "validation_candidates.csv"
    )
    write_csv(path, rows)
    return path, frame, info


def test_candidate_attempts_are_distinct_from_structures_keys_and_folds(campaign):
    rows = [
        {
            "pipeline_id": 0,
            "run_id": "a",
            "candidate_key": "same",
            "fit_succeeded": True,
            "eligible": True,
            "cv_fold_scores": "[0.8, 0.9]",
        },
        {
            "pipeline_id": 0,
            "run_id": "b",
            "candidate_key": "same",
            "fit_succeeded": False,
            "eligible": False,
            "cv_fold_scores": "",
        },
        {
            "pipeline_id": 1,
            "run_id": "c",
            "candidate_key": "other",
            "fit_succeeded": True,
            "eligible": False,
            "cv_fold_scores": "[0.8, 0.9]",
        },
    ]
    _, frame, info = add_candidate_evidence(campaign, rows)
    counts, details = analysis.exploration_counts(frame, info)
    row = counts.loc[counts.condition.eq("baseline") & counts.dataset.eq("wilt")].iloc[
        0
    ]
    assert row.candidate_records == 3
    assert row.unique_candidates == 2
    assert row.successful_candidate_records == 2
    assert row.eligible_candidates == 1
    assert details.set_index("pipeline_id").loc[0, "candidate_records"] == 2
    assert details.candidate_records.sum() == 3  # Never multiply by CV folds.


def test_empty_candidate_evidence_is_known_zero_not_unknown(campaign):
    path, frame, info = add_candidate_evidence(
        campaign,
        [{"pipeline_id": 0, "run_id": "a", "candidate_key": "x", "eligible": False}],
    )
    path.write_text("pipeline_id,run_id,candidate_key,eligible\n")
    counts, _ = analysis.exploration_counts(frame, info)
    row = counts.loc[counts.condition.eq("baseline") & counts.dataset.eq("wilt")].iloc[
        0
    ]
    assert row.candidate_records == 0
    assert row.eligible_candidates == 0
    assert pd.isna(row.successful_candidate_records)


def test_duplicate_candidate_run_records_are_rejected(campaign):
    _, frame, info = add_candidate_evidence(
        campaign,
        [{"pipeline_id": 0, "run_id": "a", "candidate_key": "x", "eligible": True}] * 2,
    )
    with pytest.raises(ValueError, match="duplicate candidate"):
        analysis.exploration_counts(frame, info)


def test_detailed_candidate_report_exports_local_pipeline_counts(campaign, tmp_path):
    add_candidate_evidence(
        campaign,
        [
            {
                "pipeline_id": 7,
                "run_id": "a",
                "candidate_key": "x",
                "eligible": True,
                "fit_succeeded": True,
            }
        ],
    )
    output = tmp_path / "detailed-report"
    result = analysis.make_report(campaign, output, formats=("png",))
    detail = pd.read_csv(output / "tables/pipeline_instances.csv")
    assert detail.pipeline_id.tolist() == [7]
    assert result["candidate_evidence_sha256"]
    assert not (
        output / "figures/08_instances_per_pipeline_baseline_run-1.png"
    ).exists()


def test_intervals_use_repetition_values_and_small_sample_t():
    interval = analysis.mean_interval([0.8, 0.9])
    # t(.975, 1)=12.7062 and SEM=.05, rather than a normal 1.96 multiplier.
    assert interval["ci95_low"] == pytest.approx(0.85 - 12.7062047364 * 0.05)
    assert interval["ci95_high"] == pytest.approx(0.85 + 12.7062047364 * 0.05)
    bounded = analysis.mean_interval([0.8, 0.9], (0, 1))
    assert bounded["ci95_low"] == pytest.approx(interval["ci95_low"])
    assert bounded["ci95_high"] == 1
    assert bounded["ci95_high_unbounded"] > 1
    assert pd.isna(analysis.mean_interval([0.9])["ci95_low"])
    assert analysis.mean_interval([0.9] * 5)["ci95_low"] == pytest.approx(0.9)


def test_paper_tables_use_current_metadata_and_separate_historical_references(
    campaign, tmp_path
):
    frame, info, _ = analysis.load_campaign(campaign)
    for field, value in [
        ("features", 9),
        ("instances", 20640),
        ("numeric_features", 8),
        ("discrete_features", 1),
    ]:
        frame.loc[frame.dataset.eq("california_housing"), field] = value
    frame.loc[:, "input_tokens"] = 100
    frame.loc[:, "output_tokens"] = 10
    frame.loc[:, "total_tokens"] = 150
    _, scores, _ = analysis.summarize(frame, info)
    out = tmp_path / "tables"
    out.mkdir()
    provenance = analysis._paper_tables(frame, info, scores, out)
    datasets = pd.read_csv(out / "paper_table_1_datasets.csv").set_index("Dataset")
    assert datasets.loc["California Housing", "Features"] == 9
    assert provenance["dataset_metadata_differences"]
    stats = pd.read_csv(out / "paper_results_baseline_statistics.csv")
    assert stats.total_tokens_mean_recorded.eq(150).all()
    assert (
        stats.loc[stats.dataset.eq("wilt"), "historical_reference_score"].iloc[0]
        == 0.975
    )
    assert stats.ci95_low.isna().all()
    assert (out / "paper_table_4_qualitative.tex").exists()


def test_paper_tables_reject_inconsistent_dataset_metadata(campaign, tmp_path):
    frame, info, _ = analysis.load_campaign(campaign)
    frame["features"] = 5
    frame.loc[frame.condition.eq("baseline") & frame.dataset.eq("wilt"), "features"] = 6
    _, scores, _ = analysis.summarize(frame, info)
    with pytest.raises(ValueError, match="Inconsistent dataset metadata"):
        analysis._paper_tables(frame, info, scores, tmp_path)


def test_compact_interval_distinguishes_zero_small_and_unavailable_margins():
    assert analysis.format_mean_interval(0.9, 0.88, 0.92) == "0.900 ± 0.020"
    assert analysis.format_mean_interval(0.9, 0.9, 0.9) == "0.900 ± 0"
    assert analysis.format_mean_interval(0.9, 0.8999, 0.9001) == "0.900 ± <0.001"
    assert (
        analysis.format_mean_interval(0.9, float("nan"), float("nan"))
        == "0.900 (CI N/A)"
    )
    table = pd.DataFrame({"Score": ["0.900 ± 0.020"]})
    assert r"\ensuremath{\pm}" in analysis.latex_table(table)
