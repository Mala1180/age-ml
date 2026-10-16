> **Created at:** 2026-09-20 17:56:55 UTC

 ## Pipeline 3

1. **imputation** with `iterative_imputer`
2. **normalization** with `power_transformer`
3. **rebalancing** with `near_miss`
4. **classification** with `knn`

The machine learning pipeline consists of the following four steps: 

1. **Imputation**: Utilizes the `IterativeImputer` to handle missing data by modeling each feature as a function of other features, with a maximum of 10 iterations (`max_iter=10`). 

2. **Normalization**: Applies the `PowerTransformer` using the 'yeo-johnson' method to stabilize variance and make the data more Gaussian-like. 

3. **Rebalancing**: Employs `NearMiss` (version 1) to perform undersampling of the majority class, effectively balancing the dataset for classification. 

4. **Classification**: Implements a `KNeighborsClassifier` (KNN) with hyperparameter options for the number of neighbors (5 or 11) and weighting strategies ('uniform' or 'distance') to perform the final predictive task.

### Summary of Pipeline Development

The development process focused on constructing a robust machine learning pipeline for classification tasks involving feature imputation, distribution transformation, class balancing, and prediction. 

**Key Design Choices:**
* **Pipeline Framework:** The choice of `imblearn.pipeline.Pipeline` was critical, as it ensures that the `NearMiss` rebalancing step is only applied during the training phase, preventing data leakage into the evaluation phase.
* **Sequential Processing:** The architecture follows a strict sequence: handling missing values with `IterativeImputer`, normalizing features via `PowerTransformer` (Yeo-Johnson), addressing class imbalance through `NearMiss` undersampling, and final prediction using `KNeighborsClassifier`.

**Challenges and Resolution:**
* The initial prompt required specific steps which posed potential compatibility issues between standard `sklearn` pipes and undersampling techniques. Using the `imblearn` implementation resolved these constraints, ensuring the function signature was met while maintaining full pipeline integrity.