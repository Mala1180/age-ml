from automlllm.specification import Specification


class TestSpecificationDescription:
    def test_describe_pipeline_includes_candidate_hyperparameters(self):
        spec_yaml = """
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
              n_estimators: [10, 50]
              max_depth: [null, 8]
        - linear

  partial_ordering: []
"""
        spec = Specification.parse(spec_yaml)

        description = spec.describe_pipeline()

        assert "- Step 'model':" in description
        assert "  - Candidates:" in description
        assert "    - 'random_forest'" in description
        assert "      - Hyperparameters:" in description
        assert "        - 'n_estimators': [10, 50]" in description
        assert "        - 'max_depth': [None, 8]" in description
        assert "    - 'linear'" in description

    def test_describe_pipeline_omits_hyperparameter_text_for_empty_params(self):
        spec_yaml = """
pipeline:
  defaults:
    candidates: []
    mandatory: false
    terminal: false
    initial: false

  steps:
    preprocessing:
      candidates:
        - standard_scaler:
            params: {}

  partial_ordering: []
"""
        spec = Specification.parse(spec_yaml)

        description = spec.describe_pipeline()

        assert "- Step 'preprocessing':" in description
        assert "  - Candidates:" in description
        assert "    - 'standard_scaler'" in description
        assert "  - Hyperparameters:" not in description
