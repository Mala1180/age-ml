import pytest
from networkx import DiGraph

from automlllm.specification import Specification
from tests.resources import get_test_resource_path

spec_sample: str = get_test_resource_path("specification-sample.yml").read_text()


@pytest.fixture
def sample_path() -> DiGraph:
    path: DiGraph = DiGraph()
    path.add_node("step1", value="a")
    path.add_node("step2", value="c")
    path.add_edge("step1", "step2")
    path.add_node("step4", value="k")
    path.add_edge("step2", "step4")
    path.add_node("step5", value="l")
    path.add_edge("step4", "step5")
    return path


@pytest.fixture
def sample_graph(sample_path: DiGraph) -> DiGraph:
    graph = sample_path.copy()
    graph.add_node("step3", value="e")
    graph.add_edge("step1", "step3")
    return graph


@pytest.fixture
def specification() -> Specification:
    return Specification.parse(spec_sample)
