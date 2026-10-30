import csv
import json
import multiprocessing
import shutil
import subprocess
import time
import uuid
from collections.abc import Callable
from copy import deepcopy
from datetime import datetime, timedelta
from multiprocessing import get_context
from pathlib import Path
from typing import Any

import fire
import mlflow
from mlflow.entities import Experiment

from ageml import logger
from ageml.common import DEFAULT_MODEL_NAME
from ageml.common.client import (
    enable_mlflow_llm_autologging,
    get_nested_runs_total_duration,
    get_nested_runs_total_llm_latency,
    get_session_total_token_usage,
)
from ageml.common.llm_config import resolve_llm_config
from ageml.execution.utils import get_metric
from ageml.fitting import seed_process
from ageml.protocol import (
    VERSION,
    digest,
    environment_identity,
    file_hash,
    prepare,
    select_and_evaluate,
    write_json,
)
from ageml.specification import Specification

# Agent modules are imported after the run configuration is exported. Their
# structured client wrappers resolve the current backend lazily at invocation.


# MLflow/HTTP clients start threads before exploration. Forking that process
# can inherit locked state; spawn starts each worker with fresh clients.
Pool = get_context("spawn").Pool


def main(
    spec_path: str,
    dataset_path: str,
    model_name: str = DEFAULT_MODEL_NAME,
    validation_metric: str | None = None,
    maximize: bool | None = None,
    retry_on_semantic_failure: bool = True,
    retry_on_execution_failure: bool = True,
    use_csp: bool = True,
    target_column: str | None = None,
    task: str | None = None,
    split_seed: int | None = None,
    split_manifest: str | None = None,
    protocol_output_dir: str | None = None,
    model_provider: str = "gemini",
    model_base_url: str | None = None,
    model_api_key_env: str | None = None,
    evaluation_protocol: str | None = None,
    run_seed: int = 42,
    model_seed: int | None = None,
    model_temperature: float | None = None,
    time_budget_seconds: int | None = None,
) -> dict:
    """Run planning and execution from the command line.

    The command can be invoked as:

    ``python -m ageml --spec_path=<path> --dataset_path=<path>
    --target_column=<column> --task=classification``

    Runtime budgets are read from ``budgets`` in the specification YAML:
    ``budgets.pipelines``, ``budgets.time`` (hours/minutes/seconds), ``budgets.workers``,
    and ``budgets.generation_attempts``.

    Args:
        spec_path: Filesystem path to the YAML specification file.
        dataset_path: Filesystem path to the input dataset used for the AutoML task.
        model_name: Name of the LLM backend used for planning/execution/evaluation
            (e.g. "gemini-2.5-flash"). Exposed on the command line as ``--model_name``
            (e.g. ``--model_name=gemini-2.5-flash`` or ``--model_name gemini-2.5-flash``).
            Defaults to ``DEFAULT_MODEL_NAME`` above when not provided.
        target_column: Explicit prediction target, validated before any LLM work.
        task: Explicit classification or regression task.
        split_seed: Holdout split seed (42 unless imported); unused by unshuffled CV.
        evaluation_protocol: holdout (default) or hamlet_cv (ten-fold selection CV).
        run_seed: Python/NumPy, planner sampling and all exposed estimator random_state.
        model_seed: Optional seed requested from the LLM backend.
        model_temperature: Optional LLM temperature.
        time_budget_seconds: Optional exploration deadline overriding the specification.
        split_manifest: Existing protocol whose frozen row lists are authoritative.
        protocol_output_dir: Fresh coordinator-owned provenance directory.
        validation_metric: Balanced accuracy for classification, RMSE for regression.
        maximize: Whether to maximize the metric (True) or minimize it (False). Default: True.
        retry_on_semantic_failure: Whether a "code not compliant with the pipeline"
            verdict from the LLM judge triggers regenerating the code (default: True).
            The judge always runs either way; when False, its verdict is only
            recorded (see ``semantic_validation_failures``/``semantic_validation_failure_reasons``
            in the returned dict) and the generated code is executed regardless.
        retry_on_execution_failure: Whether a code execution failure triggers
            regenerating the code (default: True). When False, a pipeline whose
            code fails to execute is marked failed immediately instead of retrying.
        use_csp: Whether the pipelines are planned by the constraint solver (default: True).
            When False, the LLM is given the specification and
            proposes a single pipeline directly.
    Returns:
        A dictionary containing the results of the experiment.
    """
    # Validate and freeze rows before importing any model-bound modules.
    df, protocol = prepare(
        dataset_path,
        target_column,
        task,
        split_seed,
        split_manifest,
        evaluation_protocol,
    )
    seed_process(run_seed)
    if time_budget_seconds is not None and (
        type(time_budget_seconds) is not int or time_budget_seconds <= 0
    ):
        raise ValueError("time_budget_seconds must be a positive integer")
    llm_config = resolve_llm_config(
        model_name,
        model_provider,
        model_base_url,
        model_api_key_env,
        model_seed,
        model_temperature,
    )
    expected_metric = "balanced_accuracy" if task == "classification" else "rmse"
    validation_metric = (
        expected_metric if validation_metric is None else validation_metric
    )
    maximize = (task == "classification") if maximize is None else maximize
    if validation_metric != expected_metric or maximize != (task == "classification"):
        raise ValueError(
            "v2 requires balanced_accuracy/maximize or rmse/minimize for the configured task"
        )
    if split_manifest and (
        protocol.get("metric", validation_metric) != validation_metric
        or protocol.get("maximize", maximize) != maximize
    ):
        raise ValueError("Imported manifest metric/direction conflict")
    target_feature = target_column
    train_df = df.iloc[protocol["partitions"]["train"]].reset_index(drop=True)
    validation_df = df.iloc[
        []
        if protocol["evaluation_protocol"] == "hamlet_cv"
        else protocol["partitions"]["validation"]
    ].reset_index(drop=True)
    output = Path(protocol_output_dir or f"out/{VERSION}/{uuid.uuid4().hex}")
    if (output / "protocol.json").exists():
        raise FileExistsError("Use a new protocol_output_dir for each run")
    specification = Specification.parse(Path(spec_path).read_text())
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=Path(__file__).parent, text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        commit = "unknown"
    protocol.update(
        metric=validation_metric,
        maximize=maximize,
        fitting_policy="fresh fit per CV fold; last-fold artifact; no final refit"
        if protocol["evaluation_protocol"] == "hamlet_cv"
        else "training partition only; no final refit",
        age_ml_commit=commit,
        age_ml_source_sha256=digest(
            {
                str(p.relative_to(Path(__file__).parent)): file_hash(p)
                for p in sorted(Path(__file__).parent.rglob("*.py"))
            }
        ),
        effective_llm_configuration=llm_config.public_dict(),
        environment=environment_identity(),
        specification_sha256=file_hash(spec_path),
        budgets=specification.budgets.model_dump(mode="json"),
        exploration_budget_seconds=time_budget_seconds
        if time_budget_seconds is not None
        else specification.budgets.time.total_seconds,
        search_configuration={
            "use_csp": use_csp,
            "effective_structure_budget": specification.budgets.pipelines
            if use_csp
            else 1,
            "retry_on_semantic_failure": retry_on_semantic_failure,
            "retry_on_execution_failure": retry_on_execution_failure,
            "fit_seed": run_seed,
            "planner_seed": run_seed,
            "time_budget_seconds": time_budget_seconds
            or specification.budgets.time.total_seconds,
            "refit": False,
        },
        access_boundary={
            "filesystem_isolation": False,
            "limitation": "Local multiprocessing shares filesystem permissions; generated code is trusted. API data separation is not isolation.",
        },
        prediction_encoding="one scalar per source-ordered row; classification uses original training labels",
    )
    protocol["run_identity"] = digest(
        {
            "split": protocol["split_identity"],
            "metric": validation_metric,
            "maximize": maximize,
            "specification": protocol["specification_sha256"],
            "model": llm_config.public_dict(),
            "code": protocol["age_ml_source_sha256"],
            "repetition": str(output.resolve()),
            "use_csp": use_csp,
            "run_seed": run_seed,
            "time_budget_seconds": time_budget_seconds,
            "retry_on_semantic_failure": retry_on_semantic_failure,
            "retry_on_execution_failure": retry_on_execution_failure,
        }
    )
    write_json(output / "protocol.json", protocol, exclusive=True)
    llm_config.export()

    # Workers inherit this configuration; lazy model wrappers also support reused processes.
    from ageml.execution.agent import ExecutionPipeline, PipelineStatus
    from ageml.planning.types import PlanningPipeline

    plan: Callable[[dict[str, Any]], dict[str, Any]]
    if use_csp:
        from ageml.planning.agent import planning_agent

        plan = planning_agent.invoke
    else:
        from ageml.planning.plain_llm import plan as plan_with_llm

        plan = plan_with_llm

    enable_mlflow_llm_autologging()

    start_time = time.perf_counter()
    timeout = (
        specification.budgets.time.total_seconds
        if time_budget_seconds is None
        else time_budget_seconds
    )
    if type(timeout) is not int or timeout <= 0:
        raise ValueError("time_budget_seconds must be a positive integer")
    deadline = time.time() + timeout

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    run_name: str = f"pipelines_exploration-{timestamp}"
    session: str = run_name
    with mlflow.context(
        tags={"session": session},
        metadata={"mlflow.trace.session": session},
    ):
        planning = plan(
            {
                "specification_path": spec_path,
                "train_df": train_df,
                "run_seed": run_seed,
                "target_feature": target_feature,
            }
        )
        planned_pipelines: list[PlanningPipeline] = planning["pipelines"]

        experiment_name: str = Path(dataset_path).stem
        mlflow.set_experiment(experiment_name)
        experiment: Experiment | None = mlflow.get_experiment_by_name(experiment_name)
        assert experiment is not None, "Experiment should exist after setting it"
        experiment_id = experiment.experiment_id

        with mlflow.start_run(run_name=run_name) as run:
            inputs: list[dict[str, Any]] = []
            for i, planned_pipeline in enumerate(planned_pipelines):
                execution_pipeline: ExecutionPipeline = ExecutionPipeline(
                    id=i, steps=planned_pipeline.steps
                )
                inputs.append(
                    {
                        "specification_path": spec_path,
                        "validation_df": validation_df,
                        "cv_folds": protocol.get("cv_folds"),
                        "run_seed": run_seed,
                        "exploration_deadline": deadline,
                        "candidate_output_dir": str(
                            (output / "candidate_journal").resolve()
                        ),
                        "task": task,
                        "run_identity": protocol["run_identity"],
                        "source_sha256": protocol["source_sha256"],
                        "validation_split_hash": protocol["split_hashes"]["validation"],
                        "train_df": train_df,
                        "target_feature": target_feature,
                        "pipeline": execution_pipeline,
                        "root_run_id": run.info.run_id,
                        "experiment_id": experiment_id,
                        "validation_metric": validation_metric,
                        "maximize": maximize,
                        "retry_on_semantic_failure": retry_on_semantic_failure,
                        "retry_on_execution_failure": retry_on_execution_failure,
                    }
                )

            results: list = deepcopy(inputs)

            # Run-scoped protocol output must survive exploration.

            failed: int = 0
            timed_out: int = 0
            with Pool(processes=specification.budgets.workers) as pool:
                jobs = [pool.apply_async(invoke_agent, (i, session)) for i in inputs]

                for i, job in enumerate(jobs):
                    remaining = deadline - time.time()
                    remaining = max(0, remaining)

                    try:
                        results[i] = job.get(timeout=remaining)
                    except multiprocessing.TimeoutError:
                        logger.info(
                            f"Pipeline {i} did not return before the shared exploration deadline "
                            "(including queue wait)"
                        )
                        results[i]["status"] = PipelineStatus.TIMED_OUT
                    except Exception as e:  # noqa: BLE001 - preserve independent worker failures
                        logger.error(
                            f"Pipeline {i} execution failed with general error:\n{e}"
                        )
                        results[i]["status"] = PipelineStatus.FAILED
                        failed += 1

            logger.info("Exploration workers stopped; collecting completed candidates")
            total_training_time: float = 0.0
            semantic_validation_failure_reasons: dict[int, list[str]] = {}
            for r in results:
                if r["status"] == PipelineStatus.FAILED:
                    failed += 1
                if r["status"] == PipelineStatus.TIMED_OUT:
                    timed_out += 1
                val_attempts: int = r.get("validation_attempts", 0)
                exec_attempts: int = r.get("execution_attempts", 0)
                semantic_failures: list[str] = r.get("semantic_validation_feedback", [])
                if semantic_failures:
                    semantic_validation_failure_reasons[r["pipeline"].id] = (
                        semantic_failures
                    )
                logger.info(
                    f"Pipeline id: {r['pipeline'].id}, validation_attempts: {val_attempts}, execution_attempts: {exec_attempts}, "
                    f"semantic_validation_failures: {len(semantic_failures)}, status: {r['status'].value}"
                )

                pipeline_run_id: str | None = r.get("pipeline_run_id")
                if pipeline_run_id:
                    nested_runs_duration = get_nested_runs_total_duration(
                        pipeline_run_id, experiment_id
                    )
                    total_training_time += nested_runs_duration
            total_inference_time: float = get_nested_runs_total_llm_latency(
                session, experiment_id
            )

            logger.info(f"Failed pipelines: {failed}")
            logger.info(f"Timed out pipelines: {timed_out}")
            logger.info(
                f"Semantic validation failures: {sum(len(v) for v in semantic_validation_failure_reasons.values())}"
            )

            pipeline_run_ids: dict[str, str | None] = {
                result["pipeline"].id: result.get("pipeline_run_id")
                if result["status"] == PipelineStatus.COMPLETED
                else None
                for result in results
            }

            # remove tmp artifacts saved during execution agent phase
            shutil.rmtree(Path("tmp"), ignore_errors=True)

            from ageml.common.client import get_model_from_run_id

            def load_candidate(c):
                artifact = Path(
                    mlflow.artifacts.download_artifacts(
                        run_id=c["run_id"], artifact_path="model"
                    )
                )
                files = sorted(artifact.rglob("*.pkl"))
                if len(files) != 1 or file_hash(files[0]) != c["model_sha256"]:
                    raise ValueError("Model artifact checksum mismatch")
                code_file = mlflow.artifacts.download_artifacts(
                    run_id=c["run_id"], artifact_path="code.py"
                )
                if file_hash(code_file) != c["code_sha256"]:
                    raise ValueError("Generated code artifact checksum mismatch")
                return get_model_from_run_id(c["run_id"])

            def test_provider():
                heldout = df.iloc[protocol["partitions"]["test"]]
                return (
                    heldout.drop(columns=[target_feature]),
                    heldout[target_feature],
                    protocol["partitions"]["test"],
                )

            write_json(
                output / "exploration_failures.json",
                [
                    {
                        "pipeline_id": r["pipeline"].id,
                        "status": r["status"].value,
                        "semantic_feedback": r.get("semantic_validation_feedback", []),
                        "execution_feedback": r.get("code_execution_feedback"),
                        "pipeline_run_id": r.get("pipeline_run_id"),
                    }
                    for r in results
                ],
            )
            candidates = {
                c["run_id"]: c for r in results for c in r.get("candidates", [])
            }
            for evidence in sorted((output / "candidate_journal").glob("*.json")):
                try:
                    c = json.loads(evidence.read_text())
                except (OSError, json.JSONDecodeError):
                    continue  # An interrupted export is not a completed candidate.
                candidates[c["run_id"]] = c
            for c in candidates.values():
                if (
                    c.get("fit_succeeded")
                    and c.get("completed_at", float("inf")) > deadline
                ):
                    c.update(
                        fit_succeeded=False,
                        failure="Candidate did not complete within the exploration budget",
                    )
            res = select_and_evaluate(
                list(candidates.values()),
                protocol,
                output,
                load_candidate,
                train_df.drop(columns=[target_feature]).head(3),
                test_provider,
                get_metric(validation_metric),
                train_df[target_feature].unique() if task == "classification" else None,
            )
            for candidate in read_candidate_evidence(
                output / "validation_candidates.csv"
            ):
                if candidate.get("run_id"):
                    mlflow.MlflowClient().set_tag(
                        candidate["run_id"],
                        "eligible",
                        str(candidate["eligible"]).lower(),
                    )
            res["pipeline_run_ids"] = pipeline_run_ids
            mlflow.set_tags(
                {
                    "protocol_version": VERSION,
                    "run_identity": protocol["run_identity"],
                    "source_sha256": protocol["source_sha256"],
                    "split_identity": protocol["split_identity"],
                }
            )
            if res["test_score"] is not None:
                mlflow.log_metric("test/" + validation_metric, res["test_score"])
            if res["selection_validation_score"] is not None:
                mlflow.log_metric(
                    "selection/" + validation_metric, res["selection_validation_score"]
                )
            if res["best_run_id"]:
                from ageml.evaluation.agent import download_artifacts

                res = download_artifacts(res)
            res["semantic_validation_failures"] = sum(
                len(v) for v in semantic_validation_failure_reasons.values()
            )
            res["semantic_validation_failure_reasons"] = (
                semantic_validation_failure_reasons
            )

            elapsed_seconds = time.perf_counter() - start_time
            human_readable_runtime = str(timedelta(seconds=round(elapsed_seconds)))
            res["exploration_budget_seconds"] = timeout
            res["runtime_seconds"] = elapsed_seconds
            res["runtime_human_readable"] = human_readable_runtime
            res["pipelines_found"] = planning["pipelines_found"]
            res["training_time"] = total_training_time
            res["inference_time"] = total_inference_time
            res["token_usage"] = get_session_total_token_usage(session)
            logger.info(
                f"Best model: Pipeline {res['best_pipeline_id']}\n"
                f"  - run id = {res['best_run_id']}\n"
                f"  - run name = {res['best_run_name']}\n"
                f"  - selection {res['validation_metric']} = {res['selection_validation_score']}; test = {res['test_score']}"
            )
            logger.info(
                f"Session '{run.info.run_name}' time:\n"
                f"  - runtime_seconds = {res['runtime_seconds']:.2f}\n"
                f"  - runtime_human_readable = {res['runtime_human_readable']}\n"
                f"  - training_time = {res['training_time']:.2f}\n"
                f"  - inference_time = {res['inference_time']:.2f}"
            )
            logger.info(
                f"Session '{run.info.run_name}' token usage:\n"
                f"  - input_tokens = {res['token_usage']['input_tokens']}\n"
                f"  - output_tokens = {res['token_usage']['output_tokens']}\n"
                f"  - total_tokens = {res['token_usage']['total_tokens']}"
            )
            logger.info(
                f"Session '{run.info.run_name}' costs:\n"
                f"  - input_cost = {res['token_usage']['input_cost']}\n"
                f"  - output_cost = {res['token_usage']['output_cost']}\n"
                f"  - total_cost = {res['token_usage']['total_cost']}"
            )

            write_json(output / "result.json", res)
            mlflow.log_artifacts(str(output), artifact_path="protocol")
            return res


def read_candidate_evidence(path):
    with Path(path).open(newline="") as stream:
        return list(csv.DictReader(stream))


def invoke_agent(agent_input: dict, session: str) -> dict[str, Any]:
    # Local import: this function is also the target of multiprocessing's
    # Pool.apply_async in main() below, so it must stay picklable as a plain
    # module-level function; importing execution_agent here (rather than at
    # module load) keeps the LLM backend selection (AGEML_MODEL_NAME, set in
    # main() from --model_name) effective in worker processes too.
    from ageml.execution.agent import execution_agent

    with mlflow.context(
        tags={"session": session},
        metadata={"mlflow.trace.session": session},
    ):
        logger.info(f"Invoking execution pipeline {agent_input['pipeline'].id}")
        result = execution_agent.invoke(agent_input)
        logger.info(f"Agent returned result with keys {result.keys()}")
    return result


if __name__ == "__main__":
    fire.Fire(main)
