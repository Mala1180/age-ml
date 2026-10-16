# **Created at:** 2026-09-18 04:52:46 UTC

import pandas as pd
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import ElasticNet
from sklearn.pipeline import Pipeline

def train_model(X_train, y_train, max_iter, alpha, l1_ratio):
    numeric_features = X_train.select_dtypes(include=['int64', 'float64']).columns
    categorical_features = X_train.select_dtypes(include=['object']).columns
    preprocessor = ColumnTransformer([
        ('num', 'passthrough', numeric_features),
        ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), categorical_features)
    ])
    pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('imputer', IterativeImputer(max_iter=max_iter, random_state=42)),
        ('scaler', StandardScaler()),
        ('regressor', ElasticNet(alpha=alpha, l1_ratio=l1_ratio, max_iter=max_iter))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

