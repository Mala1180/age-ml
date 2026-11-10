> **Created at:** 2026-11-09 19:05:25 UTC

 ## Pipeline 18

1. **imputation** with `simple_imputer`
2. **features** with `select_k_best`
3. **rebalancing** with `near_miss`
4. **classification** with `knn`

### Machine Learning Pipeline Explanation

1. **Imputation (Simple Imputer)**: This step handles missing values in the dataset by replacing them with either the mean or median of the respective feature columns.

2. **Features (Select K Best)**: This step performs feature selection by retaining the top 'k' features (specifically 5 or 10) based on their univariate statistical scores using the ANOVA F-value.

3. **Rebalancing (Near Miss)**: This step addresses class imbalance by undersampling the majority class using the NearMiss algorithm (version 1) to ensure a more balanced training set.

4. **Classification (KNN)**: This final step implements the K-Nearest Neighbors algorithm, classifying data points based on the majority vote or distance-weighted influence of the 5 or 11 nearest neighbors.

### Summary of Pipeline Development

*   **Design Choices**: The pipeline was designed to handle data preprocessing, feature selection, class imbalance, and classification sequentially. We utilized `SimpleImputer` for missing data, `SelectKBest` for dimensionality reduction, `NearMiss` for undersampling, and `KNeighborsClassifier` for prediction. To ensure compatibility between undersampling and the rest of the workflow, the `imblearn.pipeline.Pipeline` class was selected.

*   **Challenges Encountered**: Initial attempts to provide the code in a single-line format caused syntax errors during execution in the user's environment. The final solution resolved this by providing the code in a standard, multi-line Python format with proper indentation and clear import statements, ensuring both readability and execution stability.