from typing import Dict, List

from pydantic import BaseModel


class Step(BaseModel):
    name: str
    content: str | Dict[str, Dict]


class Pipeline(BaseModel):
    steps: List[Step]
    code: str
