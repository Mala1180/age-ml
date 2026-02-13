import networkx as nx
from networkx import DiGraph


class TestValidateGraph:
    def test_graph_is_not_connected(self, validator, sample_path):
        is_valid, message = validator.validate_graph(sample_path, True)
        assert is_valid is True
        assert message is None
        sample_path.remove_edge("step2", "step4")
        is_valid, message = validator.validate_graph(sample_path, True)
        assert is_valid is False
        assert message == "Graph is not connected."

    def test_enumerate_paths(self, validator, sample_path, sample_graph):
        paths = list(validator.enumerate_paths(sample_graph))
        assert len(paths) == 2
        path1 = paths[0]
        path2 = paths[1]
        assert nx.is_isomorphic(path1, sample_path)
        expected_path: DiGraph = DiGraph()
        expected_path.add_node("step1", value="a")
        expected_path.add_node("step3", value="e")
        expected_path.add_edge("step1", "step3")
        assert nx.is_isomorphic(path2, expected_path)

    def test_graph_with_invalid_paths(self, sample_graph, validator):
        sample_graph.nodes["step1"]["value"] = "unknown"
        is_valid, message = validator.validate_graph(sample_graph, fail_fast=False)
        assert is_valid is False
        assert message == (
            "In path ['step1', 'step2', 'step4', 'step5']:\n"
            "\n"
            "Node 'step1' has invalid value 'unknown', admissible values are ['a', 'b'].\n"
            "\n"
            "In path ['step1', 'step3']:\n"
            "\n"
            "Node 'step1' has invalid value 'unknown', admissible values are ['a', 'b'].\n"
            "\n"
            "Missing mandatory steps ['step5'].\n"
            "\n"
            "Constraints violated:\n"
            "- since 'step1' is present, required node 'step2' is missing.\n"
            "- since 'step1' is present, required node 'step4' is missing.\n"
            "- since 'step1' is present, forbidden node 'step3' is present."
        )
