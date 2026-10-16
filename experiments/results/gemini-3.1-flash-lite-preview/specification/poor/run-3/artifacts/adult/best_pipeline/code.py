# **Created at:** 2026-09-20 20:36:20 UTC

import pandas as pd
import numpy as np
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import AdaBoostClassifier
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline

def train_model(X_train, y_train, max_iter, k_neighbors, n_estimators, learning_rate):
    numeric_features = X_train.select_dtypes(include=['int64', 'float64']).columns
    categorical_features = X_train.select_dtypes(include=['object', 'category']).columns
    preprocessor = ColumnTransformer(
        transformers=[('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), categorical_features)],
        remainder='passthrough'
    )
    steps = [
        ('preprocessor', preprocessor),
        ('imputer', IterativeImputer(max_iter=max_iter)),
        ('smote', SMOTE(k_neighbors=k_neighbors)),
        ('ada_boost', AdaBoostClassifier(n_estimators=n_estimators, learning_rate=learning_rate))
    ]
    model = Pipeline(steps)
    model.fit(X_train, y_train)
    return model

