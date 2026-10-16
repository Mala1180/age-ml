> **Created at:** 2026-10-16 11:00:47 UTC

 ## Pipeline 0

1. **imputation** with `simple_imputer`
2. **normalization** with `standard`
3. **features** with `pca`
4. **rebalancing** with `smote`
5. **classification** with `nn`

### Machine Learning Pipeline Explanation

- **1. Imputation (Simple Imputer):** This step handles missing values in the dataset by replacing them with either the mean or median of each column, ensuring a complete input matrix for subsequent operations.

- **2. Normalization (Standardization):** This step transforms the features to have a mean of zero and a standard deviation of one, bringing all variables onto a common scale which is crucial for distance-based and optimization-based models.

- **3. Features (PCA):** This step performs Principal Component Analysis to reduce the dimensionality of the data, retaining 95% of the explained variance to minimize noise and improve model efficiency.

- **4. Rebalancing (SMOTE):** This step addresses potential class imbalance by generating synthetic samples for the minority classes using k-nearest neighbors (k=5), resulting in a more balanced dataset for training.

- **5. Classification (Neural Network):** This final step utilizes a Multi-layer Perceptron (MLP) as the classifier, configured with specific hidden layer architectures ([10] or [20] neurons), a regularization strength (alpha=0.001), and a training iteration limit (max_iter=300).

### Summary of Pipeline Design

- **Objective:** The goal was to construct a robust machine learning pipeline for the HAR dataset, adhering to a predefined sequence of steps: Imputation, Normalization, Feature Selection (PCA), Data Rebalancing (SMOTE), and Classification (Neural Network).

- **Implementation Strategy:** 
    - **Consistency:** The primary challenge was integrating `SMOTE` into a standard `scikit-learn` pipeline. To ensure the pipeline remains valid and executable, I utilized `imblearn.pipeline.Pipeline`, which seamlessly handles the rebalancing step.
    - **Hyperparameter Flexibility:** The `train_model` function was designed with a modular signature, allowing for dynamic assignment of hyperparameters such as `hidden_layer_sizes` and `n_components` without hardcoding them inside the function.

- **Design Choices:**
    - **Pipeline Order:** Each step was mapped exactly to the user's constraints to ensure the data processing follows the logical flow from raw numerical features to a trained Multi-layer Perceptron.
    - **Simplicity:** By returning the fitted pipeline object, the design choice prioritizes usability, allowing the user to seamlessly use the `predict()` method after calling `train_model`.