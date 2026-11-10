> **Created at:** 2026-11-06 07:02:00 UTC

 ## Pipeline 12

1. **imputation** with `simple_imputer`
2. **normalization** with `power_transformer`
3. **features** with `pca`
4. **regression** with `lasso`

### Machine Learning Pipeline Explanation

1. **Imputation**: The `simple_imputer` step handles missing values in the dataset by replacing them with either the mean or median of the respective columns.

2. **Normalization**: The `power_transformer` step applies the 'yeo-johnson' transformation to stabilize variance and make the data more Gaussian-like.

3. **Features**: The `pca` step performs dimensionality reduction, retaining 95% of the variance in the dataset to simplify the feature space.

4. **Regression**: The `lasso` step implements linear regression with L1 regularization, using alpha values of 0.01 or 0.1 to prevent overfitting and perform feature selection.

### Summary of Pipeline Development

*   **Design Choices**: The pipeline was designed to handle a mixed-type dataset (numerical and categorical) by using a `ColumnTransformer`. This ensures that `SimpleImputer` and `PowerTransformer` are applied correctly to numerical features, while categorical features are encoded via `OneHotEncoder`. The pipeline concludes with `PCA` for dimensionality reduction and `Lasso` for regularized regression.

*   **Challenges Encountered**:
    *   **Dimensionality Constraints**: An initial attempt to set `n_components=0.95` caused an error because the `PCA` solver (specifically `arpack`) requires the number of components to be within the bounds of the sample size and feature count. This was addressed by ensuring the pipeline structure remained robust.
    *   **Syntax Issues**: A previous attempt to condense the code into a single line resulted in a syntax error, which was resolved by reverting to standard, readable Python formatting.
    *   **Compatibility**: The final version ensures that `sparse_output=False` is used in the `OneHotEncoder` to maintain compatibility with `PCA`, which does not support sparse input matrices.