from automlllm.common.types import Step


class TestSpecificationValidator:
    def test_unknown_step(self, validator, sample_pipeline):
        sample_pipeline.append(Step(name="unknown_step", content="x"))
        is_valid, message = validator.validate_pipeline(sample_pipeline, True)
        assert is_valid is False
        assert (
            message
            == f"Unknown steps ['unknown_step'], admissible steps are {[s.id for s in validator.steps]}."
        )

    def test_missing_mandatory_step(self, validator, sample_pipeline):
        del sample_pipeline[0]  # remove step1
        del sample_pipeline[-1]  # remove step5
        is_valid, message = validator.validate_pipeline(sample_pipeline, True)
        assert is_valid is False
        assert message == "Missing mandatory steps ['step1', 'step5']."

    def test_step_with_wrong_value(self, validator, sample_pipeline):
        sample_pipeline[0] = Step(name="step1", content="y")
        is_valid, message = validator.validate_pipeline(sample_pipeline, True)
        assert is_valid is False
        assert (
            message
            == "Step 'step1' has invalid value 'y', admissible values are ['a', 'b']."
        )

    def test_ordering_violation(self, validator, sample_pipeline):
        sample_pipeline.insert(1, Step(name="step3", content="e"))
        is_valid, message = validator.validate_pipeline(sample_pipeline, True)
        assert is_valid is False
        assert (
            message == "Partial ordering violated:\n- 'step2' must come before 'step3'."
        )

    def test_wrong_initial_step(self, validator, sample_pipeline):
        sample_pipeline[0], sample_pipeline[1] = sample_pipeline[1], sample_pipeline[0]
        is_valid, message = validator.validate_pipeline(sample_pipeline, True)
        assert is_valid is False
        assert message == "Step step1 must be initial but is not the first step."

    def test_wrong_terminal_step(self, validator, sample_pipeline):
        sample_pipeline[-2], sample_pipeline[-1] = (
            sample_pipeline[-1],
            sample_pipeline[-2],
        )
        is_valid, message = validator.validate_pipeline(sample_pipeline, True)
        assert is_valid is False
        assert message == "Step step5 must be terminal but is not the last step."

    def test_pipeline_is_valid(self, validator, sample_pipeline):
        is_valid, message = validator.validate_pipeline(sample_pipeline, True)
        assert message is None
        assert is_valid is True

    def test_constraint_violation_without_values(self, validator, sample_pipeline):
        sample_pipeline[1] = Step(name="step3", content="e")
        is_valid, message = validator.validate_pipeline(sample_pipeline, True)
        assert is_valid is False

        assert message == (
            "Constraints violated:\n"
            "- since 'step1' is present, required step 'step2' is missing.\n"
            "- since 'step1' is present, forbidden step 'step3' is present."
        )

    def test_required_constraint_violation_with_values(
        self, validator, sample_pipeline
    ):
        sample_pipeline[0] = Step(name="step1", content="b")
        is_valid, message = validator.validate_pipeline(sample_pipeline, True)
        assert is_valid is False
        assert message == (
            "Constraints violated:\n"
            "- since 'step1' has value 'b', required value 'j' for step 'step4' is missing.\n"
            "- since 'step1' has value 'b', forbidden value 'l' for step 'step5' is present."
        )
