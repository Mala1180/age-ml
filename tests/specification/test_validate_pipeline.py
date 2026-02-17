from automlllm.specification.types import Node


class TestSpecificationValidator:
    def test_unknown_step(self, validator, sample_pipeline):
        sample_pipeline.append(Node(id="unknown_step", value="x"))
        is_valid, message = validator.validate_pipeline(sample_pipeline, True)
        assert is_valid is False
        assert (
            message
            == f"Unknown nodes ['unknown_step'], admissible nodes are {[n.id for n in validator.steps]}."
        )

    def test_missing_mandatory_step(self, validator):
        pipeline = [Node(id="step2", value="c"), Node(id="step4", value="k")]
        is_valid, message = validator.validate_pipeline(pipeline, True)
        assert is_valid is False
        assert message == "Missing mandatory steps ['step1', 'step5']."

    def test_step_with_wrong_value(self, validator, sample_pipeline):
        sample_pipeline[0] = Node(id="step1", value="y")
        is_valid, message = validator.validate_pipeline(sample_pipeline, True)
        assert is_valid is False
        assert (
            message
            == "Node 'step1' has invalid value 'y', admissible values are ['a', 'b']."
        )

    def test_ordering_violation(self, validator):
        pipeline = [
            Node(id="step1", value="a"),
            Node(id="step3", value="e"),
            Node(id="step2", value="c"),
            Node(id="step4", value="k"),
            Node(id="step5", value="l"),
        ]
        is_valid, message = validator.validate_pipeline(pipeline, True)
        assert is_valid is False
        assert (
            message
            == "Partial ordering violated:\n- 'step2' node must come before 'step3' node."
        )

    def test_wrong_initial_step(self, validator):
        pipeline = [
            Node(id="step2", value="c"),
            Node(id="step1", value="a"),
            Node(id="step4", value="k"),
            Node(id="step5", value="l"),
        ]
        is_valid, message = validator.validate_pipeline(pipeline, True)
        assert is_valid is False
        assert message == "Node step1 must be initial but is not the first step."

    def test_wrong_terminal_step(self, validator):
        pipeline = [
            Node(id="step1", value="a"),
            Node(id="step2", value="c"),
            Node(id="step5", value="l"),
            Node(id="step4", value="k"),
        ]
        is_valid, message = validator.validate_pipeline(pipeline, True)
        assert is_valid is False
        assert message == "Node step5 must be terminal but is not the last step."

    def test_pipeline_is_valid(self, validator, sample_pipeline):
        is_valid, message = validator.validate_pipeline(sample_pipeline, True)
        assert message is None
        assert is_valid is True

    def test_constraint_violation_without_values(self, validator):
        pipeline = [
            Node(id="step1", value="a"),
            Node(id="step3", value="e"),
            Node(id="step4", value="k"),
            Node(id="step5", value="l"),
        ]
        is_valid, message = validator.validate_pipeline(pipeline, True)
        assert is_valid is False

        assert message == (
            "Constraints violated:\n"
            "- since 'step1' is present, required node 'step2' is missing.\n"
            "- since 'step1' is present, forbidden node 'step3' is present."
        )

    def test_required_constraint_violation_with_values(self, validator):
        pipeline = [
            Node(id="step1", value="b"),
            Node(id="step2", value="c"),
            Node(id="step4", value="k"),
            Node(id="step5", value="l"),
        ]
        is_valid, message = validator.validate_pipeline(pipeline, True)
        assert is_valid is False
        assert message == (
            "Constraints violated:\n"
            "- since 'step1' has value 'b', required value 'j' for node 'step4' is missing.\n"
            "- since 'step1' has value 'b', forbidden value 'l' for node 'step5' is present."
        )
