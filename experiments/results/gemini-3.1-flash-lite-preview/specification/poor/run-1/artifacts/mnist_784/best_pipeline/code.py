# **Created at:** 2026-09-17 21:09:08 UTC

from sklearn.impute import SimpleImputer
from sklearn.preprocessing import Binarizer
from sklearn.decomposition import PCA
from imblearn.under_sampling import NearMiss
from sklearn.neighbors import KNeighborsClassifier
from imblearn.pipeline import Pipeline

def train_model(X_train, y_train, imputation_strategy, threshold, n_components, version, n_neighbors, weights):
    pipeline = Pipeline([
        ('imputation', SimpleImputer(strategy=imputation_strategy)),
        ('discretization', Binarizer(threshold=threshold)),
        ('features', PCA(n_components=n_components)),
        ('rebalancing', NearMiss(version=version)),
        ('classification', KNeighborsClassifier(n_neighbors=n_neighbors, weights=weights))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

