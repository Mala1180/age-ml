"""Branch selection, fair denominators, matched metrics and accessible outputs."""

import csv
import io
import json
import math

import pytest
import yaml

from scripts import competitor_analysis as report
from scripts import competitor_data as data
from scripts import competitor_figures as figures


class SavedSource:
    def __init__(self, files):
        self.files = files

    def read(self, path, optional=False):
        if optional:
            return self.files.get(path)
        return self.files[path]


def csv_bytes(rows):
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode()


@pytest.fixture
def saved():
    datasets = {
        "classification": {"wilt": 40983},
        "regression": {"ames_housing": 42165},
    }
    evidence = {
        name: {
            "source_sha256": str(i) * 64,
            "split_identity": str(i + 2) * 64,
            "manifest": {"cv_folds": [{} for _ in range(10)]},
        }
        for i, name in enumerate(("wilt", "ames_housing"), start=1)
    }
    model = "gemini-test"
    manifest = {
        "campaign_identity": "a" * 64,
        "config": {
            "evaluation_protocol": "hamlet_cv",
            "model": {"name": model, "temperature": 0, "seed": 42},
            "run_seed": 42,
            "time_budget_seconds": 3600,
            "repetitions": [1, 2, 3],
            "datasets": datasets,
        },
        "plan": {"protocol_version": "ageml-evaluation-v3"},
        "source_evidence": evidence,
    }
    raw = json.dumps(manifest).encode()
    cfg = {
        "campaign_id": "mlzero-test",
        "protocol": data.PROTOCOL,
        "llm": {"model": model, "settings": {"seed": 42, "temperature": 0}},
        "mlzero": {"search_seed": 42},
        "budget": {"search_wall_seconds": 3600},
        "age_campaign_identity": manifest["campaign_identity"],
        "age_manifest_sha256": data.digest(raw),
        "repetitions": [1, 2, 3],
        "dataset_entries": [
            {
                "key": name,
                "task": task,
                "openml_id": identifier,
                "input_hashes": {"data.csv": evidence[name]["source_sha256"]},
                "split_identity": evidence[name]["split_identity"],
            }
            for task, entries in datasets.items()
            for name, identifier in entries.items()
        ],
    }
    age_files = {"age/campaign.json": raw}
    for rep in (1, 2, 3):
        rows = []
        for task, entries in datasets.items():
            for name, identifier in entries.items():
                rows.append(
                    {
                        "Dataset": name,
                        "OpenML ID": identifier,
                        "Problem": task,
                        "Protocol Version": "ageml-evaluation-v3",
                        "Evaluation Protocol": "hamlet_cv",
                        "Validation Metric": "balanced_accuracy"
                        if task == "classification"
                        else "rmse",
                        "Split Identity": evidence[name]["split_identity"],
                        "Status": "completed",
                        data.CV_SCORE: 0.8 + 0.02 * (rep - 1)
                        if task == "classification"
                        else 90 + 10 * rep,
                        "Workers": 8,
                    }
                )
        age_files[f"age/baseline/run-{rep}/ageml-evaluation-v3/results.csv"] = (
            csv_bytes(rows)
        )
    ml_rows = []
    for name, rep, status, score in (
        ("wilt", 1, "completed", 0.9),
        ("wilt", 2, "no_artifact", ""),
        ("ames_housing", 1, "completed", 90),
        ("ames_housing", 2, "completed", 88),
    ):
        ml_rows.append(
            {
                "model": model,
                "protocol": data.PROTOCOL,
                "score_role": data.ROLE,
                "test_score": "",
                "final": True,
                "dataset": name,
                "repetition": rep,
                "source_sha256": evidence[name]["source_sha256"],
                "split_identity": evidence[name]["split_identity"],
                "fit_seed": 42,
                "llm_seed_requested": 42,
                "temperature": 0,
                "search_budget_s": 3600,
                "llm_settings_verified": True,
                "status": status,
                "cv_score": score,
                "cv_fold_scores": json.dumps([score] * 10)
                if status == "completed"
                else "",
                "termination_reason": "timeout",
            }
        )
    ml_files = {
        "config.yml": yaml.safe_dump(cfg).encode(),
        "ml/report/mlzero_runs.csv": csv_bytes(ml_rows),
    }
    definition = {
        "age_campaign": "age",
        "mlzero_campaign": "ml",
        "mlzero_config": "config.yml",
        "model": model,
        "label": "Test backend",
    }
    return SavedSource(age_files), SavedSource(ml_files), definition, cfg, ml_rows


