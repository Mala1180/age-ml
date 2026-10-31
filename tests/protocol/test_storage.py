"""Download lifetimes, streaming hashes and verified loser-only retention."""

import csv
import hashlib
import json
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from ageml.protocol import file_hash, write_json
from ageml.storage import (
    WORKSPACE_ENV,
    artifact_workspace,
    downloaded_artifact,
    prune_nonwinning_models,
)


@pytest.mark.parametrize("fail", [False, True])
def test_downloads_are_removed_on_success_and_failure(tmp_path, monkeypatch, fail):
    import mlflow

    destinations = []

    def download(**kwargs):
        destination = Path(kwargs["dst_path"])
        destinations.append(destination)
        model = destination / "model"
        model.mkdir()
        (model / "model.pkl").write_bytes(b"model")
        return str(model)

    monkeypatch.setattr(mlflow.artifacts, "download_artifacts", download)
    monkeypatch.setenv(WORKSPACE_ENV, str(tmp_path))
    try:
        with downloaded_artifact("run", "model") as model:
            assert model.is_dir()
            assert model.parent.parent == tmp_path
            if fail:
                raise ValueError("consumer failed")
    except ValueError:
        assert fail
    assert not destinations[0].exists()


def test_workspace_cleans_worker_leftovers_and_restores_environment(monkeypatch):
    monkeypatch.setenv(WORKSPACE_ENV, "previous-workspace")
    previous_tempdir = tempfile.tempdir
    previous_tmpdir = os.environ.get("TMPDIR")
    with pytest.raises(RuntimeError), artifact_workspace() as workspace:
        assert Path(os.environ[WORKSPACE_ENV]) == workspace
        assert Path(tempfile.gettempdir()) == workspace
        assert Path(os.environ["TMPDIR"]) == workspace
        # A SIGTERM worker may not run its own TemporaryDirectory finalizer.
        orphan = Path(tempfile.mkdtemp())
        assert orphan.parent == workspace
        (orphan / "model.pkl").write_bytes(b"orphan")
        raise RuntimeError("coordinator failed")
    assert not workspace.exists()
    assert os.environ[WORKSPACE_ENV] == "previous-workspace"
    assert tempfile.tempdir == previous_tempdir
    assert os.environ.get("TMPDIR") == previous_tmpdir


def test_hashing_large_models_does_not_read_entire_file(tmp_path, monkeypatch):
    path = tmp_path / "model.pkl"
    content = b"model" * 500_000
    path.write_bytes(content)

    def forbidden(*args, **kwargs):
        raise AssertionError("whole-file read would cause a RAM spike")

    monkeypatch.setattr(Path, "read_bytes", forbidden)
    assert file_hash(path) == hashlib.sha256(content).hexdigest()


