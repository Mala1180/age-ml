from networkx import MultiDiGraph
import pytest

from automlllm.planning.validation import Validator
from tests.resources import get_test_resource_path

spec_sample: str = get_test_resource_path("specification-sample.yml").read_text()


@pytest.fixture
def sample_graph() -> MultiDiGraph:
    graph: MultiDiGraph = MultiDiGraph()
    graph.add_node("step1", value="a")
    graph.add_node("step2", value="c")
    graph.add_edge("step1", "step2")
    graph.add_node("step4", value="i")
    graph.add_edge("step2", "step4")
    graph.add_node("step5", value="k")
    graph.add_edge("step4", "step5")
    return graph


@pytest.fixture
def validator() -> Validator:
    return Validator(spec_sample, True)


class TestValidator:
    def test_unknown_step(self, validator, sample_graph):
        sample_graph.add_node("unknown_step", value="x")
        is_valid, message = validator.validate(sample_graph)
        assert is_valid is False
        assert (
            message
            == f"Unknown node 'unknown_step', admissible nodes are {list(validator.steps.keys())}."
        )

    def test_step_with_wrong_value(self, validator, sample_graph):
        sample_graph.nodes["step1"]["value"] = "y"
        is_valid, message = validator.validate(sample_graph)
        assert is_valid is False
        assert (
            message
            == "Node 'step1' has invalid value 'y', admissible values are ['a', 'b']."
        )

    def test_ordering_violation(self, validator, sample_graph):
        sample_graph.add_node("step3", value="e")
        sample_graph.add_edge("step3", "step2")
        is_valid, message = validator.validate(sample_graph)
        assert is_valid is False
        assert message == "Ordering {'before': 'step2', 'after': 'step3'} violated."

    def test_wrong_initial_step(self, validator, sample_graph):
        sample_graph.remove_edge("step1", "step2")
        sample_graph.add_edge("step2", "step1")
        is_valid, message = validator.validate(sample_graph)
        assert is_valid is False
        assert message == "Node step1 must be initial but has ingoing edges."

    def test_wrong_terminal_step(self, validator, sample_graph):
        sample_graph.add_edge("step5", "step2")
        is_valid, message = validator.validate(sample_graph)
        assert is_valid is False
        assert message == "Node step5 must be terminal but has outgoing edges."

    def test_graph_is_not_connected(self, validator, sample_graph):
        sample_graph.remove_edge("step2", "step4")
        is_valid, message = validator.validate(sample_graph)
        assert is_valid is False
        assert message == "Graph is not connected."

    def test_graph_is_valid(self, validator, sample_graph):
        is_valid, message = validator.validate(sample_graph)
        assert message is None
        assert is_valid is True

    def test_required_constraint_violation_without_value(self, validator, sample_graph):
        sample_graph.remove_node("step1")
        is_valid, message = validator.validate(sample_graph)
        assert is_valid is False

        assert message == (
            "Constraint violated since {'step2': {}} condition is met but some of "
            "required nodes ['step1'] are missing."
        )

    def test_forbidden_constraint_violation_without_value(
        self, validator, sample_graph
    ):
        sample_graph.remove_node("step1")
        is_valid, message = validator.validate(sample_graph)
        assert is_valid is False
        assert message == (
            "Constraint violated since {'step2': {}} condition is met but some of "
            "required nodes ['step1'] are missing."
        )

    def test_required_constraint_violation_with_value(self, validator, sample_graph):
        sample_graph.nodes["step1"]["value"] = "b"
        is_valid, message = validator.validate(sample_graph)
        assert is_valid is False
        assert message == (
            "Constraint violated since {'step1': 'b'} condition is met but some of "
            "required nodes {'step3': 'f', 'step4': 'i'} are missing.\n"
            "Constraint violated since {'step1': 'b'} condition is met but some of "
            "forbidden nodes {'step3': 'e', 'step4': 'j'} are present."
        )

    def test_forbidden_constraint_violation_with_value(self, validator, sample_graph):
        sample_graph.nodes["step1"]["value"] = "b"
        is_valid, message = validator.validate(sample_graph)
        assert is_valid is False
        assert message == (
            "Constraint violated since {'step1': 'b'} condition is met but some of "
            "required nodes {'step3': 'f', 'step4': 'i'} are missing.\n"
            "Constraint violated since {'step1': 'b'} condition is met but some of "
            "forbidden nodes {'step3': 'e', 'step4': 'j'} are present."
        )
