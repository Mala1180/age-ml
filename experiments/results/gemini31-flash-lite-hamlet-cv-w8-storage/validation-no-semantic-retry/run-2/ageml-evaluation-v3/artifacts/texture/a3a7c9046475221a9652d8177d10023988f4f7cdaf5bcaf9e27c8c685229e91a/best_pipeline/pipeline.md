> **Created at:** 2026-11-07 05:29:15 UTC

 ## Pipeline 5

1. **imputation** with `iterative_imputer`
2. **normalization** with `power_transformer`
3. **rebalancing** with `smote`
4. **classification** with `nn`

### Machine Learning Pipeline Explanation

1. **Imputation (Iterative Imputer)**: This step handles missing data by modeling each feature with missing values as a function of other features in a round-robin fashion, using `max_iter=10` to refine the estimates.

2. **Normalization (Power Transformer)**: This step applies the `yeo-johnson` transformation to stabilize variance and make the data more Gaussian-like, which helps improve the performance of the neural network.

3. **Rebalancing (SMOTE)**: This step addresses class imbalance by generating synthetic samples for the minority classes using `k_neighbors=5` to ensure the model learns from a more representative distribution.

4. **Classification (Neural Network)**: This final step uses a Multi-Layer Perceptron (`nn`) to perform the classification, configured with `hidden_layer_sizes` of either `[10]` or `[20]`, a regularization parameter `alpha=0.001`, and a training limit of `max_iter=300`.

### Summary of Pipeline Development

- **Design Choices**: The pipeline was constructed using `imblearn.pipeline.Pipeline` to ensure seamless integration between scikit-learn preprocessing steps and the imbalanced-learn `SMOTE` rebalancing technique. This architecture ensures that resampling only occurs during training, preventing data leakage.
- **Implementation Details**: The `build_model` function was designed to return an unfitted pipeline object, adhering to the requirement of separating model construction from the fitting process. The `IterativeImputer` was selected for robust handling of missing values, followed by `PowerTransformer` for feature normalization to satisfy the requirements of the `MLPClassifier`.
- **Problem Resolution**: The primary challenge was ensuring compatibility between standard scikit-learn transformers and the `SMOTE` sampler. By utilizing the `imblearn` pipeline class, we successfully resolved the issue of applying resampling within a cross-validation-friendly structure, ensuring the final code is both executable and compliant with the specified pipeline steps.