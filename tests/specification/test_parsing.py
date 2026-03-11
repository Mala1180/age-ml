import pytest

from automlllm.specification import Specification
from automlllm.specification.types import Candidate, StepCondition
from tests.specification.conftest import spec_sample


class TestSpecificationParsing:
    def test_parse_sample_specification(self):
        spec = Specification.parse(spec_sample)
        assert len(spec.steps) == 5
        step_ids = {s.id for s in spec.steps}
        assert step_ids == {"step1", "step2", "step3", "step4", "step5"}
        step1 = next(s for s in spec.steps if s.id == "step1")
        assert step1.initial is True
        assert step1.mandatory is True
        assert len(step1.candidates) == 2
        assert step1.candidates[0].name == "a"
        assert step1.candidates[1].name == "b"
        step5 = next(s for s in spec.steps if s.id == "step5")
        assert step5.terminal is True
        assert step5.mandatory is True
        assert len(spec.ordering) == 5
        assert len(spec.constraints) == 3
        assert len(spec.technical_details) == 2

    def test_parse_steps_with_string_candidates(self):
        spec = Specification.parse(spec_sample)

        for step in spec.steps:
            assert all(isinstance(c, Candidate) for c in step.candidates)
            assert all(c.params == {} for c in step.candidates)

    def test_parse_steps_with_dict_candidates(self):
        spec_sample = """
pipeline:
  defaults:
    candidates: []
    mandatory: false
    terminal: false
    initial: false
  
  steps:
    model:
      candidates:
        - random_forest:
            params:
              n_estimators: [10, 50, 100]
              max_depth: [5, 10, 15]
        - svm:
            params:
              C: [0.1, 1.0, 10.0]
              kernel: [linear, rbf]

  partial_ordering: []
"""
        spec = Specification.parse(spec_sample)

        assert len(spec.steps) == 1
        model = spec.steps[0]
        assert model.id == "model"
        assert len(model.candidates) == 2

        rf_candidate = model.candidates[0]
        assert rf_candidate.name == "random_forest"
        assert "n_estimators" in rf_candidate.params
        assert rf_candidate.params["n_estimators"] == [10, 50, 100]
        assert rf_candidate.params["max_depth"] == [5, 10, 15]

        svm_candidate = model.candidates[1]
        assert svm_candidate.name == "svm"
        assert "C" in svm_candidate.params
        assert svm_candidate.params["C"] == [0.1, 1.0, 10.0]
        assert svm_candidate.params["kernel"] == ["linear", "rbf"]

    def test_parse_mixed_candidates(self):
        spec_sample = """
pipeline:
  defaults:
    candidates: []
    mandatory: false
    terminal: false
    initial: false
  
  steps:
    preprocessing:
      candidates:
        - scaler
        - pca:
            params:
              n_components: [2, 5, 10]
  
  partial_ordering: []
"""
        spec = Specification.parse(spec_sample)

        preprocessing = spec.steps[0]
        assert len(preprocessing.candidates) == 2

        scaler = preprocessing.candidates[0]
        assert scaler.name == "scaler"
        assert scaler.params == {}

        pca = preprocessing.candidates[1]
        assert pca.name == "pca"
        assert pca.params["n_components"] == [2, 5, 10]

    def test_parse_ordering_rules(self):
        spec = Specification.parse(spec_sample)

        assert len(spec.ordering) == 5

        # Check specific ordering rules
        ordering_pairs = [(o.before, o.after) for o in spec.ordering]
        assert ("step1", "step2") in ordering_pairs
        assert ("step2", "step3") in ordering_pairs
        assert ("step1", "step3") in ordering_pairs
        assert ("step1", "step4") in ordering_pairs
        assert ("step4", "step5") in ordering_pairs

    def test_parse_ordering_sequence_syntax(self):
        spec_yaml = """
pipeline:
  defaults:
    candidates: []
    mandatory: false
    terminal: false
    initial: false

  steps:
    a:
      candidates: []
    b:
      candidates: []
    c:
      candidates: []

  partial_ordering:
    - sequence:
        - a
        - b
        - c
"""
        spec = Specification.parse(spec_yaml)
        ordering_pairs = [(o.before, o.after) for o in spec.ordering]
        assert len(ordering_pairs) == 3
        assert ("a", "b") in ordering_pairs
        assert ("a", "c") in ordering_pairs
        assert ("b", "c") in ordering_pairs

    def test_parse_constraints_without_values(self):
        spec = Specification.parse(spec_sample)

        constraint = spec.constraints[0]
        assert constraint.condition == StepCondition(step="step1")
        assert len(constraint.require) == 2
        assert constraint.require[0].candidate == ""
        assert constraint.require[1].candidate == ""
        assert len(constraint.forbid) == 1
        assert constraint.forbid[0].candidate == ""

    def test_parse_constraints_with_values(self):
        spec = Specification.parse(spec_sample)

        constraint = spec.constraints[1]
        assert constraint.condition == StepCondition(
            step="step1", candidate=Candidate(name="b")
        )
        assert len(constraint.require) == 1
        assert constraint.require[0].name == "step4"
        assert constraint.require[0].candidate == "j"
        assert len(constraint.forbid) == 1
        assert constraint.forbid[0].name == "step5"
        assert constraint.forbid[0].candidate == "l"

    def test_parse_multiple_constraints(self):
        spec = Specification.parse(spec_sample)

        assert len(spec.constraints) == 3
        assert spec.constraints[0].condition == StepCondition(step="step1")
        assert spec.constraints[1].condition == StepCondition(
            step="step1", candidate=Candidate(name="b")
        )
        assert spec.constraints[2].condition == StepCondition(
            step="step4", candidate=Candidate(name="j")
        )

    def test_parse_step_attributes(self):
        spec = Specification.parse(spec_sample)

        step1 = next(s for s in spec.steps if s.id == "step1")
        assert step1.initial is True
        assert step1.mandatory is True
        assert step1.terminal is False

        step2 = next(s for s in spec.steps if s.id == "step2")
        assert step2.initial is False
        assert step2.mandatory is False
        assert step2.terminal is False

        step5 = next(s for s in spec.steps if s.id == "step5")
        assert step5.initial is False
        assert step5.mandatory is True
        assert step5.terminal is True

    def test_parse_defaults_applied_to_steps(self):
        spec_sample = """
pipeline:
  defaults:
    candidates: []
    mandatory: true
    terminal: false
    initial: false
  
  steps:
    step1:
      candidates: [a]
    
    step2:
      candidates: [b]
      mandatory: false

  partial_ordering: []
"""
        spec = Specification.parse(spec_sample)

        step1 = next(s for s in spec.steps if s.id == "step1")
        assert step1.mandatory is True  # from defaults

        step2 = next(s for s in spec.steps if s.id == "step2")
        assert step2.mandatory is False  # overridden

    def test_parse_invalid_yaml(self):
        invalid_yaml = """
pipeline:
  steps
    step1: [invalid yaml
"""
        with pytest.raises(Exception):
            Specification.parse(invalid_yaml)

    def test_parse_constraint_with_multiple_required_nodes(self):
        spec = Specification.parse(spec_sample)

        constraint = spec.constraints[0]
        assert len(constraint.require) == 2
        required_names = [step.name for step in constraint.require]
        assert "step2" in required_names
        assert "step4" in required_names

    def test_parse_all_step_ids(self):
        spec = Specification.parse(spec_sample)

        step_map = {s.id: s for s in spec.steps}
        assert "step1" in step_map
        assert "step2" in step_map
        assert "step3" in step_map
        assert "step4" in step_map
        assert "step5" in step_map

    def test_parse_candidates_count(self):
        spec = Specification.parse(spec_sample)

        step_map = {s.id: s for s in spec.steps}
        assert len(step_map["step1"].candidates) == 2  # [a, b]
        assert len(step_map["step2"].candidates) == 2  # [c, d]
        assert len(step_map["step3"].candidates) == 4  # [e, f, g, h]
        assert len(step_map["step4"].candidates) == 3  # [i, j, k]
        assert len(step_map["step5"].candidates) == 2  # [l, m]

    def test_parse_technical_details(self):
        spec = Specification.parse(spec_sample)
        assert spec.technical_details == [
            "use python for the implementation",
            "use scikit-learn for the ML algorithms",
        ]

    def test_parse_technical_details_missing(self):
        spec_yaml = """
pipeline:
  defaults:
    candidates: []
    mandatory: false
    terminal: false
    initial: false

  steps:
    step1:
      candidates: [a]

  partial_ordering: []
"""
        spec = Specification.parse(spec_yaml)
        assert spec.technical_details == []
