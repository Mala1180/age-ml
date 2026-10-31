import hashlib
import importlib.util
import time
from datetime import datetime
from enum import Enum
from pathlib import Path
from types import ModuleType
from typing import Any, Literal

import mlflow
import pandas as pd
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.constants import END
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph
from mlflow.models import infer_signature
from pydantic import BaseModel
from typing_extensions import override

from ageml import logger
from ageml.common.client import (
    enable_mlflow_llm_autologging,
    set_run_description,
)
from ageml.common.model import model
from ageml.common.types import Pipeline, Step
from ageml.common.utils import save_file
from ageml.execution.utils import (
    extract_python_code,
    get_metric,
    grid_search_exploration,
)
from ageml.fitting import evaluate_candidate, seed_process
from ageml.protocol import VERSION, candidate_key, file_hash, write_json
from ageml.specification import Specification
from ageml.storage import downloaded_artifact


class ExecutionPipeline(Pipeline):
    id: int
    code: str = ""
    explanation: str = ""
    created_at: datetime | None = None

    @override
    def _format_step(self, step: Step, index: int) -> str:
        markdown_step: str = f"{index}. **{step.name}** with `{step.candidate}`"
        return markdown_step

    @override
    def __str__(self) -> str:
        string_value: str = f"## Pipeline {self.id}\n\n{self.format_steps()}"
        if self.explanation:
            string_value += f"\n\n{self.explanation}"
        return string_value

    def extract_hyperparameters(self) -> dict[str, Any]:
        hyperparameters: dict[str, Any] = {}
        for step in self.steps:
            for hp_name, hp_values in step.hyperparameters.items():
                hyperparameters[hp_name] = hp_values
        return hyperparameters


