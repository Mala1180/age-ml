from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from automlllm.common.types import Step


class Defaults(BaseModel):
    mandatory: bool = False


class TimeBudget(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hours: int = Field(default=0, ge=0)
    minutes: int = Field(default=0, ge=0)
    seconds: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_non_zero_duration(self) -> "TimeBudget":
        if self.total_seconds <= 0:
            raise ValueError(
                "Budget time must be greater than zero. Set hours, minutes, or seconds."
            )
        return self

    @property
    def total_seconds(self) -> int:
        return self.hours * 3600 + self.minutes * 60 + self.seconds


class Budgets(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pipelines: int = 20
    workers: int = 5
    time: TimeBudget = Field(default_factory=lambda: TimeBudget(minutes=60))


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


class TrueCondition(Condition):
    pass


class SemanticCondition(Condition):
    pass


class StepCondition(Condition):
    step: str
    candidate: Optional[Candidate] = None


class DatasetFeatureCondition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    is_like: Optional[str] = None
    role: Optional[str] = None
    data_kind: Optional[str] = None


class DatasetCondition(SemanticCondition):
    feature: DatasetFeatureCondition

    def __str__(self):
        conditions = []
        if self.feature.is_like:
            conditions.append(f"feature name is like '{self.feature.is_like}'")
        if self.feature.role:
            conditions.append(f"feature role is '{self.feature.role}'")
        if self.feature.data_kind:
            conditions.append(f"feature data kind is '{self.feature.data_kind}'")
        return " and ".join(conditions)


class NaturalLanguageCondition(SemanticCondition):
    text: str

    def __str__(self):
        return self.text


class Constraint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    condition: Condition
    require: List[Step] = Field(default_factory=list)
    forbid: List[Step] = Field(default_factory=list)
