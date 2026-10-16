# **Created at:** 2026-09-18 07:27:10 UTC

import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import KBinsDiscretizer, StandardScaler
from sklearn.neural_network import MLPClassifier

def train_model(X_train, y_train, imputation_strategy, n_bins, encode, discretization_strategy, hidden_layer_sizes, alpha, max_iter):
    pipeline = Pipeline([
        ('imputation', SimpleImputer(strategy=imputation_strategy)),
        ('discretization', KBinsDiscretizer(n_bins=n_bins, encode=encode, strategy=discretization_strategy)),
        ('normalization', StandardScaler(with_mean=False)),
        ('classification', MLPClassifier(hidden_layer_sizes=hidden_layer_sizes, alpha=alpha, max_iter=max_iter, random_state=42))
    ])
    
    pipeline.fit(X_train, y_train)
    return pipeline

