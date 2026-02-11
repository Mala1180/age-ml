class TestValidator:
    def test_unknown_step(self, validator, sample_path):
        sample_path.add_node("unknown_step", value="x")
        is_valid, message = validator.validate_path(sample_path, True)
        assert is_valid is False
        assert (
            message
            == f"Unknown nodes ['unknown_step'], admissible nodes are {[n.id for n in validator.steps]}."
        )

    def test_missing_mandatory_step(self, validator, sample_path):
        sample_path.remove_nodes_from({"step1", "step5"})
        is_valid, message = validator.validate_path(sample_path, True)
        assert is_valid is False
        assert message == "Missing mandatory steps ['step1', 'step5']."

    def test_step_with_wrong_value(self, validator, sample_path):
        sample_path.nodes["step1"]["value"] = "y"
        is_valid, message = validator.validate_path(sample_path, True)
        assert is_valid is False
        assert (
            message
            == "Node 'step1' has invalid value 'y', admissible values are ['a', 'b']."
        )

    def test_ordering_violation(self, validator, sample_path):
        sample_path.add_node("step3", value="e")
        sample_path.add_edge("step3", "step2")
        is_valid, message = validator.validate_path(sample_path, True)
        assert is_valid is False
        assert (
            message
            == "Partial ordering violated:\n- 'step2' node must come before 'step3' node."
        )

    def test_wrong_initial_step(self, validator, sample_path):
        sample_path.remove_edge("step1", "step2")
        sample_path.add_edge("step2", "step1")
        is_valid, message = validator.validate_path(sample_path, True)
        assert is_valid is False
        assert message == "Node step1 must be initial but has ingoing edges."

    def test_wrong_terminal_step(self, validator, sample_path):
        sample_path.add_edge("step5", "step2")
        is_valid, message = validator.validate_path(sample_path, True)
        assert is_valid is False
        assert message == "Node step5 must be terminal but has outgoing edges."

    def test_path_is_valid(self, validator, sample_path):
        is_valid, message = validator.validate_path(sample_path, True)
        assert message is None
        assert is_valid is True

    def test_constraint_violation_without_values(self, validator, sample_path):
        sample_path.remove_node("step2")
        sample_path.add_edge("step1", "step3")
        sample_path.add_edge("step3", "step4")
        is_valid, message = validator.validate_path(sample_path, True)
        assert is_valid is False

        assert message == (
            "Constraints violated:\n"
            "- since 'step1' is present, required node 'step2' is missing.\n"
            "- since 'step1' is present, forbidden node 'step3' is present."
        )

    def test_required_constraint_violation_with_values(self, validator, sample_path):
        sample_path.nodes["step1"]["value"] = "b"
        sample_path.add_edge("step2", "step4")
        is_valid, message = validator.validate_path(sample_path, True)
        assert is_valid is False
        assert message == (
            "Constraints violated:\n"
            "- since 'step1' has value 'b', required value 'j' for node 'step4' is missing.\n"
            "- since 'step1' has value 'b', forbidden value 'l' for node 'step5' is present."
        )
