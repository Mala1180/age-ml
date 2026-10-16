# **Created at:** 2026-09-20 14:18:55 UTC

import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import KBinsDiscretizer, MinMaxScaler
from sklearn.decomposition import PCA
from sklearn.neighbors import KNeighborsClassifier

def train_model(X_train, y_train, n_bins, encode, discretization_strategy, feature_range, n_components, n_neighbors, weights):
    pipeline = Pipeline([
        ('discretization', KBinsDiscretizer(n_bins=n_bins, encode=encode, strategy=discretization_strategy)),
        ('normalization', MinMaxScaler(feature_range=tuple(feature_range))),
        ('features', PCA(n_components=n_components)),
        ('classification', KNeighborsClassifier(n_neighbors=n_neighbors, weights=weights))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

