> **Created at:** 2026-09-18 17:55:35 UTC

 ## Pipeline 2

1. **imputation** with `simple_imputer`
2. **normalization** with `standard`
3. **regression** with `ridge`

### Machine Learning Pipeline Explanation

1. **Imputation** (`simple_imputer`): This step handles missing data points in the dataset by replacing them with a calculated statistical value (the 'mean' or 'median') for each feature, ensuring the model has a complete dataset for training.

2. **Normalization** (`standard`): This step scales the features so that they have a mean of zero and a standard deviation of one, which is essential to provide uniform weighting for features and improve the convergence speed of the regression algorithm.

3. **Regression** (`ridge`): This final step fits a ridge regression model to the processed data; it introduces L2 regularization via the `alpha` parameter (1.0 or 10.0) to prevent overfitting by penalizing large coefficient values.

### Summary of Pipeline Development

- **Design Process**: The objective was to create a robust scikit-learn pipeline for house price prediction comprising imputation, normalization, and ridge regression.
- **Initial Hurdle**: The first implementation failed because it attempted to apply numerical scaling directly to categorical data, triggering a runtime error when encountering string values.
- **Resolution**: To address this, the pipeline was updated to include a `ColumnTransformer`. This structure separately processes numerical features (imputation followed by standardization) and categorical features (imputation, one-hot encoding, and sparse scaling), ensuring data compatibility.
- **Outcome**: The final version correctly maps the data processing steps to the specified pipeline requirements, resulting in a functional `train_model` function capable of handling heterogeneous input data.