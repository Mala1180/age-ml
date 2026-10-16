# **Created at:** 2026-09-21 10:03:54 UTC

import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import RobustScaler, OneHotEncoder
from sklearn.feature_selection import SelectKBest
from sklearn.ensemble import RandomForestRegressor
from sklearn.compose import ColumnTransformer

def train_model(X_train, y_train, max_iter, quantile_range, k, n_estimators, max_depth):
    numeric_features = X_train.select_dtypes(include=['int64', 'float64']).columns
    categorical_features = X_train.select_dtypes(include=['object', 'category']).columns
    preprocessor = ColumnTransformer(transformers=[('num', 'passthrough', numeric_features), ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_features)])
    pipeline = Pipeline(steps=[('preprocessor', preprocessor), ('imputation', IterativeImputer(max_iter=max_iter)), ('normalization', RobustScaler(quantile_range=tuple(quantile_range))), ('features', SelectKBest(k=k)), ('regression', RandomForestRegressor(n_estimators=n_estimators, max_depth=max_depth))])
    pipeline.fit(X_train, y_train)
    return pipeline

