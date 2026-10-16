# **Created at:** 2026-10-16 11:06:12 UTC

import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import KBinsDiscretizer, PowerTransformer
from sklearn.decomposition import PCA
from sklearn.neighbors import KNeighborsClassifier

def train_model(X_train, y_train, max_iter, n_bins, encode, discretization_strategy, method, n_components, n_neighbors, weights):
    pipeline = Pipeline([
        ('imputation', IterativeImputer(max_iter=max_iter)),
        ('discretization', KBinsDiscretizer(n_bins=n_bins, encode=encode, strategy=discretization_strategy)),
        ('normalization', PowerTransformer(method=method)),
        ('features', PCA(n_components=n_components)),
        ('classification', KNeighborsClassifier(n_neighbors=n_neighbors, weights=weights))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

