"""Run the dataset suite once per validation-check ablation config, several times over.

    python -m experiments.ablation.validation --model_name=gemini-3.1-flash-lite-preview

Ablates the execution agent's two self-correction checks (see
``ageml/execution/agent.py``): the LLM judge's semantic compliance check, and
the retry after a code execution failure. Unlike :mod:`experiments.ablation`
(which varies the specification), this axis keeps the specification fixed and
only varies ``ageml.app.main``'s ``retry_on_semantic_failure`` and
``retry_on_execution_failure`` flags.

Every (config, repetition) pair gets its own ``results.csv`` and its own
``artifacts`` tree, under
``experiments/results/<model_tag>/validation/<config>/run-<n>``.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple, Union

import fire

from ageml.common import DEFAULT_MODEL_NAME
from ageml.common.utils import safe_filename_part
from experiments import RESULTS_DIR
from experiments.ablation.campaign import (
    DEFAULT_REPETITIONS,
    AblationConfig,
    run_campaign,
)
from resources import DIR as RESOURCES_DIR


@dataclass(frozen=True)
class ValidationConfig:
    """One point of the ablation: which of the two retries are enabled."""

    id: str
    retry_on_semantic_failure: bool
    retry_on_execution_failure: bool


#: Each retry disabled on its own, against the baseline (both enabled) run by
#: `python -m experiments`.
VALIDATION_CONFIGS: Tuple[ValidationConfig, ...] = (
    ValidationConfig("no-semantic-retry", False, True),
    ValidationConfig("no-execution-retry", True, False),
)

VALIDATION_CONFIGS_BY_ID: Dict[str, ValidationConfig] = {
    config.id: config for config in VALIDATION_CONFIGS
}


def get_validation_config(config_id: str) -> ValidationConfig:
    if config_id not in VALIDATION_CONFIGS_BY_ID:
        raise ValueError(
            f"Unknown validation config '{config_id}', "
            f"admissible values are {sorted(VALIDATION_CONFIGS_BY_ID)}."
        )
    return VALIDATION_CONFIGS_BY_ID[config_id]


def run_validation_ablation(
    model_name: str = DEFAULT_MODEL_NAME,
    spec_path: Optional[str] = None,
    configs: Optional[Union[str, Sequence[str]]] = None,
    repetitions: Union[int, Sequence[int]] = DEFAULT_REPETITIONS,
) -> None:
    """Run the dataset suite once per validation-check config, once per repetition.

    Args:
        model_name: Name of the LLM backend used for planning/execution/evaluation.
            Defaults to ``ageml.common.DEFAULT_MODEL_NAME``.
        spec_path: Specification used for every config (this axis does not vary
            it). Defaults to ``resources/general-specification.yml``.
        configs: Ids of the configs to run (e.g. ``--configs=no-semantic-retry``).
            Defaults to both.
        repetitions: How many times to run each config (``--repetitions=5``),
            or the exact ids of the repetitions to run (``--repetitions=4,5``).
            Defaults to :data:`experiments.ablation.campaign.DEFAULT_REPETITIONS`.
    """
    requested: Sequence[str] = (
        [configs] if isinstance(configs, str) else list(configs or ())
    )
    selected: List[ValidationConfig] = [
        get_validation_config(c) for c in requested
    ] or list(VALIDATION_CONFIGS)
    specification: Path = Path(spec_path or RESOURCES_DIR / "general-specification.yml")

    run_campaign(
        model_name=model_name,
        output_root=RESULTS_DIR / safe_filename_part(model_name) / "validation",
        configs=[
            AblationConfig(
                id=config.id,
                run_suite_kwargs={
                    "spec_path": specification,
                    "retry_on_semantic_failure": config.retry_on_semantic_failure,
                    "retry_on_execution_failure": config.retry_on_execution_failure,
                },
            )
            for config in selected
        ],
        repetitions=repetitions,
        axis="validation",
    )


if __name__ == "__main__":
    fire.Fire(run_validation_ablation)
