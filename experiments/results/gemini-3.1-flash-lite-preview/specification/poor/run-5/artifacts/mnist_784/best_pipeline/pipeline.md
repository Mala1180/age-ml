> **Created at:** 2026-09-22 11:15:54 UTC

 ## Pipeline 14

1. **imputation** with `simple_imputer`
2. **discretization** with `kbins`
3. **normalization** with `standard`
4. **rebalancing** with `near_miss`
5. **classification** with `random_forest`

The machine learning pipeline consists of five sequential steps designed to preprocess data and perform classification:

1. **Imputation (Simple Imputer):** This step handles missing values by replacing them using the 'mean' or 'median' of each column.
2. **Discretization (KBins Discretizer):** This step transforms continuous features into discrete categories using quantile-based binning with 10 ordinal intervals.
3. **Normalization (Standard Scaler):** This step standardizes the features by removing the mean and scaling to unit variance.
4. **Rebalancing (NearMiss):** This step addresses class imbalance by using the NearMiss undersampling algorithm to select representative samples from the majority class.
5. **Classification (Random Forest):** This final step trains a Random Forest model, using either a deep or unrestricted tree structure, to predict the target class.

### Summary of Pipeline Development

- **Objective:** The goal was to construct a robust machine learning pipeline for the MNIST dataset using five specific steps: imputation, discretization, normalization, rebalancing, and classification.
- **Design Choices:** I utilized `imblearn.pipeline.Pipeline` to ensure that the `NearMiss` rebalancing step could be integrated seamlessly with standard `scikit-learn` transformers and the `RandomForestClassifier`. This was crucial because standard `scikit-learn` pipelines do not support undersampling.
- **Implementation Challenges:** 
  - Initial attempts failed due to formatting issues, specifically the use of semicolons and compressed one-line code blocks that caused `SyntaxError` during execution.
  - These problems were resolved by adopting a cleaner, PEP 8-compliant structure with proper line breaks and indentation.
- **Final Result:** The current version provides a modular, functional, and executable `train_model` function that maps hyperparameters directly to each pipeline component.