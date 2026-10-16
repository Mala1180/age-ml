# **Created at:** 2026-09-21 00:52:07 UTC

import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import MinMaxScaler
from sklearn.neural_network import MLPClassifier
from imblearn.pipeline import Pipeline as ImbPipeline
from imblearn.over_sampling import SMOTE

def train_model(X_train, y_train, imputation_strategy, feature_range, k_neighbors, hidden_layer_sizes, alpha, max_iter):
    steps = [
        ('imputation', SimpleImputer(strategy=imputation_strategy)),
        ('normalization', MinMaxScaler(feature_range=tuple(feature_range))),
        ('rebalancing', SMOTE(k_neighbors=k_neighbors)),
        ('classification', MLPClassifier(hidden_layer_sizes=hidden_layer_sizes, alpha=alpha, max_iter=max_iter, random_state=42))
    ]
    pipeline = ImbPipeline(steps)
    pipeline.fit(X_train, y_train)
    return pipeline

