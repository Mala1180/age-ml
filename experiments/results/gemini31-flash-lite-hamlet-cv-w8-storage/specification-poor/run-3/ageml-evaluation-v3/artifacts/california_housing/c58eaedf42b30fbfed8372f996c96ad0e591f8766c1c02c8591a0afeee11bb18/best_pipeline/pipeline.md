> **Created at:** 2026-11-08 00:41:23 UTC

 ## Pipeline 4

1. **imputation** with `iterative_imputer`
2. **normalization** with `standard`
3. **regression** with `knn_regressor`

### Machine Learning Pipeline Explanation

1. **Imputation (Iterative Imputer)**: This step handles missing values in the dataset by modeling each feature with missing values as a function of other features in a round-robin fashion, using `max_iter` to control the number of imputation cycles.

2. **Normalization (Standard Scaler)**: This step transforms the numerical features to have a mean of 0 and a standard deviation of 1, ensuring that all features contribute equally to the model regardless of their original scale.

3. **Regression (KNN Regressor)**: This final step predicts the target variable by averaging the values of the `n_neighbors` nearest data points in the feature space, with the `weights` parameter determining the influence of each neighbor based on their distance.

### Summary of Pipeline Development

- **Design Choices**: The pipeline was constructed using `scikit-learn`'s `Pipeline` class to ensure modularity. It incorporates `ColumnTransformer` to handle mixed data types (numerical and categorical) before applying the requested sequence: `IterativeImputer` for missing data, `StandardScaler` for feature normalization, and `KNeighborsRegressor` for the final prediction.

- **Challenges Encountered**: Initial attempts to provide the code in a single-line format caused syntax errors during automated execution. The final version resolved this by providing clean, multi-line Python code that adheres to standard formatting practices, ensuring the `build_model` function is correctly defined and executable.