def load(saved):
    return data.read_backend(*saved[:2], "test", saved[2], [1, 2, 3])


def test_failures_and_unpublished_runs_stay_distinct_in_denominators(saved):
    frame, _ = load(saved)
    assert len(frame) == 12
    summary = data.summarize(frame)
    row = summary[summary.dataset.eq("wilt") & summary.method.eq("MLZero")].iloc[0]
    assert (
        row.n_valid,
        row.n_failed,
        row.n_not_published,
        row.n_recorded,
        row.n_planned,
    ) == (1, 1, 1, 2, 3)
    assert row["mean"] == 0.9
    assert math.isnan(row.ci95_half_width)


def test_matched_differences_have_correct_units_and_use_common_successes(saved):
    frame, _ = load(saved)
    pairs = data.paired_results(frame)
    wilt = pairs[pairs.dataset.eq("wilt") & pairs.both_valid].iloc[0]
    assert wilt.mlzero_advantage == pytest.approx(10)
    assert wilt.advantage_unit == "percentage_points"
    summary = data.summarize_pairs(pairs)
    ames = summary[summary.dataset.eq("ames_housing")].iloc[0]
    assert ames.n_pairs == 2 and ames.mlzero_wins == 2
    assert ames.age_mean_on_pairs == 105
    assert ames["mean"] == pytest.approx(15)
    # Averages over the paired subset must not silently reuse all AGE successes.
    age = data.summarize(frame)
    assert (
        age[age.dataset.eq("ames_housing") & age.method.eq(data.METHODS[0])].iloc[0][
            "mean"
        ]
        == 110
    )


def test_missing_backend_summary_is_not_45_failures(saved):
    del saved[1].files["ml/report/mlzero_runs.csv"]
    frame, info = load(saved)
    ml = frame[frame.method.eq("MLZero")]
    assert set(ml.status) == {data.MISSING} and not info["mlzero_summary_published"]
    assert data.summarize(ml).n_failed.sum() == 0


@pytest.mark.parametrize(
    "field,value,message",
    [
        ("protocol", "holdout", "protocol"),
        ("age_manifest_sha256", "wrong", "manifest hash"),
        ("age_campaign_identity", "wrong", "different AGE-ML campaign"),
    ],
)
def test_mixed_protocol_or_campaign_is_rejected(saved, field, value, message):
    saved[3][field] = value
    saved[1].files["config.yml"] = yaml.safe_dump(saved[3]).encode()
    with pytest.raises(ValueError, match=message):
        load(saved)


@pytest.mark.parametrize(
    "field,value,message",
    [
        ("score_role", "held_out_test", "test scores cannot be substituted"),
        ("split_identity", "other", "fold mismatch"),
        ("source_sha256", "other", "source mismatch"),
        ("search_budget_s", 1800, "settings mismatch"),
        ("cv_score", 0.95, "disagrees"),
        ("test_score", 0.9, "independent-test"),
    ],
)
def test_inconsistent_mlzero_summary_is_rejected(saved, field, value, message):
    saved[4][0][field] = value
    saved[1].files["ml/report/mlzero_runs.csv"] = csv_bytes(saved[4])
    with pytest.raises(ValueError, match=message):
        load(saved)


def test_duplicate_terminal_outcomes_are_not_selected_by_score(saved):
    saved[4].append(dict(saved[4][0]))
    saved[1].files["ml/report/mlzero_runs.csv"] = csv_bytes(saved[4])
    with pytest.raises(ValueError, match="Duplicate MLZero"):
        load(saved)


def test_singleton_and_shared_seed_intervals_are_not_fabricated():
    one = data.describe([0.8])
    assert math.isnan(one["ci95_half_width"])
    interval = data.describe([0.1, 0.9])
    assert interval["ci95_low"] < 0 and interval["ci95_high"] > 1
    assert data.describe([])["mean"] != data.describe([])["mean"]


def test_zero_rmse_baseline_has_no_fabricated_relative_percentage(saved):
    frame, _ = load(saved)
    same = frame.dataset.eq("ames_housing") & frame.repetition.eq(1)
    frame.loc[same, "score"] = 0
    pairs = data.paired_results(frame)
    zero = pairs[pairs.dataset.eq("ames_housing") & pairs.repetition.eq(1)].iloc[0]
    assert zero.both_valid and math.isnan(zero.mlzero_advantage)


