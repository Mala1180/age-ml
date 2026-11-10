> **Created at:** 2026-11-08 11:16:04 UTC

 ## Pipeline 21

1. **imputation** with `simple_imputer`
2. **normalization** with `power_transformer`
3. **features** with `select_k_best`
4. **regression** with `ridge`

### Machine Learning Pipeline Explanation

1. **Imputation (Simple Imputer)**: This step handles missing values in the dataset by replacing them with either the mean or median of the respective columns, ensuring the data is complete for subsequent processing.

2. **Normalization (Power Transformer)**: This step applies a power transformation (specifically the Yeo-Johnson method) to stabilize variance and make the data distribution more Gaussian, which helps improve the performance of linear models.

3. **Features (Select K Best)**: This step performs feature selection by identifying and retaining the top 'k' features (5 or 10) that have the strongest statistical relationship with the target variable, reducing dimensionality and noise.

4. **Regression (Ridge)**: This final step implements Ridge regression, a linear model that includes L2 regularization to prevent overfitting by penalizing large coefficients, controlled by the 'alpha' hyperparameter.

### Summary of Pipeline Design

- **Design Choices**: The pipeline was constructed using a modular `scikit-learn` approach. To handle the mixed data types (numerical and categorical) present in the provided dataset, a `ColumnTransformer` was implemented. This ensures that `SimpleImputer` and `PowerTransformer` are applied appropriately to numerical features, while categorical features are encoded via `OneHotEncoder` before entering the feature selection and regression stages.

- **Compliance**: The pipeline strictly adheres to the requested sequence: imputation, normalization, feature selection, and regression. The `build_model` function was designed to be flexible, accepting hyperparameters as arguments to allow for future tuning without modifying the core structure.

- **Problem Resolution**: A potential issue regarding the presence of non-numeric data (the 'ocean_proximity' column) was identified. The design choice to include a `ColumnTransformer` resolved this, ensuring the pipeline remains robust and executable on the full dataset without requiring manual data cleaning prior to the pipeline execution.