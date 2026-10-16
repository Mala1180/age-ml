# **Created at:** 2026-10-16 11:06:44 UTC

import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import Binarizer, PowerTransformer
from sklearn.decomposition import PCA
from sklearn.neighbors import KNeighborsClassifier
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline

def train_model(X_train, y_train, max_iter, threshold, method, n_components, k_neighbors, n_neighbors, weights):
    pipeline = ImbPipeline([
        ('imputation', IterativeImputer(max_iter=max_iter)),
        ('discretization', Binarizer(threshold=threshold)),
        ('normalization', PowerTransformer(method=method)),
        ('features', PCA(n_components=n_components)),
        ('rebalancing', SMOTE(k_neighbors=k_neighbors)),
        ('classification', KNeighborsClassifier(n_neighbors=n_neighbors, weights=weights))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