def test_accessible_html_and_tables_preserve_outcomes(saved, tmp_path):
    frame, info = load(saved)
    pairs = data.paired_results(frame)
    report.write_report(
        tmp_path,
        frame,
        data.summarize(frame),
        pairs,
        data.summarize_pairs(pairs),
        {"test": info},
        {"test": "fixture"},
        ["svg"],
    )
    page = (tmp_path / "index.html").read_text()
    assert 'lang="en"' in page and 'scope="col"' in page and 'alt="' in page
    assert "Final failures" in page and "Not published" in page
    assert "specification-compliance filtering" in page
    assert len(list((tmp_path / "figures/test").glob("*.svg"))) == 4
    assert "95%" in (tmp_path / "tables/test_metrics.md").read_text()
    assert "\\pm" in (tmp_path / "tables/test_metrics.tex").read_text()
    metadata = json.loads((tmp_path / "sources.json").read_text())
    assert metadata["campaigns"]["test"]["source_data_and_folds_match"]
    assert all(
        value >= 4.5
        for value in figures.accessibility_notes()[
            "color_contrast_against_white"
        ].values()
    )


def test_git_reader_uses_named_branch_and_keeps_checkout_and_offline_pin(tmp_path):
    repository = tmp_path / "source"
    repository.mkdir()
    data.git(repository, "init", "-b", "main", "--quiet")
    data.git(repository, "config", "user.name", "Test")
    data.git(repository, "config", "user.email", "test@example.invalid")
    summary = repository / "summary.csv"
    summary.write_text("wrong branch")
    data.git(repository, "add", "summary.csv")
    data.git(repository, "commit", "-qm", "main")
    data.git(repository, "checkout", "-qb", "results/mlzero-gemini")
    summary.write_text("correct results")
    data.git(repository, "commit", "-qam", "results")
    data.git(repository, "checkout", "-q", "main")
    summary.write_text("uncommitted work must remain untouched")
    cache = tmp_path / "cache"
    source = data.GitSource(repository, "results/mlzero-gemini", cache)
    assert source.read("summary.csv") == b"correct results"
    assert data.git(repository, "branch", "--show-current").strip() == b"main"
    assert summary.read_text() == "uncommitted work must remain untouched"
    offline = data.GitSource(repository, "results/mlzero-gemini", cache, offline=True)
    assert (
        offline.commit == source.commit
        and offline.read("summary.csv") == b"correct results"
    )
    assert offline.read("absent.csv", optional=True) is None
    assert source.provenance()["file_sha256"]["summary.csv"] == data.digest(
        b"correct results"
    )


def test_offline_first_use_fails_clearly(tmp_path):
    with pytest.raises(ValueError, match="run once online"):
        data.GitSource(
            "https://example.invalid/repo.git",
            "results/branch",
            tmp_path / "cache",
            offline=True,
        )


def test_audit_table_is_cross_checked_and_diagnostics_are_retained(saved):
    frame, _ = load(saved)
    rows = []
    for original in saved[4]:
        age = frame[
            (frame.method == data.METHODS[0])
            & (frame.dataset == original["dataset"])
            & (frame.repetition == original["repetition"])
        ].iloc[0]
        rows.append(
            {
                **{
                    key: original[key]
                    for key in (
                        "dataset",
                        "repetition",
                        "status",
                        "cv_score",
                        "source_sha256",
                        "split_identity",
                    )
                },
                "age_cv_score": age.score,
                "generated_nodes": 7,
                "cv_exports": 2,
            }
        )
    saved[2]["mlzero_audit"] = "audit"
    saved[1].files["audit/run_audit.csv"] = csv_bytes(rows)
    saved[1].files["audit/run_diagnostics.csv"] = csv_bytes(
        [
            {
                "dataset": "wilt",
                "repetition": 2,
                "status": "no_artifact",
                "terminal_phase": "Timeout with evaluation unfinished",
            },
        ]
    )
    frame, info = load(saved)
    assert info["audited_rows_cross_checked"] == 4
    failed = frame[(frame.method == "MLZero") & (frame.status == "no_artifact")].iloc[0]
    assert (
        failed.terminal_phase == "Timeout with evaluation unfinished"
        and failed.generated_nodes == 7
    )
    rows[0]["age_cv_score"] = 0.99
    saved[1].files["audit/run_audit.csv"] = csv_bytes(rows)
    with pytest.raises(ValueError, match="Audit score disagrees"):
        load(saved)


@pytest.mark.parametrize("value", ["1,1", "0", "6", "1;echo bad"])
def test_invalid_repetitions_are_rejected(value):
    with pytest.raises(ValueError):
        data.parse_repetitions(value)
