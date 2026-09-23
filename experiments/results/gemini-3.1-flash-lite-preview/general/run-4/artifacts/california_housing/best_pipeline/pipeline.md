> **Created at:** 2026-09-21 15:30:25 UTC

 ## Pipeline 3

1. **imputation** with `simple_imputer`
2. **normalization** with `power_transformer`
3. **features** with `select_k_best`
4. **regression** with `knn_regressor`

### Pipeline Step-by-Step Explanation

1. **Imputation (SimpleImputer)**: This step handles missing data by replacing missing values with either the mean or the median of the respective column to ensure dataset completeness.

2. **Normalization (PowerTransformer)**: This step applies the 'yeo-johnson' transformation to stabilize variance and make data more Gaussian-like, which is crucial for distance-based algorithms.

3. **Features (SelectKBest)**: This step selects the top 'k' features (5 or 10) based on their relationship with the target variable using the f_regression scoring function to reduce dimensionality.

4. **Regression (KNeighborsRegressor)**: This final step performs the prediction by calculating the distance-weighted average of the 'n_neighbors' (5 or 11) nearest training samples.

### Summary of Pipeline Design

- **Objective**: Developed a robust regression pipeline for the California Housing dataset using `scikit-learn`.
- **Design Process**: The implementation followed a modular approach, leveraging a `Pipeline` object to sequence data preprocessing (imputation and normalization), feature selection, and model training. A `ColumnTransformer` was used to ensure numerical features were appropriately transformed while maintaining data integrity.
- **Design Choices**: 
    - **Imputation**: Selected `SimpleImputer` to handle missing values flexibly.
    - **Normalization**: Chose `PowerTransformer` to address skewness in housing data distributions.
    - **Feature Selection**: Implemented `SelectKBest` with `f_regression` to filter relevant input variables.
    - **Regression**: Integrated `KNeighborsRegressor` as requested, utilizing `distance` weights for optimized performance.
- **Outcome**: The resulting `train_model` function provides a clean, encapsulated, and scikit-learn compliant workflow that accepts hyperparameters as arguments, ensuring high reproducibility without hardcoded settings.