"""Planning without the CSP: the LLM reads the specification and proposes a single pipeline itself.

Ablation counterpart of :mod:`ageml.planning.agent`. The specification YAML is
handed over as is, minus the ``budgets`` section (runtime knobs, of no use to
the LLM, still enforced by :func:`ageml.app.main`). No solver: constraints are
not guaranteed to be satisfied, which is precisely what is being measured.
"""

from pathlib import Path
from typing import Any

import pandas as pd
import yaml
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from ageml import logger
from ageml.common.model import model
from ageml.common.types import Step
from ageml.planning.types import PlanningPipeline
from ageml.specification import Specification


class PlannedStep(BaseModel):
    name: str
    candidate: str


class PlannedPipeline(BaseModel):
    steps: list[PlannedStep]


planning_model = model.with_structured_output(PlannedPipeline)


def plan(inputs: dict[str, Any]) -> dict[str, Any]:
    """Same contract as ``planning_agent.invoke``: ``pipelines`` and ``pipelines_found``."""
    text: str = Path(inputs["specification_path"]).read_text()
    specification: Specification = Specification.parse(text)
    raw: dict[str, Any] = yaml.safe_load(text)
    raw.pop("budgets", None)
    df: pd.DataFrame = inputs["train_df"]

    response = planning_model.invoke(
        [
            HumanMessage(
                content=f"""
        You are an expert of machine learning and data science.
        Propose the single best machine learning pipeline for the dataset below,
        following the specification: the steps and candidates you can pick from, their order,
        and the constraints on which steps are required or forbidden under which conditions.

        Dataset: {len(df)} rows, target feature: '{inputs["target_feature"]}'
        Data Types:\n{df.dtypes.to_markdown()}
        Preview:\n{df.head().to_markdown()}

        Specification:
        {yaml.safe_dump(raw, sort_keys=False)}

        The pipeline is the ordered list of its steps, each with the step name and one candidate.
    """
            )
        ]
    )
    assert isinstance(response, PlannedPipeline)

    params: dict[tuple, dict[str, list[Any]]] = {
        (step.id, candidate.name): candidate.params
        for step in specification.steps
        for candidate in step.candidates
    }
    pipeline = PlanningPipeline(
        steps=[
            Step(
                name=s.name,
                candidate=s.candidate,
                hyperparameters=params.get((s.name, s.candidate), {}),
            )
            for s in response.steps
        ]
    )
    logger.info(f"LLM-planned pipeline:\n{pipeline.format_steps()}")
    return {"pipelines": [pipeline], "pipelines_found": 1}
