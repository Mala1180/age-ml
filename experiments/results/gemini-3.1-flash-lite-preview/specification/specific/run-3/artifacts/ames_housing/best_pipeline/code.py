# **Created at:** 2026-09-21 05:36:07 UTC

import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.feature_selection import SelectKBest, f_regression
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder

def train_model(X_train, y_train, k, n_estimators, max_depth):
    numeric_features = X_train.select_dtypes(include=['int64', 'float64']).columns
    categorical_features = X_train.select_dtypes(include=['object']).columns
    numeric_transformer = SimpleImputer(strategy='median')
    categorical_transformer = Pipeline(steps=[('imputer', SimpleImputer(strategy='constant', fill_value='missing')), ('onehot', OneHotEncoder(handle_unknown='ignore'))])
    preprocessor = ColumnTransformer(transformers=[('num', numeric_transformer, numeric_features), ('cat', categorical_transformer, categorical_features)])
    pipeline = Pipeline(steps=[('preprocessor', preprocessor), ('features', SelectKBest(score_func=f_regression, k=k)), ('regression', RandomForestRegressor(n_estimators=n_estimators, max_depth=max_depth, random_state=42))])
    pipeline.fit(X_train, y_train)
    return pipeline

