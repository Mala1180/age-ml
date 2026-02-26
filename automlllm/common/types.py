from typing import Any, Dict, List

from pydantic import BaseModel


class Step(BaseModel):
    name: str
    candidate: str
    hyperparameters: Dict[str, List[Any]]


class Pipeline(BaseModel):
    steps: List[Step]

    def _format_step(self, step: Step, index: int) -> str:
        hyperparameters: str = f" and hyperparameters: {step.hyperparameters}" if step.hyperparameters else ""
        return f"Step {index}: {step.name} with {step.candidate}{hyperparameters}"

    def format_steps(self) -> str:
        if not self.steps:
            return "(no steps)"
        return "\n".join(
            self._format_step(step=step, index=index)
            for index, step in enumerate(self.steps, start=1)
        )

    def __str__(self) -> str:
        return f"Pipeline:\n{self.format_steps()}"
