# **Created at:** 2026-09-17 19:14:45 UTC

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PowerTransformer
from sklearn.neighbors import KNeighborsClassifier

def train_model(X_train, y_train, method, n_neighbors, weights):
    pipeline = Pipeline([
        ('normalization', PowerTransformer(method=method)),
        ('classification', KNeighborsClassifier(n_neighbors=n_neighbors, weights=weights))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

