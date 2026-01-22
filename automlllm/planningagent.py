from langchain.agents import create_agent

# from langchain.agents.middleware import HumanInTheLoopMiddleware
# from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph

from automlllm.model import model
from automlllm.tools import (
    generate_pipeline_graph,
    validate_pipeline_graph,
    load_csv,
    load_yaml,
)

system_prompt: str = """
    You are a helpful assistant able to design machine learning pipelines.
    Your task is to create a graph representing a machine learning pipeline based on the provided dataset and specification.
    The pipeline must respect the specification provided in yaml format.
    Pipeline step names are provided as the keys in the 'steps' section of the specification, under the 'pipeline' key.
    These step names should be the node keys in the graph.
    Values for each step should be chosen among the admissible values defined inside the spep object.
    The output should be a graph representing the machine learning pipeline steps.
    It is not necessary to use all the steps defined in the specification, but you have to validate that the pipeline respects the specification.
    You need to create the best pipeline depending on the dataset characteristics.
"""


# checkpointer = MemorySaver()
#
# middleware = HumanInTheLoopMiddleware(
#     interrupt_on={
#         "generate_computational_graph": True,
#     }
# )

planning_agent: CompiledStateGraph = create_agent(
    model=model,
    tools=[load_csv, load_yaml, generate_pipeline_graph, validate_pipeline_graph],
    system_prompt=system_prompt,
    # checkpointer=checkpointer,
    # middleware=[middleware],
)
