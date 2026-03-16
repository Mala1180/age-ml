from typing import override

from automlllm.common.types import Pipeline


class PlanningPipeline(Pipeline):
    @override
    def __str__(self) -> str:
        return f"Planning Pipeline:\n{self.format_steps()}"
