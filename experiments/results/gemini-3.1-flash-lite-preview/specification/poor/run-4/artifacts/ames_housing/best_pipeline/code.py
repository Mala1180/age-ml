# **Created at:** 2026-09-21 10:20:24 UTC

import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.feature_selection import SelectKBest, f_regression
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import OrdinalEncoder
from sklearn.compose import ColumnTransformer

def train_model(X_train, y_train, max_iter, k, n_estimators, max_depth):
    categorical_cols = X_train.select_dtypes(include=['object']).columns
    numeric_cols = X_train.select_dtypes(include=['number']).columns
    
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', 'passthrough', numeric_cols),
            ('cat', OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=-1), categorical_cols)
        ]
    )
    
    pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('imputer', IterativeImputer(max_iter=max_iter)),
        ('features', SelectKBest(score_func=f_regression, k=k)),
        ('regression', RandomForestRegressor(n_estimators=n_estimators, max_depth=max_depth, random_state=42))
    ])
    
    pipeline.fit(X_train, y_train)
    return pipeline

