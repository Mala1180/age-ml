> **Created at:** 2026-09-20 17:53:34 UTC

 ## Pipeline 5

1. **imputation** with `simple_imputer`
2. **normalization** with `power_transformer`
3. **rebalancing** with `smote`
4. **classification** with `nn`

### Machine Learning Pipeline Steps

1. **Imputation**: This step employs the `SimpleImputer` to handle missing values by replacing them with either the 'mean' or 'median' of the respective feature columns.

2. **Normalization**: The `PowerTransformer` is applied using the 'yeo-johnson' method to stabilize variance and make the data follow a more Gaussian-like distribution.

3. **Rebalancing**: The `SMOTE` (Synthetic Minority Over-sampling Technique) algorithm is utilized with `k_neighbors=5` to address class imbalance by generating synthetic samples for the minority class.

4. **Classification**: The final step uses a Neural Network (`MLPClassifier`) configured with specified `hidden_layer_sizes` ([10] or [20]), an `alpha` regularization parameter of 0.001, and a maximum iteration limit of 300 to predict the target classes.

### Summary of Design Choices and Process

1. **Pipeline Architecture**: The initial task required constructing a machine learning pipeline for the 'wilt' dataset using a specific sequence: Imputation, Normalization, Rebalancing, and Classification.
2. **Technological Implementation**: To ensure compatibility between standard `scikit-learn` transformers and the `SMOTE` oversampling technique, the `imblearn.pipeline.Pipeline` class was selected. This prevents leakage and ensures the rebalancing occurs only during training.
3. **Component Selection**: 
    - `SimpleImputer` was chosen for missing data management.
    - `PowerTransformer` ('yeo-johnson') was used to handle skewed feature distributions.
    - `SMOTE` was integrated as requested to handle the class imbalance present in the 'wilt' dataset.
    - `MLPClassifier` (Neural Network) was configured as the final estimator.
4. **Constraint Management**: The solution adhered to strict functional signature requirements (`train_model`) and avoided unnecessary operations like grid search or data loading, resulting in a clean, modular, and reusable pipeline function.