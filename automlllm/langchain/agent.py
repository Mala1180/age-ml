from langchain.agents import create_agent

# from langchain.agents.middleware import HumanInTheLoopMiddleware
# from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph

from automlllm import system_prompt
from automlllm.common.model import model
from automlllm.common.tools import load_dataset
from automlllm.planning.tools import (
    generate_pipeline_graph,
    validate_pipeline_graph,
    load_yaml,
)

# checkpointer = MemorySaver()
#
# middleware = HumanInTheLoopMiddleware(
#     interrupt_on={
#         "generate_computational_graph": True,
#     }
# )

planning_agent: CompiledStateGraph = create_agent(
    model=model,
    tools=[load_dataset, load_yaml, generate_pipeline_graph, validate_pipeline_graph],
    system_prompt=system_prompt,
    # checkpointer=checkpointer,
    # middleware=[middleware],
)

# config: RunnableConfig = {"configurable": {"thread_id": str(uuid.uuid4())}}
#
# # Stream agent progress and LLM tokens until interrupt
# agent_streaming(messages, config)
# for mode, chunk in planning_agent.stream(
#         {"messages": messages},
#         config=config,
#         stream_mode=["values"],
# ):
#     for step, data in chunk.items():
#         logger.info(f"step: {step}")
#         logger.info(f"content: {data}")
