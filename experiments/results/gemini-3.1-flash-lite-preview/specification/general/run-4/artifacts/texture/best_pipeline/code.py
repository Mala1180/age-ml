# **Created at:** 2026-09-21 10:39:34 UTC

from sklearn.preprocessing import PowerTransformer
from imblearn.under_sampling import NearMiss
from sklearn.neural_network import MLPClassifier
from imblearn.pipeline import Pipeline

def train_model(X_train, y_train, method, version, hidden_layer_sizes, alpha, max_iter):
    pipeline = Pipeline([
        ('normalization', PowerTransformer(method=method)),
        ('rebalancing', NearMiss(version=version)),
        ('classification', MLPClassifier(hidden_layer_sizes=hidden_layer_sizes, alpha=alpha, max_iter=max_iter, random_state=42))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

