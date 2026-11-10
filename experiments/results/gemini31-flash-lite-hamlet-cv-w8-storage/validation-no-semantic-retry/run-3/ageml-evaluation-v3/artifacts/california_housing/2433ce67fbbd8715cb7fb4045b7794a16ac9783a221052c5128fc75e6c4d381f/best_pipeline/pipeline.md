> **Created at:** 2026-11-08 08:36:24 UTC

 ## Pipeline 8

1. **imputation** with `simple_imputer`
2. **normalization** with `robust_scaler`
3. **features** with `pca`
4. **regression** with `knn_regressor`

### Machine Learning Pipeline Explanation

1. **Imputation (SimpleImputer)**: This step handles missing values in the dataset by replacing them with either the mean or median of their respective columns, ensuring a complete dataset for subsequent modeling.

2. **Normalization (RobustScaler)**: This step scales the numerical features using statistics that are robust to outliers, specifically by centering and scaling data based on the interquartile range (25th to 75th percentile).

3. **Features (PCA)**: This step performs dimensionality reduction by transforming the features into a set of principal components that retain 95% of the original variance, simplifying the model while preserving information.

4. **Regression (KNeighborsRegressor)**: This final step predicts the target variable by identifying the nearest neighbors in the feature space and weighting their contributions based on distance, providing a flexible, non-parametric regression approach.

### Summary of Pipeline Development

- **Design Choices**: The pipeline was constructed using a `ColumnTransformer` to handle mixed data types (numerical and categorical) appropriately. Numerical features undergo imputation and robust scaling, while categorical features are encoded. The pipeline concludes with PCA for dimensionality reduction and a K-Nearest Neighbors regressor.

- **Challenges Encountered**: 
    - **Syntax Errors**: Initial attempts to provide the code in a single line or with improper formatting caused execution failures.
    - **Type Mismatch**: A critical issue arose where the `quantile_range` hyperparameter was passed as a list, which violated the `RobustScaler` requirement for a tuple. This was resolved by explicitly casting the input to a tuple within the `build_model` function.

- **Final Outcome**: The resulting code is a robust, modular, and scikit-learn-compliant pipeline that correctly handles data preprocessing, feature engineering, and regression modeling.