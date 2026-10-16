# **Created at:** 2026-09-23 12:48:53 UTC

import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import KBinsDiscretizer, PowerTransformer
from sklearn.decomposition import PCA
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from imblearn.pipeline import Pipeline as ImbPipeline
from imblearn.over_sampling import SMOTE

def train_model(X_train, y_train, imputation_strategy, n_bins, encode, discretization_strategy, method, n_components, k_neighbors, n_neighbors, weights):
    pipeline = ImbPipeline([
        ('imputation', SimpleImputer(strategy=imputation_strategy)),
        ('discretization', KBinsDiscretizer(n_bins=n_bins, encode=encode, strategy=discretization_strategy)),
        ('normalization', PowerTransformer(method=method)),
        ('features', PCA(n_components=n_components)),
        ('rebalancing', SMOTE(k_neighbors=k_neighbors)),
        ('classification', KNeighborsClassifier(n_neighbors=n_neighbors, weights=weights))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

