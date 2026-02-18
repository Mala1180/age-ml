from datetime import datetime
from pathlib import Path
from typing import Any, Tuple, Optional, Literal

from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from langgraph.constants import END
from langgraph.graph import StateGraph, START, MessagesState
from langgraph.graph.state import CompiledStateGraph
from typing_extensions import override

from automlllm.common.model import model
from automlllm.common.types import Pipeline
from automlllm.execution.utils import extract_python_code
from automlllm.planning.agent import PlanningPipeline


class ExecutionPipeline(Pipeline):
    id: int
    code: str = ""
    explanation: str = ""

    @override
    def __str__(self) -> str:
        string_value: str = f"Pipeline {self.id}:\n" + "\n".join(
            [f"{step.name}: {step.content}" for step in self.steps]
        )
        if self.code:
            string_value += f"\nCode:\n{self.code}"
        if self.explanation:
            string_value += f"\nExplanation:\n{self.explanation}"
        return string_value


class ExecutionAgentState(MessagesState):
    dataset_path: str
    dataset_info: str
    planning_pipeline: PlanningPipeline
    pipeline: ExecutionPipeline
    # current_step: int
    code_generation_feedback: Tuple[bool, Optional[str]]


# def load_pipeline(state: ExecutionAgentState) -> ExecutionAgentState:
#     steps: List[Step] = [Step(**step_data) for step_data in state["pipeline"]]
#     state["planned_pipeline"] = ExecutionPipeline(id=1, steps=steps)
#     return state


def load_info(state: ExecutionAgentState) -> ExecutionAgentState:
    state["messages"] = [
        SystemMessage(content=system_prompt),
        AIMessage(content=f"Dataset path: {state['dataset_path']}"),
        AIMessage(content=f"Dataset info: \n{state['dataset_info']}"),
        AIMessage(content=f"Pipeline: \n{str(state['pipeline'])}"),
    ]
    return state


def generate_pipeline_code(state: ExecutionAgentState) -> ExecutionAgentState:
    local_prompt: str = f"""
        You are generating python code for a machine learning pipeline.
        The pipeline to implement is the following:
        {str(state["pipeline"])}
        Provide only the code without any explanations.
        Ensure that the generated code is compliant with the provided pipeline, i.e. it implements all the steps of the pipeline and only those steps.
        The code eventually will be executed, so ensure that it is correct and executable.
    """
    state["messages"] = state["messages"] + [HumanMessage(content=local_prompt)]

    response: Any = model.invoke(state["messages"])
    assert isinstance(response.content, str)
    state["pipeline"].code = extract_python_code(response.content)
    state["messages"] = state["messages"] + [AIMessage(content=response.content)]
    return state


def validate_code_compliance(
    state: ExecutionAgentState,
) -> ExecutionAgentState:
    validating_prompt: str = "Is the generated code compliant with the provided pipeline? Answer with a simple 'yes' if compliant, otherwise answer 'no' and explain why."

    state["messages"] = state["messages"] + [HumanMessage(content=validating_prompt)]

    response: Any = model.invoke(state["messages"])
    assert isinstance(response.content, str)
    if "yes" in response.content[:10].lower().strip():
        state["code_generation_feedback"] = (True, None)
    else:
        state["code_generation_feedback"] = (False, response.content)
        state["pipeline"].code = ""
    # append feedback message
    state["messages"] = state["messages"] + [AIMessage(content=response.content)]
    return state


def code_validation_branch(
    state: ExecutionAgentState,
) -> Literal["generate_pipeline_code", "explain_pipeline"]:
    is_valid: bool
    message: Optional[str]
    is_valid, message = state["code_generation_feedback"]
    return "explain_pipeline" if is_valid else "generate_pipeline_code"


def explain_pipeline(state: ExecutionAgentState) -> ExecutionAgentState:
    explain_prompt: str = """
        Explain the final machine learning pipeline generated, step by step.
        For each pipeline step, create a concise phrase that explain such step concisely.
    """
    state["messages"] = state["messages"] + [HumanMessage(content=explain_prompt)]
    response: Any = model.invoke(state["messages"])
    state["messages"] = state["messages"] + [AIMessage(content=response.content)]
    assert isinstance(response.content, str)
    state["pipeline"].explanation = response.content
    return state


def save_pipeline(state: ExecutionAgentState) -> ExecutionAgentState:
    pipeline: ExecutionPipeline = state["pipeline"]
    out_dir: Path = Path(f"out/pipeline_{pipeline.id}")
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now()
    created_at = (
        "**Created at:** " + timestamp.strftime("%Y-%m-%d %H:%M:%S") + " UTC\n\n"
    )
    pipeline.code = "# " + created_at + pipeline.code
    pipeline.explanation = "> " + created_at + pipeline.explanation
    (out_dir / "code.py").write_text(pipeline.code, encoding="utf-8")
    (out_dir / "explanation.md").write_text(pipeline.explanation, encoding="utf-8")
    return state


def execute_code(state: ExecutionAgentState) -> ExecutionAgentState:
    try:
        import mlflow

        mlflow.autolog()
        # WARNING: Using eval/exec can be dangerous. This is just for demonstration purposes.
        namespace: dict = {}
        exec(state["pipeline"].code, namespace, namespace)
    except Exception as e:
        state["messages"] = state["messages"] + [
            AIMessage(content=f"Error during code execution: {str(e)}")
        ]

    return state


state_graph = StateGraph(ExecutionAgentState)

state_graph.add_sequence(
    [
        load_info,
        generate_pipeline_code,
        validate_code_compliance,
    ]
)
state_graph.add_edge(START, "load_info")
state_graph.add_conditional_edges("validate_code_compliance", code_validation_branch)
state_graph.add_sequence(
    [
        explain_pipeline,
        save_pipeline,
        execute_code,
    ]
)
state_graph.add_edge("execute_code", END)

execution_agent: CompiledStateGraph = state_graph.compile()


system_prompt: str = """
    You are an expert of machine learning and data science.
    Your task is to help the user to generate a machine learning pipeline in python.
    You will be provided with a dataset and a pipeline representing the steps to implement.
    You must ensure that the generated machine learning code is compliant with the provided pipeline.
    You will generate the code step by step, i.e. step by step of the pipeline.
"""


print(execution_agent.get_graph().draw_mermaid())
