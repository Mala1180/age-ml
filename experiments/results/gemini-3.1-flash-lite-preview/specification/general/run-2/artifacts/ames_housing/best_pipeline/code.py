# **Created at:** 2026-09-20 16:24:23 UTC

import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import PowerTransformer
from sklearn.feature_selection import SelectKBest, f_regression
from sklearn.neighbors import KNeighborsRegressor
from sklearn.compose import ColumnTransformer

def train_model(X_train, y_train, imputation_strategy, method, k, n_neighbors, weights):
    numeric_features = X_train.select_dtypes(include=['int64', 'float64']).columns
    preprocessor = ColumnTransformer(transformers=[('num', SimpleImputer(strategy=imputation_strategy), numeric_features)], remainder='drop')
    pipeline = Pipeline(steps=[
        ('imputer', preprocessor),
        ('scaler', PowerTransformer(method=method)),
        ('selector', SelectKBest(score_func=f_regression, k=k)),
        ('regressor', KNeighborsRegressor(n_neighbors=n_neighbors, weights=weights))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

