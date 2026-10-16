# **Created at:** 2026-09-22 13:03:57 UTC

import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import PowerTransformer, OneHotEncoder
from sklearn.feature_selection import SelectKBest, f_regression
from sklearn.ensemble import RandomForestRegressor
from sklearn.compose import ColumnTransformer

def train_model(X_train, y_train, max_iter, method, k, n_estimators, max_depth):
    numeric_features = X_train.select_dtypes(include=['number']).columns
    categorical_features = X_train.select_dtypes(exclude=['number']).columns
    preprocessor = ColumnTransformer(transformers=[
        ('num', 'passthrough', numeric_features),
        ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), categorical_features)
    ])
    pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('imputation', IterativeImputer(max_iter=max_iter, initial_strategy='mean')),
        ('normalization', PowerTransformer(method=method)),
        ('features', SelectKBest(score_func=f_regression, k=k)),
        ('regression', RandomForestRegressor(n_estimators=n_estimators, max_depth=max_depth, random_state=42))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

