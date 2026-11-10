> **Created at:** 2026-11-08 18:57:34 UTC

 ## Pipeline 19

1. **imputation** with `iterative_imputer`
2. **classification** with `knn`

### Pipeline Explanation

1. **Imputation**: This step utilizes the `IterativeImputer` to handle missing values in the dataset by modeling each feature with missing values as a function of other features in a round-robin fashion, configured with a `max_iter` of 10.

2. **Classification**: This step employs the `KNeighborsClassifier` (KNN) algorithm to predict the target class based on the proximity of data points in the feature space, with hyperparameters set to evaluate `n_neighbors` (5 or 11) and `weights` ('uniform' or 'distance').

### Summary of Pipeline Development

- **Design Choices**: The pipeline was designed to address missing data through multivariate imputation (`IterativeImputer`) followed by a non-parametric classification approach (`KNeighborsClassifier`). This combination ensures that feature dependencies are captured before classification.
- **Implementation Strategy**: The code was structured as a modular `build_model` function, ensuring compatibility with scikit-learn's `Pipeline` API. This allows for seamless integration into cross-validation loops and hyperparameter tuning workflows.
- **Compliance**: The final implementation strictly adheres to the requested steps, function signature, and the requirement to return an unfitted estimator, ensuring the pipeline is ready for deployment in a standard machine learning workflow.