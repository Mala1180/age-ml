# **Created at:** 2026-09-21 00:24:49 UTC

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PowerTransformer
from sklearn.feature_selection import SelectKBest
from sklearn.neighbors import KNeighborsClassifier

def train_model(X_train, y_train, method, k, n_neighbors, weights):
    pipeline = Pipeline([
        ('normalization', PowerTransformer(method=method)),
        ('features', SelectKBest(k=k)),
        ('classification', KNeighborsClassifier(n_neighbors=n_neighbors, weights=weights))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

