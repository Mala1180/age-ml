> **Created at:** 2026-09-21 13:40:43 UTC

 ## Pipeline 10

1. **imputation** with `simple_imputer`
2. **normalization** with `minmax`
3. **features** with `pca`
4. **classification** with `knn`

### Machine Learning Pipeline Explanation

This pipeline is designed to transform and classify data systematically through the following stages:

1. **Imputation**: The `SimpleImputer` replaces missing values in the dataset using either the mean or median of each feature, ensuring data completeness.
2. **Normalization**: The `MinMaxScaler` scales all features to a specific range (defaulting to [0, 1]), which standardizes the input distribution for better model performance.
3. **Features**: The `PCA` (Principal Component Analysis) algorithm reduces the dimensionality of the feature set while retaining 95% of the original variance.
4. **Classification**: The `KNeighborsClassifier` (KNN) performs the final prediction by identifying the k-nearest data points, utilizing 5 or 11 neighbors with either uniform or distance-based weighting.

### Summary of Pipeline Development

- **Objective**: The task was to build a machine learning pipeline for MNIST classification involving imputation, normalization, dimensionality reduction, and classification.
- **Design Process**: I implemented a `scikit-learn` pipeline using `SimpleImputer`, `MinMaxScaler`, `PCA`, and `KNeighborsClassifier` as requested.
- **Issues Encountered**: During the initial execution, the code failed because the `MinMaxScaler` `feature_range` parameter strictly requires a `tuple`, whereas input arguments often provide lists. 
- **Resolution**: I updated the `train_model` function to explicitly cast `feature_range` to a `tuple` before passing it to the `MinMaxScaler`, ensuring compliance with the scikit-learn API and enabling successful execution.