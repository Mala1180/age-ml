> **Created at:** 2026-09-21 07:51:42 UTC

 ## Pipeline 19

1. **imputation** with `iterative_imputer`
2. **normalization** with `robust_scaler`
3. **rebalancing** with `smote`
4. **classification** with `nn`

### Machine Learning Pipeline Explanation

1. **Imputation (Iterative Imputer):** This step addresses missing data by modeling each feature with missing values as a function of other features, iteratively refining the estimates across a specified number of maximum iterations.

2. **Normalization (Robust Scaler):** This process scales the features using statistics that are robust to outliers, specifically by removing the median and scaling data according to the provided quantile range.

3. **Rebalancing (SMOTE):** To handle class imbalance, this step generates synthetic samples for the minority class by interpolating between existing minority instances based on a defined number of k-neighbors.

4. **Classification (Neural Network):** The final step employs a multi-layer perceptron neural network to learn the patterns in the processed data, configured with specific hidden layer architectures, regularization (alpha), and convergence limits.

### Summary of Design Evolution

- **Initial Approach:** The project began by attempting to use a standard `scikit-learn` pipeline with separate imputation paths for numeric and categorical variables, which was architecturally flawed as it applied iterative imputation to data that had not yet been properly encoded.

- **Problem Solving & Pipeline Integration:** Subsequent iterations moved toward using `imblearn.pipeline.Pipeline` to maintain compatibility between the preprocessing, rebalancing, and classification steps. A critical hurdle involved correctly configuring the `RobustScaler` parameter, which requires a `tuple` rather than a `list`, causing runtime errors in earlier versions.

- **Final Design Choice:** The final version establishes a `ColumnTransformer` to handle one-hot encoding for categorical variables before passing the combined data through the `IterativeImputer`. By wrapping the entire sequence in an `ImbPipeline`, we ensured that SMOTE is only applied during the training phase, preventing data leakage and ensuring the final model is ready for inference.