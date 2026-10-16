# **Created at:** 2026-09-19 02:45:03 UTC

import numpy as np
import pandas as pd
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import MinMaxScaler, OrdinalEncoder
from sklearn.compose import ColumnTransformer
from sklearn.neural_network import MLPClassifier
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline

def train_model(X_train, y_train, max_iter, feature_range, k_neighbors, hidden_layer_sizes, alpha):
    categorical_cols = X_train.select_dtypes(include=['object']).columns
    numeric_cols = X_train.select_dtypes(include=[np.number]).columns
    preprocessor = ColumnTransformer([
        ('cat', OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=-1), categorical_cols)
    ], remainder='passthrough')
    pipe = Pipeline([
        ('preprocessor', preprocessor),
        ('imputer', IterativeImputer(max_iter=max_iter)),
        ('scaler', MinMaxScaler(feature_range=tuple(feature_range))),
        ('smote', SMOTE(k_neighbors=k_neighbors)),
        ('nn', MLPClassifier(hidden_layer_sizes=hidden_layer_sizes, alpha=alpha, max_iter=max_iter))
    ])
    pipe.fit(X_train, y_train)
    return pipe

