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
