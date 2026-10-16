# **Created at:** 2026-09-20 22:52:56 UTC

import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import PowerTransformer, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.decomposition import PCA
from sklearn.linear_model import ElasticNet

def train_model(X_train, y_train, max_iter, method, n_components, alpha, l1_ratio):
    numeric_features = X_train.select_dtypes(include=['int64', 'float64']).columns
    categorical_features = X_train.select_dtypes(include=['object']).columns
    preprocessor = ColumnTransformer(transformers=[
        ('num', 'passthrough', numeric_features),
        ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), categorical_features)
    ])
    pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('imputation', IterativeImputer(max_iter=max_iter, random_state=42)),
        ('normalization', PowerTransformer(method=method)),
        ('features', PCA(n_components=n_components)),
        ('regression', ElasticNet(alpha=alpha, l1_ratio=l1_ratio))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

