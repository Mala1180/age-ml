from typing import Literal, Tuple, Optional

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, START, MessagesState
from langgraph.graph.state import CompiledStateGraph

from automlllm.common.model import model
from automlllm.execution.pipeline import Step, Pipeline
from automlllm.execution.utils import extract_python_code


class CodeGenerationAgentState(MessagesState):
    dataset_path: str
    dataset_info: str
    pipeline: Pipeline
    current_step: int
    code_generation_feedback: Tuple[bool, Optional[str]]
    generated_code: str


def load_info(state: CodeGenerationAgentState) -> CodeGenerationAgentState:
    state["messages"] = [
        SystemMessage(content=system_prompt),
        AIMessage(content=f"Dataset info: \n{state['dataset_info']}"),
        AIMessage(content=f"Pipeline: \n{str(state['pipeline'].steps)}"),
    ]
    state["current_step"] = 0
    return state


def generate_code_for_step(state: CodeGenerationAgentState) -> CodeGenerationAgentState:
    step: Step = state["pipeline"].steps[state["current_step"]]
    pipeline_code: str = state["pipeline"].code
    value: str
    if isinstance(step.content, str):
        value = step.content
    else:
        assert isinstance(step.content, dict)
        value = list(step.content.keys())[0]  # TODO: place here hyperparameters
    local_prompt: str = f"""
        You are generating code for a machine learning pipeline step by step.
        The current step to implement is '{step}' using '{value}'.
        Ensure also that the generated code integrates well with the previously generated code.
        Previously generated code: 
        {pipeline_code if pipeline_code else "No code generated yet."}\n
        Generate the python code for this step only, ensuring compliance with the provided pipeline graph 
        and in such a way that can be appended to the previously generated code.
        Provide only the code without any explanations.
    """
    state["messages"] = state["messages"] + [HumanMessage(content=local_prompt)]

    response = model.invoke(state["messages"])
    assert isinstance(response.content, str)
    generated_code: str = extract_python_code(response.content)
    state["generated_code"] = generated_code
    state["messages"] = state["messages"] + [AIMessage(content=response.content)]
    return state


def validate_code_compliance(
    state: CodeGenerationAgentState,
) -> CodeGenerationAgentState:
    validating_prompt: str = "Is the generated code compliant with the provided pipeline? Answer with a simple 'yes' if compliant, otherwise answer 'no' and explain why."

    state["messages"] = state["messages"] + [HumanMessage(content=validating_prompt)]

    response = model.invoke(state["messages"])
    assert isinstance(response.content, str)
    if "yes" in response.content[:10].lower().strip():
        state["code_generation_feedback"] = (True, None)
        state["current_step"] += 1
        state["pipeline"].code += "\n" + state["generated_code"]
        state["generated_code"] = ""
    else:
        state["code_generation_feedback"] = (False, response.content)
    # append feedback message
    state["messages"] = state["messages"] + [AIMessage(content=response.content)]
    return state


def code_validation_branch(
    state: CodeGenerationAgentState,
) -> Literal["generate_code_for_step", "__end__"]:
    is_valid, message = state["code_generation_feedback"]
    if is_valid:
        if state["current_step"] >= len(state["pipeline"].steps):
            return "__end__"
        else:
            return "generate_code_for_step"
    else:
        return "generate_code_for_step"


state_graph = StateGraph(CodeGenerationAgentState)

state_graph.add_sequence(
    [
        load_info,
        generate_code_for_step,
        validate_code_compliance,
    ]
)
state_graph.add_edge(START, "load_info")
state_graph.add_conditional_edges("validate_code_compliance", code_validation_branch)


code_generation_agent: CompiledStateGraph = state_graph.compile()


system_prompt: str = """
    You are an expert of machine learning and data science.
    Your task is to help the user to generate a machine learning pipeline in python.
    You will be provided with a dataset and a graph representing the pipeline to implement.
    You must ensure that the generated machine learning code is compliant with the provided graph.
    You will generate the code step by step, i.e. node by node of the graph.
"""


print(code_generation_agent.get_graph().draw_mermaid())
