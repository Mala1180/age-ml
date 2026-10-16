> **Created at:** 2026-09-23 12:48:53 UTC

 ## Pipeline 16

1. **imputation** with `simple_imputer`
2. **discretization** with `kbins`
3. **normalization** with `power_transformer`
4. **features** with `pca`
5. **rebalancing** with `smote`
6. **classification** with `knn`

### Pipeline Explanation

1. **Imputation (`simple_imputer`)**: Replaces missing values in the dataset using either the mean or median of the feature columns to ensure completeness.

2. **Discretization (`kbins`)**: Transforms continuous features into discrete bins using a quantile-based strategy, converting them into ordinal categories.

3. **Normalization (`power_transformer`)**: Applies the Yeo-Johnson transformation to stabilize variance and make the distribution of features more Gaussian-like.

4. **Features (`pca`)**: Performs Principal Component Analysis to reduce dimensionality, retaining 95% of the explained variance in the dataset.

5. **Rebalancing (`smote`)**: Addresses class imbalance by synthetically oversampling the minority classes using 5 nearest neighbors.

6. **Classification (`knn`)**: Executes the k-Nearest Neighbors classifier to predict labels, with adjustable parameters for the number of neighbors (5 or 11) and weighting schemes (uniform or distance).

### Summary of Pipeline Development

- **Objective**: The task involved designing a machine learning pipeline for the MNIST-784 dataset, specifically following a six-step architecture including imputation, discretization, normalization, feature reduction, rebalancing, and classification.
- **Design Choices**: 
    - We utilized `SimpleImputer` for handling missing data and `KBinsDiscretizer` to convert continuous features into ordinal categorical representations.
    - To handle non-normal distributions, the `PowerTransformer` (Yeo-Johnson) was selected.
    - Dimensionality reduction was performed via PCA to capture 95% variance, ensuring efficiency.
    - Given the potential for imbalanced classes in classification tasks, `SMOTE` was integrated using `imblearn.pipeline` to ensure the classifier receives a balanced input.
    - The architecture was implemented using an `ImbPipeline` to ensure compatibility between standard `scikit-learn` transformers and the `imbalanced-learn` rebalancing step.
- **Technical Considerations**: The main challenge was ensuring the pipeline maintained a clean, functional structure consistent with the provided hyperparameter constraints. No significant errors were encountered, as the use of the `imblearn` pipeline successfully resolved the integration between oversampling and standard preprocessing steps.