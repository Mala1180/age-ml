Attempt 1:
The previous execution failed because the 'quantile_range' parameter for `RobustScaler` expects a tuple, but it was likely passed as a list. The code itself uses `quantile_range=quantile_range`, so the issue is with the type of the `quantile_range` argument being passed to the `build_model` function, not directly with the code's structure. To be fully compliant and executable, the `quantile_range` argument should be ensured to be a tuple, e.g., `(25.0, 75.0)` instead of `[25.0, 75.0]`.

---

Attempt 2:
The code is syntactically correct and implements the pipeline steps as requested. However, it is not fully executable because the `RobustScaler` expects the `quantile_range` parameter to be a tuple, but it is being passed as a list, causing a `TypeError`. To ensure executability, the `quantile_range` argument should be explicitly converted to a tuple before being passed to `RobustScaler`.