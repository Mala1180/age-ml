# **Created at:** 2026-09-18 06:35:07 UTC

import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import KBinsDiscretizer, StandardScaler
from sklearn.neighbors import KNeighborsClassifier
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline

def train_model(X_train, y_train, max_iter, n_bins, encode, discretization_strategy, k_neighbors, n_neighbors, weights):
    pipeline = ImbPipeline([
        ('imputation', IterativeImputer(max_iter=max_iter)),
        ('discretization', KBinsDiscretizer(n_bins=n_bins, encode=encode, strategy=discretization_strategy)),
        ('normalization', StandardScaler()),
        ('rebalancing', SMOTE(k_neighbors=k_neighbors)),
        ('classification', KNeighborsClassifier(n_neighbors=n_neighbors, weights=weights))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

