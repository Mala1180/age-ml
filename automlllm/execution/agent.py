import importlib.util
from datetime import datetime
from pathlib import Path
from types import ModuleType
from typing import Any, Optional, Literal, Dict

import mlflow
import pandas as pd
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from langgraph.constants import END
from langgraph.graph import StateGraph, START, MessagesState
from langgraph.graph.state import CompiledStateGraph
from mlflow.models import infer_signature
from pydantic import BaseModel
from sklearn.model_selection import train_test_split
from typing_extensions import override

from automlllm import logger
from automlllm.common.client import set_run_description, delete_failed_runs
from automlllm.common.model import model
from automlllm.common.types import Pipeline
from automlllm.execution.utils import (
    extract_python_code,
    grid_search_exploration,
    get_metric,
)
from automlllm.specification import Specification


class ExecutionPipeline(Pipeline):
    id: int
    code: str = ""
    explanation: str = ""
    created_at: Optional[datetime] = None

    @override
    def __str__(self) -> str:
        string_value: str = f"Pipeline {self.id}:\n{self.format_steps()}"
        if self.code:
            string_value += f"\nCode:\n```python\n{self.code}```"
        if self.explanation:
            string_value += f"\nExplanation:\n{self.explanation}"
        return string_value

    def extract_hyperparameters(self) -> Dict[str, Any]:
        hyperparameters: Dict[str, Any] = {}
        for step in self.steps:
            for hp_name, hp_values in step.hyperparameters.items():
                hyperparameters[hp_name] = hp_values
        return hyperparameters


class ExecutionAgentState(MessagesState):
    root_run_id: str
    pipeline_run_id: Optional[str]
    experiment_id: str
    dataset_path: str
    specification_path: str
    pipeline: ExecutionPipeline
    code_validation_feedback: bool
    code_execution_feedback: bool
    validation_attempts: int
    execution_attempts: int
    validation_metric: str
    maximize: bool
    train_df: pd.DataFrame
    best_run_id: Optional[str]
    target_feature: str


max_attempts: int = 5


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
    df: pd.DataFrame = pd.read_csv(state["dataset_path"])

    dataset_info: str = f"""
        Loaded dataset with {len(df)} rows and {len(df.columns)} columns
        Columns:\n{list(df.columns)}
        Data Types:\n{df.dtypes.to_markdown()}
        Description:\n{df.describe().to_markdown()}
        Preview:\n{df.head().to_markdown()}
    """
    content: str = Path(state["specification_path"]).read_text()
    technical_details: str = Specification.parse(content).describe_technical_details()
    state["messages"] = [
        SystemMessage(content=system_prompt),
        AIMessage(content=f"Dataset path: {state['dataset_path']}"),
        AIMessage(content=f"Dataset info: \n{dataset_info}"),
        AIMessage(content=f"Identified target column: '{state['target_feature']}'"),
        AIMessage(content=str(state["pipeline"])),
        AIMessage(content=technical_details),
    ]
    state["validation_attempts"] = 0
    state["execution_attempts"] = 0
    return state


def generate_pipeline_code(state: ExecutionAgentState) -> ExecutionAgentState:
    hyperparameter_names = list(state["pipeline"].extract_hyperparameters().keys())
    prompt: str = f"""
        You are generating python code for a machine learning pipeline.
        The pipeline to implement is the following:
        {str(state["pipeline"])}
        Provide only the code without any explanations, and pay attention to the indentation.
        Ensure that the generated code is compliant with the provided pipeline, i.e. it implements all the steps of the pipeline and only those steps.
        The code eventually will be executed, so ensure that it is correct and executable.
        The code must be contained in a function called 'train_model'.

        The 'train_model' function MUST have the following signature:
        def train_model(X_train, y_train{", " + ", ".join(hyperparameter_names) if hyperparameter_names else ""}):

        Where:
        - X_train: Training features (pandas DataFrame or numpy array)
        - y_train: Training target (pandas Series or numpy array)
        {f"- {", ".join(hyperparameter_names)}: Hyperparameters for the pipeline" if hyperparameter_names else ""}

        The function must:
        1. Build and train the pipeline on the training data
        2. Return the trained model

        Do NOT calculate any validation metrics - just train and return the model.
        Do NOT use grid search.
        Do NOT load data from files - data will be passed as arguments.
    """
    state["messages"] = state["messages"] + [HumanMessage(content=prompt)]

    response: Any = code_model.invoke(state["messages"])
    assert isinstance(response, CodeResponse)
    state["pipeline"].created_at = datetime.now()
    created_at = (
        "**Created at:** "
        + state["pipeline"].created_at.strftime("%Y-%m-%d %H:%M:%S")
        + " UTC"
    )
    state[
        "pipeline"
    ].code = f"# {created_at}\n\n{extract_python_code(response.code)}\n\n"

    __save_file(state["pipeline"].id, "code.py", state["pipeline"].code)
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
    if response.is_compliant:
        state["code_validation_feedback"] = True
    else:
        state["code_validation_feedback"] = False
        state["pipeline"].code = ""
        state["pipeline_run_id"] = None
    # append feedback message
    state["messages"] = state["messages"] + [AIMessage(content=response.feedback)]
    state["validation_attempts"] = state["validation_attempts"] + 1
    return state


