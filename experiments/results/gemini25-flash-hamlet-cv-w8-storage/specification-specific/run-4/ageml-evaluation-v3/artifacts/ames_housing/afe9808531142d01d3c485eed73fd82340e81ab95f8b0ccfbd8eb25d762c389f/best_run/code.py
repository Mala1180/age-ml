import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder
from sklearn.feature_selection import SelectKBest, f_regression
from sklearn.ensemble import RandomForestRegressor
import numpy as np

def build_model(X_train, y_train, imputation_strategy, k, n_estimators, max_depth):
    # Identify numerical and categorical features
    numerical_features = X_train.select_dtypes(include=np.number).columns
    categorical_features = X_train.select_dtypes(include='object').columns

    # Create a pipeline for numerical features
    numerical_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy=imputation_strategy))
    ])

    # Create a pipeline for categorical features
    categorical_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='most_frequent')), # Impute missing categorical values
        ('onehot', OneHotEncoder(handle_unknown='ignore')) # One-hot encode categorical features
    ])

    # Create a preprocessor using ColumnTransformer
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numerical_transformer, numerical_features),
            ('cat', categorical_transformer, categorical_features)
        ],
        remainder='passthrough' # Keep other columns (if any)
    )

    # Feature selection
    # For regression, f_regression is a common choice for SelectKBest
    feature_selector = SelectKBest(score_func=f_regression, k=k)

    # Regression model
    regressor = RandomForestRegressor(n_estimators=n_estimators, max_depth=max_depth, random_state=42)

    # Create the full pipeline
    pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('feature_selection', feature_selector),
        ('regressor', regressor)
    ])

    return pipeline
