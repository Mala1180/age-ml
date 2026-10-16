# **Created at:** 2026-09-18 05:26:46 UTC

from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import RobustScaler, OneHotEncoder
from sklearn.neighbors import KNeighborsClassifier
from sklearn.compose import ColumnTransformer
from imblearn.pipeline import Pipeline
from imblearn.over_sampling import SMOTE
import pandas as pd

def train_model(X_train, y_train, max_iter, quantile_range, k_neighbors, n_neighbors, weights):
    numeric_features = X_train.select_dtypes(include=['int64', 'float64']).columns
    categorical_features = X_train.select_dtypes(include=['object']).columns
    preprocessor = ColumnTransformer(transformers=[('num', 'passthrough', numeric_features), ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), categorical_features)])
    pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('imputer', IterativeImputer(max_iter=max_iter)),
        ('scaler', RobustScaler(quantile_range=tuple(quantile_range))),
        ('smote', SMOTE(k_neighbors=k_neighbors)),
        ('classifier', KNeighborsClassifier(n_neighbors=n_neighbors, weights=weights))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

