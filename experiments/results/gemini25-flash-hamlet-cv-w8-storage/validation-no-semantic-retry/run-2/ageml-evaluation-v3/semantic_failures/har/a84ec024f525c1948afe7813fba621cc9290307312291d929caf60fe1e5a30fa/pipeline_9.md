Attempt 1:
The `random_state` parameter for the `SMOTE` step is hardcoded to `42` within the pipeline. The instructions state that "The host sets every exposed random_state", implying that if a component has a `random_state` parameter, it should be exposed as an argument in the `build_model` function signature to allow the host to set it. Since `random_state` is not a parameter of `build_model`, the host cannot control it.

---

Attempt 2:
The `random_state` parameter for the `SMOTE` step is hardcoded to `42` within the pipeline. The instructions state that "The host sets every exposed random_state", implying that if a component has a `random_state` parameter, it should be exposed as an argument in the `build_model` function signature to allow the host to set it. Since `random_state` is not a parameter of `build_model`, the host cannot control it.