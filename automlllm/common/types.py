from typing import Any, Dict, List

from pydantic import BaseModel


class Step(BaseModel):
    name: str
    candidate: str
    hyperparameters: Dict[str, List[Any]]


class Pipeline(BaseModel):
    steps: List[Step]
