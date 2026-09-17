# **Created at:** 2026-04-23 15:14:19 UTC

import pandas as pd
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import RobustScaler
from sklearn.neural_network import MLPClassifier
from imblearn.pipeline import Pipeline as ImbPipeline
from imblearn.over_sampling import SMOTE

def train_model(X_train, y_train, max_iter, quantile_range, k_neighbors, hidden_layer_sizes, alpha):
    pipeline = ImbPipeline([
        ('imputation', IterativeImputer(max_iter=max_iter)),
        ('normalization', RobustScaler(quantile_range=tuple(quantile_range))),
        ('rebalancing', SMOTE(k_neighbors=k_neighbors)),
        ('classification', MLPClassifier(hidden_layer_sizes=hidden_layer_sizes, alpha=alpha, max_iter=1000))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

