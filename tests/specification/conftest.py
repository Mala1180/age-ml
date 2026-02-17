from typing import List

import pytest

from automlllm.specification import Specification
from automlllm.specification.types import Node
from automlllm.specification.validation import SpecificationValidator
from tests.resources import get_test_resource_path

spec_sample: str = get_test_resource_path("specification-sample.yml").read_text()


@pytest.fixture
def sample_pipeline() -> List[Node]:
    return [
        Node(id="step1", value="a"),
        Node(id="step2", value="c"),
        Node(id="step4", value="k"),
        Node(id="step5", value="l"),
    ]


@pytest.fixture
def specification() -> Specification:
    return Specification.parse(spec_sample)


@pytest.fixture
def validator(specification) -> SpecificationValidator:
    return SpecificationValidator(specification)
