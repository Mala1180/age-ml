"""Owned download workspaces and conservative, post-selection model retention."""

import csv
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname

import mlflow
import yaml

from ageml.protocol import file_hash

WORKSPACE_ENV = "AGEML_ARTIFACT_WORKSPACE"


@contextmanager
def artifact_workspace():
    """The coordinator also cleans downloads left by terminated pool workers."""
    previous = os.environ.get(WORKSPACE_ENV)
    previous_tmpdir = os.environ.get("TMPDIR")
    previous_tempdir = tempfile.tempdir
    with tempfile.TemporaryDirectory(prefix="ageml-artifacts-") as workspace:
        os.environ[WORKSPACE_ENV] = workspace
        # Cover MLflow's own staging/inference files as well as our downloads.
        # Spawned workers inherit TMPDIR; the coordinator may already have a
        # cached tempfile directory, so update and later restore that cache too.
        os.environ["TMPDIR"] = workspace
        tempfile.tempdir = workspace
        try:
            yield Path(workspace)
        finally:
            tempfile.tempdir = previous_tempdir
            if previous_tmpdir is None:
                os.environ.pop("TMPDIR", None)
            else:
                os.environ["TMPDIR"] = previous_tmpdir
            if previous is None:
                os.environ.pop(WORKSPACE_ENV, None)
            else:
                os.environ[WORKSPACE_ENV] = previous


@contextmanager
def downloaded_artifact(run_id, artifact_path):
    with tempfile.TemporaryDirectory(
        prefix="download-", dir=os.environ.get(WORKSPACE_ENV)
    ) as destination:
        yield Path(
            mlflow.artifacts.download_artifacts(
                run_id=run_id, artifact_path=artifact_path, dst_path=destination
            )
        )


def _local_path(uri):
    if Path(uri).is_absolute():
        return Path(uri).resolve()
    parsed = urlparse(uri)
    if parsed.scheme != "file" or parsed.netloc not in ("", "localhost"):
        return None
    return Path(url2pathname(parsed.path)).resolve()


def _logged_models(client, run_id):
    # Run IDs are interpolated into MLflow's filter language.
    if len(run_id) != 32 or any(c not in "0123456789abcdef" for c in run_id):
        raise ValueError("Invalid candidate run ID")
    experiment_id = client.get_run(run_id).info.experiment_id
    root = _local_path(client.get_experiment(experiment_id).artifact_location)
    if root is None:
        raise ValueError("Best-only model retention requires a local artifact store")
    token = None
    while True:
        page = client.search_logged_models(
            experiment_ids=[experiment_id],
            filter_string=f"source_run_id = '{run_id}'",
            max_results=1000,
            page_token=token,
        )
        for model in page:
            if model.source_run_id != run_id:
                raise ValueError("Logged model provenance mismatch")
            directory = _local_path(model.artifact_location)
            if directory is None or not directory.is_relative_to(root):
                raise ValueError(
                    "Logged model is outside its experiment artifact store"
                )
            metadata_path = directory / "MLmodel"
            if not metadata_path.is_file():
                continue
            metadata = yaml.safe_load(metadata_path.read_text(encoding="utf-8"))
            if metadata.get("run_id") != run_id:
                raise ValueError("Model metadata run ID mismatch")
            files = sorted(directory.rglob("*.pkl"))
            if len(files) == 1 and not files[0].is_symlink():
                if not files[0].resolve().is_relative_to(root):
                    raise ValueError("Model binary is outside its artifact store")
                yield model.model_id, files[0]
        token = getattr(page, "token", None)
        if not token:
            break


def _save_report(path, report):
    """Persist the deletion plan before unlinking any model binary."""
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as stream:
            temporary = Path(stream.name)
            json.dump(report, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def prune_nonwinning_models(protocol_dir, client=None):
    """Keep scores/code/provenance and the winner; remove verified loser pickles.

    The suite must call this only after its summary CSV and artifact export
    have been saved. Unfinished datasets and remote stores are never pruned.
    """
    output = Path(protocol_dir)
    result = json.loads((output / "result.json").read_text())
    if result.get("status") not in (
        "completed",
        "no_valid_candidate",
        "test_evaluation_failed",
    ):
        return {"removed_bytes": 0, "removed_models": 0}
    selection_path = output / "selection.json"
    selection = json.loads(selection_path.read_text())
    protocol_path = output / "protocol.json"
    if (
        result["selection_sha256"] != file_hash(selection_path)
        or selection["protocol_sha256"] != file_hash(protocol_path)
        or result["protocol_sha256"] != file_hash(protocol_path)
    ):
        raise ValueError("Frozen selection/protocol checksum mismatch")
    winner = selection.get("selected")
    winner_id = None if winner is None else winner["run_id"]
    if result["best_run_id"] != winner_id:
        raise ValueError("Winner identity mismatch")
    client = client or mlflow.MlflowClient()
    # Require the persistent winner to exist and match before deleting losers.
    if winner is not None and not any(
        file_hash(path) == winner["model_sha256"]
        for _, path in _logged_models(client, winner["run_id"])
    ):
        raise ValueError("Persistent winning model is missing or changed")
    with (output / "validation_candidates.csv").open(newline="") as stream:
        candidates = list(csv.DictReader(stream))
    report_path = output / "storage_cleanup.json"
    report = (
        json.loads(report_path.read_text())
        if report_path.exists()
        else {"policy": "best", "kept_run_id": winner_id, "events": []}
    )
    if report["kept_run_id"] != winner_id:
        raise ValueError("Retention report winner mismatch")
    _save_report(report_path, report)
    removed_bytes = removed_models = 0
    seen = set()
    for candidate in candidates:
        run_id = candidate.get("run_id")
        expected_hash = candidate.get("model_sha256")
        if not run_id or run_id == winner_id or not expected_hash:
            continue
        for model_id, path in _logged_models(client, run_id):
            if str(path) in seen:
                continue
            seen.add(str(path))
            if file_hash(path) != expected_hash:
                continue  # Never delete an unverified or unrelated binary.
            size = path.stat().st_size
            event = {
                "run_id": run_id,
                "model_id": model_id,
                "path": str(path),
                "sha256": expected_hash,
                "bytes": size,
                "state": "planned",
            }
            report["events"].append(event)
            _save_report(report_path, report)
            path.unlink()
            event["state"] = "removed"
            _save_report(report_path, report)
            removed_bytes += size
            removed_models += 1
            client.set_tag(run_id, "model_retention", "binary_removed_after_selection")
    return {"removed_bytes": removed_bytes, "removed_models": removed_models}
