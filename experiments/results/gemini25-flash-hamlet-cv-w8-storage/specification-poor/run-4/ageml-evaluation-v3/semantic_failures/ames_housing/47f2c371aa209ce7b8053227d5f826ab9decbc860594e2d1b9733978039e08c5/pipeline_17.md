Attempt 1:
The `imputation_strategy` parameter is provided in the function signature, but it is only used for numerical features. For categorical features, the `SimpleImputer` is hardcoded to use `strategy='most_frequent'`, which means the provided `imputation_strategy` parameter is not fully utilized across all imputation steps as implied by the pipeline definition.

---

Attempt 2:
The `imputation_strategy` parameter is provided in the function signature, but it is only used for numerical features. For categorical features, the `SimpleImputer` is hardcoded to use `strategy='most_frequent'`, which means the provided `imputation_strategy` parameter is not fully utilized across all imputation steps as implied by the pipeline definition.