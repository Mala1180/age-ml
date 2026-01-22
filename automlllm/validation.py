from typing import Optional, Dict, List, Tuple

import networkx as nx
import yaml
from networkx import DiGraph


class Validator:
    def __init__(self, spec_yaml: str):
        self.spec: Dict = yaml.safe_load(spec_yaml)
        self.pipeline: Dict = self.spec["pipeline"]
        self.steps: Dict = self.pipeline["steps"]
        self.rules: Dict = self.spec["rules"]
        self.constraints: List[Dict] = self.spec["constraints"]

    def _check_admissible_step(self, graph: DiGraph) -> bool:
        for node in graph:
            if node not in self.steps:
                return False
        return True

    def _check_ordering(self, graph: DiGraph, before: str, after: str) -> bool:
        return any(nx.all_simple_paths(graph, source=before, target=after))

    def _check_constraint(
        self,
        graph: DiGraph,
        condition: Dict,
        require: Dict,
        forbid: Dict,
    ) -> bool:
        condition_node, condition_value = list(condition.items())[0]

        if condition_node in graph:
            if (
                condition_value == {}
                or graph.nodes[condition_node]["value"] == condition_value
            ):
                required_nodes = set(require.get("steps", []))
                if not required_nodes.issubset(graph.nodes):
                    return False

                forbidden_nodes = set(forbid.get("steps", []))
                if forbidden_nodes.intersection(graph.nodes):
                    return False
        return True

    def _validate_allowed_steps(self, graph: DiGraph) -> Tuple[bool, Optional[str]]:
        for node_id in graph:
            if node_id not in self.steps:
                return False, f"Unknown step {node_id}"

            if self.steps[node_id].get("values") == {}:
                continue
            print(graph.nodes)
            print(node_id)
            print(graph.nodes[node_id])
            if graph.nodes[node_id]["value"] not in self.steps[node_id].get("values"):
                return (
                    False,
                    f"Step {node_id} has invalid value {graph.nodes[node_id]['value']}, "
                    f"admissible values are {self.steps[node_id].get('values')}",
                )
        return True, None

    def _validate_initial_steps(self, graph: DiGraph) -> Tuple[bool, Optional[str]]:
        for step_id, step in self.steps.items():
            if step_id in graph and step.get("initial", False):
                if graph.in_degree(step_id) != 0:
                    return (
                        False,
                        f"Step {step_id} must be initial but has ingoing edges",
                    )
        return True, None

    def _validate_terminal_steps(self, graph: DiGraph) -> Tuple[bool, Optional[str]]:
        for step_id, step in self.steps.items():
            if step_id in graph and step.get("terminal", False):
                if graph.out_degree(step_id) != 0:
                    return (
                        False,
                        f"Step {step_id} must be terminal but has outgoing edges",
                    )
        return True, None

    def _validate_connectivity(self, graph: DiGraph) -> Tuple[bool, Optional[str]]:
        if not nx.is_weakly_connected(graph):
            return False, "Graph is not connected"
        return True, None

    def _validate_ordering(self, graph: DiGraph) -> Tuple[bool, Optional[str]]:
        for ordering in self.rules.get("ordering", []):
            before = ordering["before"]
            after = ordering["after"]

            if (
                after in graph
                and before in graph
                and not self._check_ordering(graph, before, after)
            ):
                return False, f"Ordering {ordering} violated"
        return True, None

    def _validate_constraints(self, graph: DiGraph) -> Tuple[bool, Optional[str]]:
        for constraint in self.constraints:
            condition = constraint["condition"]
            require = constraint.get("require", {})
            forbid = constraint.get("forbid", {})
            if not self._check_constraint(graph, condition, require, forbid):
                return False, f"Constraint {constraint} violated"
        return True, None

    def validate(self, graph: DiGraph) -> Tuple[bool, Optional[str]]:
        checks = [
            self._validate_allowed_steps,
            self._validate_initial_steps,
            self._validate_terminal_steps,
            self._validate_connectivity,
            self._validate_ordering,
            self._validate_constraints,
        ]

        for check in checks:
            is_valid, message = check(graph)
            if not is_valid:
                return is_valid, message

        return True, None
