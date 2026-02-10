import networkx as nx
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


class TestValidator:
    def test_unknown_step(self, specification, sample_path):
        sample_path.add_node("unknown_step", value="x")
        is_valid, message = specification.validate_path(sample_path, True)
        assert is_valid is False
        assert (
            message
            == f"Unknown nodes ['unknown_step'], admissible nodes are {[n.id for n in specification.steps]}."
        )

    def test_missing_mandatory_step(self, specification, sample_path):
        sample_path.remove_nodes_from({"step1", "step5"})
        is_valid, message = specification.validate_path(sample_path, True)
        assert is_valid is False
        assert message == "Missing mandatory steps ['step1', 'step5']."

    def test_step_with_wrong_value(self, specification, sample_path):
        sample_path.nodes["step1"]["value"] = "y"
        is_valid, message = specification.validate_path(sample_path, True)
        assert is_valid is False
        assert (
            message
            == "Node 'step1' has invalid value 'y', admissible values are ['a', 'b']."
        )

    def test_ordering_violation(self, specification, sample_path):
        sample_path.add_node("step3", value="e")
        sample_path.add_edge("step3", "step2")
        is_valid, message = specification.validate_path(sample_path, True)
        assert is_valid is False
        assert (
            message
            == "Partial ordering violated:\n- 'step2' node must come before 'step3' node."
        )

    def test_wrong_initial_step(self, specification, sample_path):
        sample_path.remove_edge("step1", "step2")
        sample_path.add_edge("step2", "step1")
        is_valid, message = specification.validate_path(sample_path, True)
        assert is_valid is False
        assert message == "Node step1 must be initial but has ingoing edges."

    def test_wrong_terminal_step(self, specification, sample_path):
        sample_path.add_edge("step5", "step2")
        is_valid, message = specification.validate_path(sample_path, True)
        assert is_valid is False
        assert message == "Node step5 must be terminal but has outgoing edges."

    def test_graph_is_not_connected(self, specification, sample_path):
        is_valid, message = specification.validate_graph(sample_path, True)
        assert is_valid is True
        assert message is None
        sample_path.remove_edge("step2", "step4")
        is_valid, message = specification.validate_graph(sample_path, True)
        assert is_valid is False
        assert message == "Graph is not connected."

    def test_path_is_valid(self, specification, sample_path):
        is_valid, message = specification.validate_path(sample_path, True)
        assert message is None
        assert is_valid is True

    def test_enumerate_paths(self, specification, sample_path, sample_graph):
        paths = list(specification.enumerate_paths(sample_graph))
        assert len(paths) == 2
        path1 = paths[0]
        path2 = paths[1]
        assert nx.is_isomorphic(path1, sample_path)
        expected_path: DiGraph = DiGraph()
        expected_path.add_node("step1", value="a")
        expected_path.add_node("step3", value="e")
        expected_path.add_edge("step1", "step3")
        assert nx.is_isomorphic(path2, expected_path)

    def test_constraint_violation_without_values(self, specification, sample_path):
        sample_path.remove_node("step2")
        sample_path.add_edge("step1", "step3")
        sample_path.add_edge("step3", "step4")
        is_valid, message = specification.validate_path(sample_path, True)
        assert is_valid is False

        assert message == (
            "Constraints violated:\n"
            "- since 'step1' is present, required node 'step2' is missing.\n"
            "- since 'step1' is present, forbidden node 'step3' is present."
        )

    def test_required_constraint_violation_with_values(
        self, specification, sample_path
    ):
        sample_path.nodes["step1"]["value"] = "b"
        sample_path.add_edge("step2", "step4")
        is_valid, message = specification.validate_path(sample_path, True)
        assert is_valid is False
        assert message == (
            "Constraints violated:\n"
            "- since 'step1' has value 'b', required value 'j' for node 'step4' is missing.\n"
            "- since 'step1' has value 'b', forbidden value 'l' for node 'step5' is present."
        )
