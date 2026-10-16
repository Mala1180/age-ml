"""Run the dataset suite with the CSP planning replaced by the LLM, several times over.

    python -m experiments.ablation.planning --model_name=gemini-3.1-flash-lite-preview

The LLM gets the specification (minus its budgets) and proposes a single
pipeline itself, see ``ageml/planning/plain_llm.py``. Results go to
``experiments/results/<model_tag>/planning/no-csp/run-<n>``.
"""

from pathlib import Path
from typing import Optional, Sequence, Union

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


def run_planning_ablation(
    model_name: str = DEFAULT_MODEL_NAME,
    spec_path: Optional[str] = None,
    repetitions: Union[int, Sequence[int]] = DEFAULT_REPETITIONS,
) -> None:
    """Run the dataset suite without the CSP, once per repetition.

    Args:
        model_name: Name of the LLM backend. Defaults to ``DEFAULT_MODEL_NAME``.
        spec_path: Specification given to the LLM. Defaults to
            ``resources/general-specification.yml``.
        repetitions: How many times to run (``--repetitions=5``), or the exact
            ids of the repetitions to run (``--repetitions=4,5``).
    """
    run_campaign(
        model_name=model_name,
        output_root=RESULTS_DIR / safe_filename_part(model_name) / "planning",
        configs=[
            AblationConfig(
                id="no-csp",
                run_suite_kwargs={
                    "spec_path": Path(
                        spec_path or RESOURCES_DIR / "general-specification.yml"
                    ),
                    "use_csp": False,
                },
            )
        ],
        repetitions=repetitions,
        axis="planning",
    )


if __name__ == "__main__":
    fire.Fire(run_planning_ablation)
