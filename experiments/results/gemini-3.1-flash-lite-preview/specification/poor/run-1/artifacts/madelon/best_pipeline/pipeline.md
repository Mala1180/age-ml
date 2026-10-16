> **Created at:** 2026-09-17 19:19:20 UTC

 ## Pipeline 15

1. **imputation** with `simple_imputer`
2. **normalization** with `robust_scaler`
3. **features** with `select_k_best`
4. **rebalancing** with `near_miss`
5. **classification** with `random_forest`

The final machine learning pipeline is structured as follows:

1. **Imputation (SimpleImputer)**: Handles missing values by replacing them with the 'mean' or 'median' of each feature.
2. **Normalization (RobustScaler)**: Scales features using statistics that are robust to outliers, specifically defined by the [25.0, 75.0] quantile range.
3. **Features (SelectKBest)**: Performs feature selection by choosing the top 5 or 10 features based on their statistical relationship with the target.
4. **Rebalancing (NearMiss)**: Addresses class imbalance in the training data by undersampling the majority class using the specified NearMiss version.
5. **Classification (RandomForest)**: Trains a Random Forest ensemble model to predict the target class, configured with 200 trees and an optional maximum tree depth.

### Summary of Pipeline Development

- **Design Choices**: The pipeline was architected to handle data preprocessing, feature engineering, and class imbalance before classification. Key libraries used include `scikit-learn` for general modeling tasks and `imblearn` for handling the `NearMiss` undersampling technique.
- **Evolution**: The code underwent several iterations to ensure robust execution. Initial issues involved improper syntax when defining components in a single line. A significant technical hurdle occurred regarding the `RobustScaler` hyperparameter `quantile_range`, which requires a strict `tuple` type; the pipeline was updated to cast input lists to tuples to prevent execution errors.
- **Final State**: The resulting `train_model` function provides a clean, modular implementation that is compatible with scikit-learn's pipeline API, ensuring proper data transformation and model training flow.