> **Created at:** 2026-09-21 04:10:34 UTC

 ## Pipeline 21

1. **imputation** with `iterative_imputer`
2. **normalization** with `minmax`
3. **features** with `select_k_best`
4. **regression** with `knn_regressor`

### Machine Learning Pipeline Explanation

The pipeline follows a structured approach to transform raw data and predict the target variable:

1. **Imputation (Iterative Imputer):** This step handles missing values by modeling each feature with missing entries as a function of other features in a round-robin fashion, configured with `max_iter=10` iterations.

2. **Normalization (MinMax):** This step scales all numerical features to a specified range, typically `[0, 1]`, ensuring that all input variables contribute equally to the distance calculations in the subsequent regression model.

3. **Features (SelectKBest):** This step performs feature selection by keeping the top `k` features (either 5 or 10) based on their statistical correlation with the target variable using the `f_regression` scoring function.

4. **Regression (KNN Regressor):** This final step predicts the target value by averaging the `n_neighbors` (5 or 11) closest training samples, weighted by their distance (`weights='distance'`) to the query point.

### Summary of Pipeline Development

- **Design Choices:** The pipeline was designed using scikit-learn's `Pipeline` and `ColumnTransformer` to handle both numerical and categorical data correctly. The architecture follows the specified sequential order: imputation, feature scaling, feature selection, and model estimation.
- **Technical Challenges:** 
  - **Data Type Handling:** Initially, the pipeline only handled numerical features. It was updated to include an `OneHotEncoder` within a `ColumnTransformer` to correctly process the `ocean_proximity` categorical variable.
  - **Parameter Constraints:** A significant issue arose with the `feature_range` parameter of `MinMaxScaler`, which strictly requires a `tuple` rather than a `list`. The code was corrected to explicitly cast the input to a `tuple`.
  - **Formatting & Execution:** Earlier attempts were rejected due to syntax errors resulting from overly condensed code formatting. The final version adopts clean, standard Python syntax to ensure successful execution in a professional machine learning environment.