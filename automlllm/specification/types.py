from typing import Optional, Dict, List, Any

from pydantic import BaseModel, Field, ConfigDict


class Node(BaseModel):
    id: str
    value: Optional[str] = None


class Defaults(BaseModel):
    mandatory: bool = False
    initial: bool = False
    terminal: bool = False


class Candidate(BaseModel):
    name: str
    params: Dict[str, List[Any]] = Field(default_factory=dict)


class StepFields(Defaults):
    candidates: List[Candidate] = Field(default_factory=list)


class Step(StepFields):
    model_config = ConfigDict(extra="forbid")
    id: str


class OrderingRule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    before: str
    after: str


class Constraint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    condition: Dict
    require: List[Node] = Field(default_factory=list)
    forbid: List[Node] = Field(default_factory=list)
