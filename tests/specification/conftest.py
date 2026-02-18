from typing import List

import pytest

from automlllm.common.types import Step
from automlllm.specification import Specification
from automlllm.specification.validation import SpecificationValidator
from tests.resources import get_test_resource_path

spec_sample: str = get_test_resource_path("specification-sample.yml").read_text()


@pytest.fixture
def sample_pipeline() -> List[Step]:
    return [
        Step(name="step1", content="a"),
        Step(name="step2", content="c"),
        Step(name="step4", content="k"),
        Step(name="step5", content="l"),
    ]


@pytest.fixture
def specification() -> Specification:
    return Specification.parse(spec_sample)


@pytest.fixture
def validator(specification) -> SpecificationValidator:
    return SpecificationValidator(specification)
