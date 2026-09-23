# **Created at:** 2026-09-21 07:51:42 UTC

import pandas as pd
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import RobustScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.neural_network import MLPClassifier
from imblearn.pipeline import Pipeline as ImbPipeline
from imblearn.over_sampling import SMOTE

def train_model(X_train, y_train, max_iter, quantile_range, k_neighbors, hidden_layer_sizes, alpha):
    cat_cols = X_train.select_dtypes(include=['object', 'category']).columns
    num_cols = X_train.select_dtypes(include=['number']).columns
    preprocessor = ColumnTransformer(transformers=[('num', 'passthrough', num_cols), ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), cat_cols)])
    pipeline = ImbPipeline(steps=[
        ('preprocessor', preprocessor),
        ('imputation', IterativeImputer(max_iter=max_iter)),
        ('normalization', RobustScaler(quantile_range=tuple(quantile_range))),
        ('rebalancing', SMOTE(k_neighbors=k_neighbors)),
        ('classification', MLPClassifier(hidden_layer_sizes=hidden_layer_sizes, alpha=alpha, max_iter=max_iter))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

