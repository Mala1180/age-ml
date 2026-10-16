# **Created at:** 2026-09-22 12:58:38 UTC

import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.feature_selection import SelectKBest, f_regression
from sklearn.ensemble import RandomForestRegressor
from sklearn.compose import ColumnTransformer

def train_model(X_train, y_train, imputation_strategy, k, n_estimators, max_depth):
    numeric_features = X_train.select_dtypes(include=['int64', 'float64']).columns
    numeric_transformer = Pipeline(steps=[('imputer', SimpleImputer(strategy=imputation_strategy))])
    preprocessor = ColumnTransformer(transformers=[('num', numeric_transformer, numeric_features)])
    pipeline = Pipeline(steps=[('preprocessor', preprocessor), ('features', SelectKBest(score_func=f_regression, k=k)), ('regression', RandomForestRegressor(n_estimators=n_estimators, max_depth=max_depth, random_state=42))])
    pipeline.fit(X_train, y_train)
    return pipeline

