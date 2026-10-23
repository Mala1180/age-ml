"""Artifact export for the coordinator's already frozen validation selection.

Selection and one-shot evaluation live in ageml.protocol; the historical
LangGraph test-ranked selector was removed intentionally.
"""

from pathlib import Path

import mlflow

from ageml import logger


def _download_artifacts(run_id: str, out_dir: Path) -> list[str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    downloaded_dir = Path(
        mlflow.artifacts.download_artifacts(run_id=run_id, dst_path=str(out_dir))
    )
    return [
        str(file_path) for file_path in downloaded_dir.rglob("*") if file_path.is_file()
    ]


def download_artifacts(state: dict) -> dict:
    state["artifacts"] = {}
    out_path = Path("out")

    best_run_id = state.get("best_run_id")
    if best_run_id:
        logger.info(f"Downloading artifacts for best run: {best_run_id}")
        state["artifacts"]["best_run"] = _download_artifacts(
            best_run_id,
            out_path / "best_run",
        )

    best_pipeline_id = state.get("best_pipeline_id")
    if best_pipeline_id is not None:
        pipeline_run_id = state["pipeline_run_ids"].get(best_pipeline_id)
        if pipeline_run_id:
            logger.info(
                f"Downloading artifacts for best pipeline run: {pipeline_run_id}"
            )
            state["artifacts"]["best_pipeline"] = _download_artifacts(
                pipeline_run_id,
                out_path / "best_pipeline",
            )

    if not state["artifacts"]:
        logger.info("No best run/pipeline artifacts available to download.")

    return state
