from typing import List

import pytest

from ageml.common.types import Step
from ageml.specification import Specification
from ageml.specification.validation import SpecificationValidator
from tests.resources import get_test_resource_path

spec_sample: str = get_test_resource_path("specification-sample.yml").read_text()


@pytest.fixture
def sample_pipeline() -> List[Step]:
    return [
        Step(name="step1", candidate="a", hyperparameters={}),
        Step(name="step2", candidate="c", hyperparameters={}),
        Step(name="step4", candidate="k", hyperparameters={}),
        Step(name="step5", candidate="l", hyperparameters={}),
    ]


@pytest.fixture
def specification() -> Specification:
    return Specification.parse(spec_sample)


@pytest.fixture
def validator(specification) -> SpecificationValidator:
    return SpecificationValidator(specification)
