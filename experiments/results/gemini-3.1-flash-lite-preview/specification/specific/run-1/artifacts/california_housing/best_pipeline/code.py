# **Created at:** 2026-09-18 06:22:54 UTC

import pandas as pd
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import RobustScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.neighbors import KNeighborsRegressor
from sklearn.pipeline import Pipeline

def train_model(X_train, y_train, max_iter, quantile_range, n_neighbors, weights):
    numeric_cols = X_train.select_dtypes(include=['number']).columns.tolist()
    categorical_cols = X_train.select_dtypes(exclude=['number']).columns.tolist()
    preprocessor = ColumnTransformer([
        ('num', 'passthrough', numeric_cols),
        ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_cols)
    ])
    pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('imputation', IterativeImputer(max_iter=max_iter, random_state=42)),
        ('normalization', RobustScaler(quantile_range=tuple(quantile_range))),
        ('regression', KNeighborsRegressor(n_neighbors=n_neighbors, weights=weights))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

