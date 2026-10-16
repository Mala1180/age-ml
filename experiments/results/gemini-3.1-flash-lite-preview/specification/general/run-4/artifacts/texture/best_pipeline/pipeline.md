> **Created at:** 2026-09-21 10:39:34 UTC

 ## Pipeline 18

1. **normalization** with `power_transformer`
2. **rebalancing** with `near_miss`
3. **classification** with `nn`

### Pipeline 18 Explanation

1. **Normalization**: Applies the `PowerTransformer` using the 'yeo-johnson' method to stabilize variance and minimize skewness in the input features.
2. **Rebalancing**: Utilizes the `NearMiss` algorithm with version 1 to perform undersampling on the majority class, effectively addressing class imbalance by selecting instances based on their distance to the minority class.
3. **Classification**: Employs an `MLPClassifier` (Neural Network) with configurable `hidden_layer_sizes` (10 or 20), a regularization term `alpha` of 0.001, and a maximum of 300 iterations to learn the underlying patterns for classification.

### Summary of Pipeline Development

- **Objective**: Implement a machine learning pipeline for the 'texture' dataset including normalization via `PowerTransformer`, rebalancing via `NearMiss`, and classification via a neural network (`MLPClassifier`).
- **Design Choices**: The implementation utilized the `imblearn.pipeline.Pipeline` to ensure that the rebalancing step is only applied during training, preventing data leakage. Parameters were passed dynamically to the `train_model` function to maintain flexibility as requested.
- **Technical Challenges**: The initial attempts to provide the code in a single, compact line failed due to Python's strict indentation rules and syntax limitations when importing and defining functions in a minified format. This was resolved by restructuring the code into a standard, readable Python script with proper indentation, which allowed for successful execution.