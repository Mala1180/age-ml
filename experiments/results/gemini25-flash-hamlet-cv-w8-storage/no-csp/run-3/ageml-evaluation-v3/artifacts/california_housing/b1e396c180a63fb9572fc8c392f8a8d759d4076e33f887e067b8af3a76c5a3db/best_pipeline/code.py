import pandas as pd
import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder
from sklearn.feature_selection import SelectKBest, f_regression
from sklearn.ensemble import RandomForestRegressor

def build_model(X_train, y_train, imputation_strategy, k, n_estimators, max_depth):
    # Identify numerical and categorical features
    numerical_features = X_train.select_dtypes(include=np.number).columns.tolist()
    categorical_features = X_train.select_dtypes(include='object').columns.tolist()

    # Create a preprocessor to handle different column types
    # Numerical features: Impute missing values
    # Categorical features: One-hot encode (assuming no missing values based on dataset info, but good practice to include imputer if needed)
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', SimpleImputer(strategy=imputation_strategy), numerical_features),
            ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_features)
        ],
        remainder='passthrough' # Keep any other columns not explicitly transformed
    )

    # Create the full pipeline
    pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('selector', SelectKBest(score_func=f_regression, k=k)),
        ('regressor', RandomForestRegressor(n_estimators=n_estimators, max_depth=max_depth, random_state=42))
    ])

    return pipeline
