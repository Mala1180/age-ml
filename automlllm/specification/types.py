from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict

from automlllm.common.types import Step


class Defaults(BaseModel):
    mandatory: bool = False
    initial: bool = False
    terminal: bool = False


class Candidate(BaseModel):
    name: str
    params: Dict[str, List[Any]] = Field(default_factory=dict)


class StepFields(Defaults):
    candidates: List[Candidate] = Field(default_factory=list)


class SpecStep(StepFields):
    model_config = ConfigDict(extra="forbid")
    id: str


class OrderingRule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    before: str
    after: str


class Condition(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StepCondition(Condition):
    step: str
    candidate: Optional[Candidate] = None


class DatasetFeatureCondition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    is_like: Optional[str] = None
    role: Optional[str] = None
    data_kind: Optional[str] = None


class DatasetCondition(Condition):
    feature: DatasetFeatureCondition


class NaturalLanguageCondition(Condition):
    text: str


class Constraint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    condition: Condition
    require: List[Step] = Field(default_factory=list)
    forbid: List[Step] = Field(default_factory=list)