class PipelineStatus(Enum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"


class ExecutionAgentState(MessagesState):
    status: PipelineStatus
    run_seed: int
    exploration_deadline: float
    cv_folds: list[dict] | None
    candidate_output_dir: str
    root_run_id: str
    failed_runs_id: str | None
    pipeline_run_id: str | None
    experiment_id: str
    validation_df: pd.DataFrame
    run_identity: str
    validation_split_hash: str
    source_sha256: str
    task: str
    candidates: list[dict]
    specification_path: str
    pipeline: ExecutionPipeline
    code_validation_feedback: bool
    code_execution_feedback: bool
    validation_attempts: int
    generation_attempts: int
    execution_attempts: int
    validation_metric: str
    maximize: bool
    train_df: pd.DataFrame
    best_run_id: str | None
    target_feature: str
    retry_on_semantic_failure: bool
    retry_on_execution_failure: bool
    semantic_validation_feedback: list[str]


class JudgeResponse(BaseModel):
    is_compliant: bool
    feedback: str


class CodeResponse(BaseModel):
    code: str


class ExplanationResponse(BaseModel):
    markdown_text: str


judge_model = model.with_structured_output(JudgeResponse)
code_model = model.with_structured_output(CodeResponse)
explanation_model = model.with_structured_output(ExplanationResponse)


def load_info(state: ExecutionAgentState) -> ExecutionAgentState:
    seed_process(state.get("run_seed", 42))
    enable_mlflow_llm_autologging()
    state["status"] = PipelineStatus.RUNNING
    state["candidates"] = []
    df: pd.DataFrame = state["train_df"]

    dataset_info: str = f"""
        Loaded dataset with {len(df)} rows and {len(df.columns)} columns
        Columns:\n{list(df.columns)}
        Data Types:\n{df.dtypes.to_markdown()}
        Description:\n{df.describe().to_markdown()}
        Preview:\n{df.head().to_markdown()}
    """
    content: str = Path(state["specification_path"]).read_text()
    specification: Specification = Specification.parse(content)
    technical_details: str = specification.describe_technical_details()
    state["generation_attempts"] = specification.generation_attempts
    state["messages"] = [
        SystemMessage(content=system_prompt),
        AIMessage(content=f"Dataset info: \n{dataset_info}"),
        AIMessage(content=f"Identified target column: '{state['target_feature']}'"),
        AIMessage(content=str(state["pipeline"])),
        AIMessage(content=technical_details),
    ]
    state["validation_attempts"] = 0
    state["execution_attempts"] = 0
    state["semantic_validation_feedback"] = []
    state.setdefault("retry_on_semantic_failure", True)
    state.setdefault("retry_on_execution_failure", True)
    return state


def generate_pipeline_code(state: ExecutionAgentState) -> ExecutionAgentState:
    hyperparameter_names = list(state["pipeline"].extract_hyperparameters().keys())
    hyperparameter_arguments = (
        ", " + ", ".join(hyperparameter_names) if hyperparameter_names else ""
    )
    hyperparameter_description = (
        f"- {', '.join(hyperparameter_names)}: Hyperparameters for the pipeline"
        if hyperparameter_names
        else ""
    )
    prompt: str = f"""
        You are generating python code for a machine learning pipeline.
        The pipeline to implement is the following:
        {state["pipeline"]!s}
        Provide only the code without any explanations, and pay attention to the indentation.
        Ensure that the generated code is compliant with the provided pipeline, i.e. it implements all the steps of the pipeline and only those steps.
        The code eventually will be executed, so ensure that it is correct and executable.
        The code must be contained in a function called 'build_model'.

        The 'build_model' function MUST have the following signature:
        def build_model(X_train, y_train{hyperparameter_arguments}):

        Where:
        - X_train: Training features (pandas DataFrame or numpy array)
        - y_train: Training target (pandas Series or numpy array)
        {hyperparameter_description}

        The function must:
        1. Build a fresh, UNFITTED sklearn-compatible estimator or pipeline.
        2. Return it WITHOUT calling fit, fit_transform, or resampling data.
        3. Put all preprocessing, feature selection and resampling INSIDE the pipeline.
        The host sets every exposed random_state and fits separately on each fold.
        Implement get_params/set_params through standard sklearn or imblearn components.

        Do NOT calculate any validation metrics - just construct and return the unfitted model.
        Do NOT use grid search.
        Do NOT load data from files - data will be passed as arguments.
    """
    state["messages"] = state["messages"] + [HumanMessage(content=prompt)]

    response = code_model.invoke(state["messages"])
    assert isinstance(response, CodeResponse)
    state["pipeline"].created_at = datetime.now()
    state["pipeline"].code = f"{extract_python_code(response.code)}\n"

    save_file(
        "code.py",
        state["pipeline"].code,
        out_dir=Path("tmp") / f"pipeline_{state['pipeline'].id}",
    )
    state["messages"] = state["messages"] + [AIMessage(content=response.code)]
    return state


def validate_code_compliance(
    state: ExecutionAgentState,
) -> ExecutionAgentState:
    validating_prompt: str = (
        "Is the generated code compliant with the provided pipeline? "
        "Answer with a simple 'yes' if both answers are 'yes', otherwise answer 'no' and explain why."
    )
    state["messages"] = state["messages"] + [HumanMessage(content=validating_prompt)]

    response = judge_model.invoke(state["messages"])
    assert isinstance(response, JudgeResponse)
    state["code_validation_feedback"] = response.is_compliant
    retry_on_semantic_failure: bool = state["retry_on_semantic_failure"]
    if not response.is_compliant:
        # Always recorded, regardless of the flag below, so compliance
        # failures stay visible in the results even when we stop retrying.
        state["semantic_validation_feedback"] = state[
            "semantic_validation_feedback"
        ] + [response.feedback]
        if retry_on_semantic_failure:
            state["pipeline"].code = ""
    # append feedback message
    state["messages"] = state["messages"] + [AIMessage(content=response.feedback)]
    state["validation_attempts"] = state["validation_attempts"] + 1

    is_valid = state["code_validation_feedback"]
    generation_attempts: int = state["generation_attempts"]
    if (
        not is_valid
        and retry_on_semantic_failure
        and state["validation_attempts"] >= generation_attempts
    ):
        state["status"] = PipelineStatus.FAILED
    return state


def code_validation_branch(
    state: ExecutionAgentState,
) -> Literal["generate_pipeline_code", "execute_code", "explain_pipeline"]:
    if not state["retry_on_semantic_failure"]:
        # The judge still ran and its verdict was recorded above; we just
        # don't act on a "no" by regenerating the code.
        return "execute_code"
    if state["status"] == PipelineStatus.FAILED:
        logger.info(
            f"Maximum attempts ({state['validation_attempts']}) reached for code validation of pipeline {state['pipeline'].id}."
        )
        return "explain_pipeline"
    is_valid = state["code_validation_feedback"]
    return "execute_code" if is_valid else "generate_pipeline_code"


def execute_code(state: ExecutionAgentState) -> ExecutionAgentState:
    state["validation_attempts"] = 0
    algorithm: str = state["pipeline"].steps[-1].candidate
    pipeline_id: int = state["pipeline"].id
    parent_run_id: str | None = state.get("pipeline_run_id")
    c = None
    # Parameters, CV scores, predictions and artifacts are logged explicitly below.
    # sklearn autolog also intercepts nested estimators/defaults and conflicts with
    # grid parameters in the same run, while repeating dataset uploads per fold.
    mlflow.sklearn.autolog(disable=True)
    try:
        run_name: str = f"pipeline_{pipeline_id}_{algorithm}"
        with mlflow.start_run(
            nested=True,
            run_id=parent_run_id,
            parent_run_id=state["root_run_id"],
            run_name=run_name,
        ) as parent_run:
            parent_run_id = parent_run.info.run_id
            state["pipeline_run_id"] = parent_run_id
            print(f"Created Run with id: {parent_run_id} for pipeline {pipeline_id}")

            semantic_failures = state["semantic_validation_feedback"]
            mlflow.log_metric("semantic_validation_failures", len(semantic_failures))
            if semantic_failures:
                mlflow.log_text(
                    "\n\n---\n\n".join(
                        f"Attempt {i + 1}:\n{feedback}"
                        for i, feedback in enumerate(semantic_failures)
                    ),
                    "semantic_validation_feedback.txt",
                )

            train_df = state["train_df"]
            val_df = state["validation_df"]

            # Extract features and target using identified target column
            target_feature = state["target_feature"]
            X_train = train_df.drop(columns=[target_feature])

            hyperparameters: dict[str, Any] = state[
                "pipeline"
            ].extract_hyperparameters()
            for index_run, hp_combination in enumerate(
                grid_search_exploration(hyperparameters)
            ):
                if time.time() >= state.get("exploration_deadline", float("inf")):
                    raise TimeoutError("Exploration deadline exceeded")
                nested_run_name: str = f"{pipeline_id}_{algorithm}_run_{index_run}"
                with mlflow.start_run(
                    nested=True, run_name=nested_run_name
                ) as fitted_run:
                    c = {
                        "candidate_key": candidate_key(
                            [
                                step.model_dump(mode="json")
                                for step in state["pipeline"].steps
                            ],
                            hp_combination,
                            state["pipeline"].code,
                            state.get("run_seed", 42),
                        ),
                        "pipeline_id": pipeline_id,
                        "run_id": fitted_run.info.run_id,
                        "hyperparameters": hp_combination,
                        "code_sha256": hashlib.sha256(
                            state["pipeline"].code.encode()
                        ).hexdigest(),
                        "fit_succeeded": False,
                        "validation_score": None,
                        "model_sha256": None,
                        "artifact_status": "fit_or_export_failed",
                        "run_identity": state["run_identity"],
                        "metric": state["validation_metric"],
                        "maximize": state["maximize"],
                        "validation_split_hash": state["validation_split_hash"],
                        "fit_attempt": state["execution_attempts"],
                        "grid_position": index_run,
                    }
                    state["candidates"].append(c)
                    mlflow.log_artifact(f"tmp/pipeline_{pipeline_id}/code.py")
                    mlflow.log_params(hp_combination)
                    spec = importlib.util.spec_from_file_location(
                        "out_module", f"tmp/pipeline_{pipeline_id}/code.py"
                    )
                    module: ModuleType = importlib.util.module_from_spec(spec)  # type: ignore
                    spec.loader.exec_module(module)  # type: ignore
                    trained_model, evaluation, predictions = evaluate_candidate(
                        module.build_model,
                        train_df,
                        val_df,
                        target_feature,
                        state["task"],
                        hp_combination,
                        state.get("run_seed", 42),
                        get_metric(state["validation_metric"]),
                        state.get("cv_folds"),
                    )
                    validation_score = evaluation["validation_score"]
                    if state.get("cv_folds") is not None:
                        mlflow.log_dict(evaluation, "cv_evaluation.json")
                        mlflow.log_text(
                            predictions.to_csv(index=False), "cv_predictions.csv"
                        )
                    mlflow.log_metric(
                        "validation/" + state["validation_metric"], validation_score
                    )

                    signature = infer_signature(
                        X_train.head(3), trained_model.predict(X_train.head(3))
                    )
                    mlflow.sklearn.log_model(
                        sk_model=trained_model,
                        name="model",
                        signature=signature,
                        input_example=X_train.head(3),
                        serialization_format=mlflow.sklearn.SERIALIZATION_FORMAT_PICKLE,
                    )

                    with downloaded_artifact(
                        fitted_run.info.run_id, "model"
                    ) as artifact_dir:
                        model_files = sorted(artifact_dir.rglob("*.pkl"))
                        if len(model_files) != 1:
                            raise ValueError("Expected one serialized model artifact")
                        model_sha256 = file_hash(model_files[0])
                    c.update(
                        {
                            "candidate_key": candidate_key(
                                [
                                    step.model_dump(mode="json")
                                    for step in state["pipeline"].steps
                                ],
                                hp_combination,
                                state["pipeline"].code,
                                state.get("run_seed", 42),
                            ),
                            "pipeline_id": pipeline_id,
                            "pipeline_run_id": parent_run_id,
                            "run_id": fitted_run.info.run_id,
                            "hyperparameters": hp_combination,
                            "code_sha256": hashlib.sha256(
                                state["pipeline"].code.encode()
                            ).hexdigest(),
                            "model_sha256": model_sha256,
                            "artifact_status": "logged",
                            "fit_seed": state.get("run_seed", 42),
                            "completed_at": time.time(),
                            "cv_fold_scores": evaluation["cv_fold_scores"],
                            "effective_random_states": evaluation[
                                "effective_random_states"
                            ],
                            "validation_score": float(validation_score),
                            "fit_succeeded": True,
                            "run_identity": state["run_identity"],
                            "validation_split_hash": state["validation_split_hash"],
                            "metric": state["validation_metric"],
                            "maximize": state["maximize"],
                        }
                    )
                    # Persist each completed candidate before explanations or timeouts.
                    if state.get("candidate_output_dir"):
                        write_json(
                            Path(state["candidate_output_dir"]) / f"{c['run_id']}.json",
                            c,
                            exclusive=True,
                        )
                    mlflow.set_tags(
                        {
                            "protocol_version": VERSION,
                            "run_identity": state["run_identity"],
                            "source_sha256": state["source_sha256"],
                            "validation_split_hash": state["validation_split_hash"],
                            "candidate_key": c["candidate_key"],
                            "eligible": "pending_artifact_verification",
                        }
                    )

            mlflow.log_artifact(f"tmp/pipeline_{pipeline_id}/code.py")
            state["code_execution_feedback"] = True
    except Exception as e:  # noqa: BLE001 - generated code may raise arbitrary exceptions
        if c is not None and not c.get("fit_succeeded"):
            c["failure"] = str(e)
        # The nested context managers already closed their runs; preserve the coordinator run.
        message = (
            f"Error during code execution of pipeline {state['pipeline'].id}: {e!s}"
        )
        logger.info(message)
        state["messages"] = state["messages"] + [AIMessage(content=message)]
        state["code_execution_feedback"] = False
        error_file_path = __save_error_file(
            state["pipeline"].id,
            state["execution_attempts"] + 1,
            str(e),
        )
        # log failed runs
        if parent_run_id is not None:
            with (
                mlflow.start_run(nested=True, run_id=parent_run_id),
                mlflow.start_run(
                    nested=True,
                    parent_run_id=parent_run_id,
                    run_name="failed_runs",
                    run_id=state.get("failed_runs_id"),
                ) as failed_runs,
            ):
                state["failed_runs_id"] = failed_runs.info.run_id
                with mlflow.start_run(
                    nested=True,
                    run_name=f"attempt_{state['execution_attempts']}",
                ):
                    mlflow.log_artifact(f"tmp/pipeline_{pipeline_id}/code.py")
                    mlflow.log_artifact(str(error_file_path))
            # Preserve failed attempts and candidate artifacts for audit.

    state["execution_attempts"] += 1

    is_valid = state["code_execution_feedback"]
    generation_attempts: int = state["generation_attempts"]
    retry_on_execution_failure: bool = state["retry_on_execution_failure"]
    if not is_valid and (
        not retry_on_execution_failure
        or state["execution_attempts"] >= generation_attempts
    ):
        state["status"] = PipelineStatus.FAILED
    return state


def code_execution_branch(state: ExecutionAgentState) -> str:
    if state["status"] == PipelineStatus.FAILED:
        if not state["retry_on_execution_failure"]:
            logger.info(
                f"Code execution failed for pipeline {state['pipeline'].id} and retries are disabled; terminating."
            )
            return END
        logger.info(
            f"Maximum attempts ({state['execution_attempts']}) reached for code execution of pipeline {state['pipeline'].id}."
        )
        return "explain_pipeline"
    is_valid = state["code_execution_feedback"]
    return "explain_pipeline" if is_valid else "generate_pipeline_code"


def explain_pipeline(state: ExecutionAgentState) -> ExecutionAgentState:
    state["execution_attempts"] = 0

    explain_prompt: str = f"""
        Explain the final machine learning pipeline generated, step by step.
        Make sure to systematically report each step of the actual pipeline:
        {state["pipeline"].steps}
        For each pipeline step, create a concise phrase that explain such step concisely.
        Use markdown format to structure the explanation paying attention to newlines and spaces.
    """
    state["messages"] = state["messages"] + [HumanMessage(content=explain_prompt)]
    explanation = explanation_model.invoke(state["messages"])
    assert isinstance(explanation, ExplanationResponse), (
        "Expected ExplanationResponse from the model"
    )
    state["messages"] = state["messages"] + [
        AIMessage(content=explanation.markdown_text)
    ]

    summarize_prompt: str = """
        Now briefly summarize the entire conversation focussing on the design choices and
        eventual problems occurred that have lead to this final version of the pipeline.
        Use markdown format to structure the summary.
    """
    state["messages"] = state["messages"] + [HumanMessage(content=summarize_prompt)]
    summary = explanation_model.invoke(state["messages"])
    assert isinstance(summary, ExplanationResponse), (
        "Expected ExplanationResponse from the model"
    )
    state["messages"] = state["messages"] + [AIMessage(content=summary.markdown_text)]

    assert state["pipeline"].created_at
    created_at = f"**Created at:** {state['pipeline'].created_at.strftime('%Y-%m-%d %H:%M:%S')} UTC"
    state["pipeline"].explanation = (
        explanation.markdown_text + "\n\n" + summary.markdown_text
    )

    pipeline_run_id = state.get("pipeline_run_id")
    if pipeline_run_id:
        set_run_description(pipeline_run_id, str(state["pipeline"].explanation))

    pipeline_md: str = f"> {created_at}\n\n {state['pipeline']!s}"
    save_file(
        "pipeline.md",
        pipeline_md,
        out_dir=Path("tmp") / f"pipeline_{state['pipeline'].id}",
    )
    mlflow.log_artifact(
        run_id=pipeline_run_id,
        local_path=f"tmp/pipeline_{state['pipeline'].id}/pipeline.md",
    )

    print(f"Generated code and explanation for pipeline_{state['pipeline'].id}")
    state["status"] = PipelineStatus.COMPLETED
    return state


def __save_error_file(pipeline_id: int, attempt: int, content: str) -> Path:
    error_dir: Path = (
        Path("tmp") / f"pipeline_{pipeline_id}" / "errors" / f"attempt_{attempt}"
    )
    return save_file("error.txt", content, out_dir=error_dir)


state_graph = StateGraph(ExecutionAgentState)

state_graph.add_edge(START, "load_info")

state_graph.add_sequence(
    [
        load_info,
        generate_pipeline_code,
        validate_code_compliance,
    ]
)
state_graph.add_conditional_edges("validate_code_compliance", code_validation_branch)

state_graph.add_node("execute_code", execute_code)
state_graph.add_conditional_edges(
    "execute_code",
    code_execution_branch,
    path_map=["generate_pipeline_code", "explain_pipeline", END],
)

state_graph.add_node("explain_pipeline", explain_pipeline)
state_graph.add_edge("explain_pipeline", END)

execution_agent: CompiledStateGraph = state_graph.compile()


system_prompt: str = """
    You are an expert of machine learning and data science.
    Your task is to help the user to generate a machine learning pipeline.
    You will be provided with a dataset and a pipeline representing the steps to implement.
    You must ensure that the generated machine learning code is compliant with the provided pipeline.
    You will generate the code step by step, i.e. step by step of the pipeline.
"""


print(execution_agent.get_graph().draw_mermaid())