def code_validation_branch(
    state: ExecutionAgentState,
) -> Literal["generate_pipeline_code", "execute_code", "__end__"]:
    is_valid = state["code_validation_feedback"]
    if not is_valid and state["validation_attempts"] >= max_attempts:
        logger.warning("Maximum attempts reached for code generation.")
        return "__end__"
    return "execute_code" if is_valid else "generate_pipeline_code"


def execute_code(state: ExecutionAgentState) -> ExecutionAgentState:
    state["validation_attempts"] = 0
    parent_run_id: Optional[str] = None
    algorithm: str = state["pipeline"].steps[-1].candidate
    pipeline_id: int = state["pipeline"].id
    try:
        mlflow.autolog(log_models=False)
        run_name: str = f"pipeline_{algorithm}_{pipeline_id}"
        with mlflow.start_run(
            nested=True,
            parent_run_id=state["root_run_id"],
            run_name=run_name,
        ) as parent_run:
            parent_run_id = parent_run.info.run_id
            state["pipeline_run_id"] = parent_run_id

            # Split train data into train/validation for model selection
            train_df_full = state["train_df"]
            train_df, val_df = train_test_split(
                train_df_full, test_size=0.2, random_state=42
            )

            # Extract features and target using identified target column
            target_feature = state["target_feature"]
            X_train = train_df.drop(columns=[target_feature])
            y_train = train_df[target_feature]
            X_val = val_df.drop(columns=[target_feature])
            y_val = val_df[target_feature]

            hyperparameters: Dict[str, Any] = state[
                "pipeline"
            ].extract_hyperparameters()
            index_run: int = 0
            for hp_combination in grid_search_exploration(hyperparameters):
                nested_run_name: str = f"{algorithm}_{pipeline_id}_run_{index_run}"
                with mlflow.start_run(nested=True, run_name=nested_run_name):
                    spec = importlib.util.spec_from_file_location(
                        "out_module", f"out/pipeline_{pipeline_id}/code.py"
                    )
                    module: ModuleType = importlib.util.module_from_spec(spec)  # type: ignore
                    spec.loader.exec_module(module)  # type: ignore

                    trained_model = module.train_model(
                        X_train, y_train, **hp_combination
                    )

                    # Calculate validation metric
                    y_pred = trained_model.predict(X_val)
                    metric_fn = get_metric(state["validation_metric"])
                    validation_score = metric_fn(y_val, y_pred)
                    mlflow.log_metric(state["validation_metric"], validation_score)

                    signature = infer_signature(X_train, trained_model.predict(X_train))
                    mlflow.sklearn.log_model(
                        sk_model=trained_model,
                        name="model",
                        signature=signature,
                        input_example=X_train.head(3),
                    )

                index_run += 1

            mlflow.log_artifact(f"out/pipeline_{pipeline_id}/code.py")
            state["code_execution_feedback"] = True
    except Exception as e:
        message = f"Error during code execution: {str(e)}"
        logger.info(message)
        state["messages"] = state["messages"] + [AIMessage(content=message)]
        state["code_execution_feedback"] = False
        if parent_run_id is not None:
            delete_failed_runs(parent_run_id, state["experiment_id"])

    return state


def code_execution_branch(
    state: ExecutionAgentState,
) -> Literal["generate_pipeline_code", "explain_pipeline"]:
    is_valid = state["code_execution_feedback"]
    state["execution_attempts"] += 1
    if not is_valid and state["execution_attempts"] == max_attempts:
        raise Exception("Maximum attempts reached for code execution.")
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
    explanation: Any = explanation_model.invoke(state["messages"])
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
    created_at = (
        "**Created at:** "
        + state["pipeline"].created_at.strftime("%Y-%m-%d %H:%M:%S")
        + " UTC\n\n"
    )
    state["pipeline"].explanation = (
        "> " + created_at + explanation.markdown_text + "\n\n" + summary.markdown_text
    )

    pipeline_run_id = state.get("pipeline_run_id")
    if pipeline_run_id:
        set_run_description(pipeline_run_id, state["pipeline"].explanation)

    __save_file(state["pipeline"].id, "explanation.md", state["pipeline"].explanation)
    with mlflow.start_run(run_id=pipeline_run_id):
        mlflow.log_artifact(f"out/pipeline_{state['pipeline'].id}/explanation.md")

    print(f"See code generated at: out/pipeline_{state['pipeline'].id}/code.py")
    print(
        f"See explanation generated at: out/pipeline_{state['pipeline'].id}/explanation.md"
    )
    return state


def __save_file(pipeline_id: int, filename: str, content: str) -> None:
    out_dir: Path = Path(f"out/pipeline_{pipeline_id}")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / filename).write_text(content, encoding="utf-8")


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
state_graph.add_conditional_edges("execute_code", code_execution_branch)

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