@pytest.fixture
def retention_case(tmp_path):
    output = tmp_path / "protocol"
    output.mkdir()
    root = tmp_path / "mlruns" / "1"
    winner, loser = "a" * 32, "b" * 32
    models = {}
    hashes = {}
    for run_id in (winner, loser):
        directory = root / "models" / run_id / "artifacts"
        directory.mkdir(parents=True)
        (directory / "MLmodel").write_text(yaml.safe_dump({"run_id": run_id}))
        binary = directory / "model.pkl"
        binary.write_bytes(run_id.encode())
        hashes[run_id] = file_hash(binary)
        models[run_id] = SimpleNamespace(
            model_id="m-" + run_id,
            source_run_id=run_id,
            artifact_location=directory.as_uri(),
        )
    write_json(output / "protocol.json", {"run_identity": "dataset"})
    protocol_hash = file_hash(output / "protocol.json")
    write_json(
        output / "selection.json",
        {
            "protocol_sha256": protocol_hash,
            "selected": {"run_id": winner, "model_sha256": hashes[winner]},
        },
    )
    write_json(
        output / "result.json",
        {
            "status": "completed",
            "best_run_id": winner,
            "protocol_sha256": protocol_hash,
            "selection_sha256": file_hash(output / "selection.json"),
        },
    )
    with (output / "validation_candidates.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["run_id", "model_sha256"])
        writer.writeheader()
        for run_id in (winner, loser):
            writer.writerow({"run_id": run_id, "model_sha256": hashes[run_id]})

    class Client:
        def __init__(self):
            self.tags = []

        def get_run(self, run_id):
            return SimpleNamespace(info=SimpleNamespace(experiment_id="1"))

        def get_experiment(self, experiment_id):
            return SimpleNamespace(artifact_location=root.as_uri())

        def search_logged_models(self, **kwargs):
            run_id = kwargs["filter_string"].split("'")[1]
            return [models[run_id]]

        def set_tag(self, *args):
            self.tags.append(args)

    return output, root, winner, loser, models, Client()


def test_retention_preserves_winner_and_metadata_and_is_idempotent(retention_case):
    output, root, winner, loser, _, client = retention_case
    metadata_before = (output / "validation_candidates.csv").read_bytes()
    result = prune_nonwinning_models(output, client)
    assert result == {"removed_models": 1, "removed_bytes": 32}
    assert (root / "models" / winner / "artifacts/model.pkl").exists()
    assert not (root / "models" / loser / "artifacts/model.pkl").exists()
    assert (root / "models" / loser / "artifacts/MLmodel").exists()
    assert (output / "validation_candidates.csv").read_bytes() == metadata_before
    audit = json.loads((output / "storage_cleanup.json").read_text())
    assert audit["events"][0]["state"] == "removed"
    assert prune_nonwinning_models(output, client)["removed_models"] == 0
    assert client.tags == [(loser, "model_retention", "binary_removed_after_selection")]


@pytest.mark.parametrize("corruption", ["winner", "selection", "outside"])
def test_unsafe_retention_never_deletes_loser(retention_case, tmp_path, corruption):
    output, root, winner, loser, models, client = retention_case
    if corruption == "winner":
        (root / "models" / winner / "artifacts/model.pkl").write_bytes(b"changed")
    elif corruption == "selection":
        (output / "selection.json").write_text("{}")
    else:
        models[loser].artifact_location = tmp_path.as_uri()
    with pytest.raises(ValueError):
        prune_nonwinning_models(output, client)
    assert (root / "models" / loser / "artifacts/model.pkl").exists()


def test_incomplete_dataset_is_not_pruned(retention_case):
    output, root, _, loser, _, client = retention_case
    write_json(output / "result.json", {"status": "running"})
    assert prune_nonwinning_models(output, client)["removed_models"] == 0
    assert (root / "models" / loser / "artifacts/model.pkl").exists()


def test_cv_verification_does_not_keep_all_models_in_ram(tmp_path):
    import weakref

    import numpy as np
    import pandas as pd

    from ageml.protocol import select_and_evaluate

    protocol = {
        "run_identity": "dataset",
        "split_identity": "split",
        "split_hashes": {"validation": "validation"},
        "metric": "balanced_accuracy",
        "maximize": True,
        "evaluation_protocol": "hamlet_cv",
        "task": "classification",
    }
    write_json(tmp_path / "protocol.json", protocol)
    candidates = [
        {
            "run_identity": "dataset",
            "validation_split_hash": "validation",
            "metric": "balanced_accuracy",
            "maximize": True,
            "fit_succeeded": True,
            "model_sha256": "verified-model-hash",
            "validation_score": 1.0,
            "cv_fold_scores": [1.0] * 10,
            "run_id": str(i),
            "candidate_key": str(i),
            "pipeline_id": i,
            "code_sha256": "verified-code-hash",
        }
        for i in range(3)
    ]
    references = []

    class Model:
        def predict(self, X):
            return np.zeros(len(X))

    def load(candidate):
        assert all(reference() is None for reference in references)
        model = Model()
        references.append(weakref.ref(model))
        return model

    result = select_and_evaluate(
        candidates,
        protocol,
        tmp_path,
        load,
        pd.DataFrame({"x": [1, 2, 3]}),
        lambda: pytest.fail("CV must not read a held-out test set"),
        lambda y, predictions: 1.0,
    )
    assert result["status"] == "completed"
    assert all(reference() is None for reference in references)


def test_terminal_dataset_without_winner_prunes_only_verified_binaries(retention_case):
    output, root, winner, loser, _, client = retention_case
    selection_path = output / "selection.json"
    selection = json.loads(selection_path.read_text())
    selection["selected"] = None
    write_json(selection_path, selection)
    result_path = output / "result.json"
    result = json.loads(result_path.read_text())
    result.update(
        status="no_valid_candidate",
        best_run_id=None,
        selection_sha256=file_hash(selection_path),
    )
    write_json(result_path, result)
    assert prune_nonwinning_models(output, client)["removed_models"] == 2
    assert not (root / "models" / winner / "artifacts/model.pkl").exists()
    assert not (root / "models" / loser / "artifacts/model.pkl").exists()
    assert (root / "models" / winner / "artifacts/MLmodel").exists()
