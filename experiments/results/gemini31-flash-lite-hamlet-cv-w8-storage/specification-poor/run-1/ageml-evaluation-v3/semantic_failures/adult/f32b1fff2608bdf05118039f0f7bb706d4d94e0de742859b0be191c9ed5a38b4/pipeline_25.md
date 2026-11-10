Attempt 1:
The code uses a lambda function inside the pipeline, which causes pickling errors during cross-validation in many environments. Additionally, the previous attempt failed due to syntax issues when using semicolons in a single line. The logic is correct, but the implementation structure needs to avoid local objects for pickling compatibility.

---

Attempt 2:
The code uses a lambda function inside a FunctionTransformer, which is not serializable (pickleable) by scikit-learn's cross-validation tools. To be compliant, a named function defined at the module level must be used instead of a lambda.