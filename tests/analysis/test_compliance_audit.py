"""Regression checks for audit identity, task errors and conservative unknowns."""

import pandas as pd
import pytest

from scripts._compliance_checks import audit_candidates
from scripts._compliance_static import Factory, Unsupported
from scripts.campaign_analysis import attach_audit
from scripts.compliance_audit import summarize_audit


def candidate(code_hash="h"):
    return {
        "condition": "baseline",
        "dataset": "toy",
        "repetition": 1,
        "run_identity": "identity",
        "pipeline_id": "0",
        "code_sha256": code_hash,
        "run_id": "run",
        "candidate_key": "key",
        "parameters": {"max_iter": 300},
        "problem": "classification",
        "numeric_features": 2,
        "discrete_features": 0,
        "matching_code_members": ["code.py"],
        "eligible": "True",
        "fit_succeeded": "True",
        "validation_score": ".9",
        "requested_steps": [
            {
                "name": "classification",
                "candidate": "nn",
                "hyperparameters": {"max_iter": [300]},
            }
        ],
    }


def test_constant_override_is_violation_and_winner_requires_exact_identity():
    c = candidate()
    rows, findings, _ = audit_candidates(
        [c],
        {
            "h": "from sklearn.neural_network import MLPClassifier\ndef build_model(X_train,y_train,max_iter):\n return MLPClassifier(max_iter=1000)"
        },
    )
    assert findings[0]["type"] == "hyperparameter_mismatch"
    frame, _, _ = summarize_audit(
        rows,
        findings,
        {
            "identity": {
                "run_id": "run",
                "candidate_key": "another-key",
                "code_sha256": "h",
            }
        },
    )
    assert frame.audit_outcome.iloc[0] == "confirmed_violation"
    assert not frame.winner.iloc[0]


def test_invalid_syntax_is_unknown_not_semantic_violation():
    rows, findings, _ = audit_candidates([candidate()], {"h": "```python\n"})
    frame, _, _ = summarize_audit(rows, findings, {})
    assert frame.audit_status.iloc[0] == "invalid_source"
    assert frame.audit_outcome.iloc[0] == "undetermined"
    assert not findings


def test_task_incompatible_requested_estimator_is_separate_finding():
    c = candidate()
    c["problem"] = "regression"
    _, findings, _ = audit_candidates(
        [c],
        {
            "h": "from sklearn.neural_network import MLPClassifier\ndef build_model(X_train,y_train,max_iter):\n return MLPClassifier(max_iter=max_iter)"
        },
    )
    assert [f["type"] for f in findings] == ["wrong_task_recipe"]


def test_training_row_count_is_never_invented():
    code = "from sklearn.linear_model import Ridge\ndef build_model(X_train,y_train):\n if X_train.shape[0]>1000:\n  return Ridge(alpha=1)\n return Ridge(alpha=10)"
    with pytest.raises(Unsupported, match="comparison"):
        Factory(code, 2, 0, {}).run()


def test_audit_join_rejects_wrong_campaign_score_and_duplicates(tmp_path):
    frame = pd.DataFrame(
        [
            {
                "condition": "baseline",
                "repetition": 1,
                "dataset": "toy",
                "run_identity": "id",
                "score": 0.9,
                "status": "completed",
            }
        ]
    )
    info = {"frozen": {"campaign_identity": "campaign"}}
    table = pd.DataFrame(
        [
            {
                "condition": "baseline",
                "repetition": 1,
                "dataset": "toy",
                "run_identity": "id",
                "score": 0.9,
                "campaign_identity": "campaign",
                "audit_outcome": "confirmed_violation",
            }
        ]
    )
    p = tmp_path / "audit.csv"
    table.to_csv(p, index=False)
    assert attach_audit(frame, info, p).audit_outcome.iloc[0] == "confirmed_violation"
    table["score"] = 0.8
    table.to_csv(p, index=False)
    with pytest.raises(ValueError, match="scores"):
        attach_audit(frame, info, p)
    table["campaign_identity"] = "other"
    table.to_csv(p, index=False)
    with pytest.raises(ValueError, match="another campaign"):
        attach_audit(frame, info, p)
    table["campaign_identity"] = "campaign"
    pd.concat([table, table]).to_csv(p, index=False)
    with pytest.raises(ValueError, match="Duplicate"):
        attach_audit(frame, info, p)


def test_additional_source_in_zero_candidate_run_uses_campaign_labels(tmp_path):
    import json
    import zipfile

    from scripts.compliance_audit import extra_sources

    source = tmp_path / "evidence.zip"
    with zipfile.ZipFile(source, "w") as z:
        z.writestr("campaign/no-csp/run-5/v3/results.csv", "Run Identity\nfailed-run\n")
        z.writestr(
            "mlflow_runs/root/run.json",
            json.dumps(
                {
                    "name": "pipeline_0_nn",
                    "dataset_runs": [
                        {
                            "run_identity": "failed-run",
                            "condition": "no-csp",
                            "dataset": "toy",
                            "repetition": 5,
                        }
                    ],
                    "parameters": {},
                }
            ),
        )
        z.writestr(
            "mlflow_runs/root/artifacts/code.py",
            "def build_model(X_train,y_train):\n return None\n",
        )
    with zipfile.ZipFile(source) as z:
        extras, _, _, _ = extra_sources(
            z,
            [],
            {},
            {},
            {},
            {
                "failed-run": {
                    "Dataset": "toy",
                    "Problem": "classification",
                    "Numeric Features": "2",
                    "Discrete Features": "0",
                }
            },
            {},
            {},
        )
    assert extras.iloc[0].condition == "no-csp"
    assert extras.iloc[0].repetition == 5
    assert extras.iloc[0].audit_status == "unresolved"


@pytest.mark.parametrize("union_count", [2, 6])
def test_violation_plot_rejects_impossible_union_counts(tmp_path, union_count):
    from scripts.compliance_audit import audit_plots

    summary = pd.DataFrame(
        [
            {
                "population": "implementation_versions",
                "auditable": 10,
                "any_structural_violation_count": 3,
                "any_parameter_violation_count": 2,
                "any_violation_count": union_count,
            }
        ]
    )
    perrun = pd.DataFrame(
        columns=["structural_violations", "parameter_violations", "either_violations"]
    )
    with pytest.raises(ValueError, match="union counts"):
        audit_plots(summary, perrun, pd.DataFrame(), tmp_path / "figures")
