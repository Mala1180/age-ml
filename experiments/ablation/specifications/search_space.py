"""Size of the planning search space induced by a specification.

The planner enumerates *every* model of the constraint system before sampling
``budgets.pipelines`` of them (``ageml.planning.agent.generate_pipelines`` and
``select_pipelines``), so that size is what the ablation is really varying. It
is reported in the tables of the paper, and computed here with the very same
solver the planner uses, so that the two cannot drift apart.
"""

from typing import Any, Mapping, Optional

import yaml

from ageml.common.types import Step
from ageml.planning.solver import create_solver, enumerate_solutions
from ageml.specification import Constraint, Specification
from ageml.specification.types import TrueCondition


def count_pipelines(document: Mapping[str, Any], task: Optional[str] = None) -> int:
    """Number of pipelines the planner may pick from, the empty one included.

    ``translate_semantic_conditions`` turns every dataset condition the LLM
    validates into an unconditional constraint before solving; the conditions
    of the general specification discriminate classification from regression,
    so fixing ``task`` is enough to reproduce what the planner will face.
    """
    specification: Specification = Specification.parse(yaml.safe_dump(dict(document)))
    if task:
        specification.constraints.append(
            Constraint(
                condition=TrueCondition(),
                require=[Step(name=task, candidate="", hyperparameters={})],
                forbid=[],
            )
        )
    return sum(1 for _ in enumerate_solutions(create_solver(specification)))
