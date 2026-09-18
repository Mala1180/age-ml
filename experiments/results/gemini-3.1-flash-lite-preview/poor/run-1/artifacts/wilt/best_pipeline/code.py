# **Created at:** 2026-09-17 19:11:22 UTC

import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import KBinsDiscretizer
from imblearn.pipeline import Pipeline as ImbPipeline
from imblearn.over_sampling import SMOTE
from sklearn.neural_network import MLPClassifier

def train_model(X_train, y_train, max_iter, n_bins, encode, discretization_strategy, k_neighbors, hidden_layer_sizes, alpha):
    pipeline = ImbPipeline([
        ('imputation', IterativeImputer(max_iter=max_iter)),
        ('discretization', KBinsDiscretizer(n_bins=n_bins, encode=encode, strategy=discretization_strategy)),
        ('rebalancing', SMOTE(k_neighbors=k_neighbors)),
        ('classification', MLPClassifier(hidden_layer_sizes=hidden_layer_sizes, alpha=alpha, max_iter=1000))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

