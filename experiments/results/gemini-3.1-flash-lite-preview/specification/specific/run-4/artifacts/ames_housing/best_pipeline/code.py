# **Created at:** 2026-09-21 18:15:58 UTC

from sklearn.pipeline import Pipeline
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import Ridge
import pandas as pd

def train_model(X_train, y_train, max_iter, alpha):
    numeric_features = X_train.select_dtypes(include=['int64', 'float64']).columns
    categorical_features = X_train.select_dtypes(include=['object']).columns
    preprocessor = ColumnTransformer(transformers=[
        ('num', 'passthrough', numeric_features),
        ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), categorical_features)
    ])
    pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('imputation', IterativeImputer(max_iter=max_iter, random_state=42)),
        ('normalization', StandardScaler()),
        ('regression', Ridge(alpha=alpha))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

