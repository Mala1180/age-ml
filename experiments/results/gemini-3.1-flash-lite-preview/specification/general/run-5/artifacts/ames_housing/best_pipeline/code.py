# **Created at:** 2026-09-23 14:44:22 UTC

import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import KBinsDiscretizer
from sklearn.ensemble import RandomForestRegressor
from sklearn.compose import ColumnTransformer

def train_model(X_train, y_train, imputation_strategy, n_bins, encode, discretization_strategy, n_estimators, max_depth):
    numeric_features = X_train.select_dtypes(include=['int64', 'float64']).columns
    
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', SimpleImputer(strategy=imputation_strategy), numeric_features)
        ],
        remainder='drop'
    )

    pipeline = Pipeline([
        ('imputation', preprocessor),
        ('discretization', KBinsDiscretizer(n_bins=n_bins, encode=encode, strategy=discretization_strategy)),
        ('regression', RandomForestRegressor(n_estimators=n_estimators, max_depth=max_depth, random_state=42))
    ])

    pipeline.fit(X_train, y_train)
    return pipeline

