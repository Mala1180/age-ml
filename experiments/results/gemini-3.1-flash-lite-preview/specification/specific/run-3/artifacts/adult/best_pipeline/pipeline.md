> **Created at:** 2026-09-21 04:39:37 UTC

 ## Pipeline 20

1. **imputation** with `simple_imputer`
2. **normalization** with `robust_scaler`
3. **rebalancing** with `smote`
4. **classification** with `nn`

### Pipeline Step-by-Step Explanation

1. **Imputation (SimpleImputer)**: Handles missing data by filling in null values using a chosen strategy such as mean or median, ensuring the dataset is complete for subsequent processing.

2. **Normalization (RobustScaler)**: Rescales numerical features using the interquartile range, which makes the model resilient to outliers present in the data.

3. **Rebalancing (SMOTE)**: Addresses class imbalance by synthetically generating new examples for the minority class, helping the model learn from all classes effectively.

4. **Classification (Neural Network)**: Utilizes a Multi-Layer Perceptron to learn non-linear relationships within the processed features, performing the final prediction based on the configured hidden layers, regularization, and iteration limits.

### Summary of Design Choices and Evolution

- **Initial Approach**: We began by using `pandas.get_dummies` for categorical encoding, but this led to feature mismatch errors during inference because the dummy columns generated on the test set did not align with those from the training set.
- **Problem Solving**: To resolve this, we migrated to a `ColumnTransformer` approach. This ensures that categorical features are handled consistently using `OneHotEncoder` with `handle_unknown='ignore'`, guaranteeing that the feature space remains stable.
- **Pipeline Architecture**: We leveraged the `imblearn.pipeline.Pipeline` class to correctly integrate the `SMOTE` rebalancing step, which must occur only during training and not during evaluation.
- **Robustness**: The final design implements a dual-path preprocessing strategy where numeric and categorical data are imputed and transformed separately before being concatenated, ensuring the `RobustScaler` only processes numeric data while maintaining schema integrity throughout the entire ML workflow.