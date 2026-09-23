> **Created at:** 2026-09-20 16:24:23 UTC

 ## Pipeline 8

1. **imputation** with `simple_imputer`
2. **normalization** with `power_transformer`
3. **features** with `select_k_best`
4. **regression** with `knn_regressor`

### Pipeline Step-by-Step Explanation

1. **Imputation (SimpleImputer)**: This step handles missing numerical data in the dataset by replacing empty values with either the mean or the median of each respective column to ensure a complete input matrix.

2. **Normalization (PowerTransformer)**: This step applies a Yeo-Johnson transformation to stabilize variance and make the distribution of the numerical features more Gaussian-like, which improves model performance.

3. **Features (SelectKBest)**: This step performs univariate feature selection by retaining only the top 'k' (either 5 or 10) most significant features based on the f-regression scoring function.

4. **Regression (KNeighborsRegressor)**: This final step builds the regression model using the K-Nearest Neighbors algorithm, utilizing either 5 or 11 neighbors and distance-based weighting to predict the housing sale price.

### Summary of Pipeline Development

- **Objective**: The task was to build a machine learning pipeline for the Ames housing dataset using scikit-learn.
- **Design Choices**: 
    - A `ColumnTransformer` was implemented to isolate numerical features for imputation, ensuring data compatibility before processing.
    - The pipeline follows a linear sequence: `SimpleImputer` (handling missing values), `PowerTransformer` (normalizing distributions), `SelectKBest` (dimensionality reduction), and `KNeighborsRegressor` (predictive modeling).
    - The design adheres to the functional signature requirement `train_model(X_train, y_train, ...)` to ensure it remains modular and data-agnostic.
- **Resolved Issues**: 
    - Initially, ensuring all categorical columns did not break the `SimpleImputer` required a explicit selection of numerical types via `select_dtypes`.
    - The integration of `f_regression` as the scoring function for feature selection was verified to align with the regression task requirements.
    - No external grid search or data loading logic was included, satisfying the constraint for a clean, reproducible training function.