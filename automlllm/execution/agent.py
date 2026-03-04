from datetime import datetime
from pathlib import Path
from types import ModuleType
from typing import Any, Optional, Literal, Dict

import pandas as pd
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from langgraph.constants import END
from langgraph.graph import StateGraph, START, MessagesState
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel
from typing_extensions import override

from automlllm.common.model import model
from automlllm.common.types import Pipeline
from automlllm.execution.utils import extract_python_code, grid_search_exploration
from automlllm.planning.agent import PlanningPipeline
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
            string_value += f"\nCode:\n{self.code}"
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
    dataset_path: str
    specification_path: str
    planning_pipeline: PlanningPipeline
    pipeline: ExecutionPipeline
    code_validation_feedback: bool
    code_execution_feedback: bool
    human_feedback: Optional[str]
    validation_attempts: int
    execution_attempts: int


max_attempts: int = 5


class JudgeResponse(BaseModel):
    is_compliant: bool
    feedback: str


judge_model = model.with_structured_output(JudgeResponse)


def load_info(state: ExecutionAgentState) -> ExecutionAgentState:
    df: pd.DataFrame = pd.read_csv(Path(state["dataset_path"]))
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
        AIMessage(content=str(state["pipeline"])),
        AIMessage(content=technical_details),
    ]
    state["validation_attempts"] = 0
    state["execution_attempts"] = 0
    return state


def generate_pipeline_code(state: ExecutionAgentState) -> ExecutionAgentState:
    local_prompt: str = f"""
        You are generating python code for a machine learning pipeline.
        The pipeline to implement is the following:
        {str(state["pipeline"])}
        Provide only the code without any explanations.
        Ensure that the generated code is compliant with the provided pipeline, i.e. it implements all the steps of the pipeline and only those steps.
        The code eventually will be executed, so ensure that it is correct and executable.
        The code must be contained in a function called 'train_model'.
        Hyperparameters used in the entire pipeline must not be magic numbers/string, but they must 
        be passed as arguments to the 'train_model' using these parameters names: {", ".join(state["pipeline"].extract_hyperparameters().keys())}.
    """
    state["messages"] = state["messages"] + [HumanMessage(content=local_prompt)]

    response: Any = model.invoke(state["messages"])
    assert isinstance(response.content, str)
    state["pipeline"].created_at = datetime.now()
    created_at = (
        "**Created at:** "
        + state["pipeline"].created_at.strftime("%Y-%m-%d %H:%M:%S")
        + " UTC"
    )
    # mlflow_start: str = (
    #     "import mlflow, os\n\n"
    #     "run_id = os.environ['MLFLOW_RUN_ID']\n"
    #     "mlflow.start_run(run_id=run_id)\n"
    #     "mlflow.autolog()"
    # )
    # mlflow_end: str = "mlflow.end_run()"
    state["pipeline"].code = (
        f"# {created_at}\n\n"
        # f"{mlflow_start}\n\n"
        f"{extract_python_code(response.content)}\n\n"
        # f"{mlflow_end}"
    )

    __save_file(state["pipeline"].id, "code.py", state["pipeline"].code)
    state["messages"] = state["messages"] + [AIMessage(content=response.content)]
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
    # append feedback message
    state["messages"] = state["messages"] + [AIMessage(content=response.feedback)]
    return state


def code_validation_branch(
    state: ExecutionAgentState,
) -> Literal["generate_pipeline_code", "execute_code"]:
    is_valid = state["code_validation_feedback"]
    state["validation_attempts"] += 1
    if not is_valid and state["validation_attempts"] == max_attempts:
        raise Exception("Maximum attempts reached for code generation.")
    return "execute_code" if is_valid else "generate_pipeline_code"


def execute_code(state: ExecutionAgentState) -> ExecutionAgentState:
    state["validation_attempts"] = 0
    try:
        import mlflow

        with mlflow.start_run(nested=True, run_name=f"pipeline_{state['pipeline'].id}"):
            hyperparameters: Dict[str, Any] = state[
                "pipeline"
            ].extract_hyperparameters()
            for index, hp_combination in enumerate(
                grid_search_exploration(hyperparameters)
            ):
                mlflow.autolog()
                # run_id: str = f"{parent_run.info.run_id}_{index}"
                with mlflow.start_run(nested=True, run_name=f"run_{index}"):
                    import importlib.util

                    spec = importlib.util.spec_from_file_location(
                        "out_module", f"out/pipeline_{state['pipeline'].id}/code.py"
                    )
                    module: ModuleType = importlib.util.module_from_spec(spec) # type: ignore
                    spec.loader.exec_module(module)  # type: ignore

                    module.train_model(**hp_combination)

            state["code_execution_feedback"] = True
    except Exception as e:
        state["messages"] = state["messages"] + [
            AIMessage(content=f"Error during code execution: {str(e)}")
        ]
        state["code_execution_feedback"] = False

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
    explain_prompt: str = """
        Explain the final machine learning pipeline generated, step by step.
        For each pipeline step, create a concise phrase that explain such step concisely.
    """
    state["messages"] = state["messages"] + [HumanMessage(content=explain_prompt)]
    response: Any = model.invoke(state["messages"])
    state["messages"] = state["messages"] + [AIMessage(content=response.content)]
    assert isinstance(response.content, str)
    created_at = (
        "**Created at:** "
        + state["pipeline"].created_at.strftime("%Y-%m-%d %H:%M:%S")
        + " UTC\n\n"
    )
    state["pipeline"].explanation = "> " + created_at + response.content
    __save_file(state["pipeline"].id, "explanation.md", state["pipeline"].explanation)
    print(f"See code generated at: out/pipeline_{state['pipeline'].id}/code.py")
    print(
        f"See explanation generated at: out/pipeline_{state['pipeline'].id}/explanation.md"
    )
    return state


# def human_feedback(state: ExecutionAgentState) -> ExecutionAgentState:
#     res: Optional[str] = None
#     while res not in ["yes", "y", "no", "n"]:
#         res = input(
#             "Do you have any feedback on the generated pipeline, code and explanation? (y/yes or n/no)\n >"
#         ).lower()
#         if res == "yes" or res == "y":
#             feedback = input("Please provide your feedback:")
#             state["human_feedback"] = feedback
#             state["messages"] = state["messages"] + [HumanMessage(content=feedback)]
#         elif res == "no" or res == "n":
#             state["human_feedback"] = None
#         else:
#             print("Invalid input. Please answer with 'y/yes' or 'n/no'.")
#     return state
#
#
# def human_feedback_branch(
#     state: ExecutionAgentState,
# ) -> Literal["generate_pipeline_code", "__end__"]:
#     return "__end__" if state["human_feedback"] is None else "generate_pipeline_code"


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

# state_graph.add_sequence(
#     [
#         explain_pipeline,
#         human_feedback,
#     ]
# )
# state_graph.add_conditional_edges("human_feedback", human_feedback_branch)

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
