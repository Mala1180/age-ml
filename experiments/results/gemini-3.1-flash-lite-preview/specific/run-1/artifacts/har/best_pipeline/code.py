# **Created at:** 2026-09-18 05:04:30 UTC

from sklearn.preprocessing import PowerTransformer
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline

def train_model(X_train, y_train, method, hidden_layer_sizes, alpha, max_iter):
    pipeline = Pipeline(steps=[
        ('normalization', PowerTransformer(method=method)),
        ('classification', MLPClassifier(hidden_layer_sizes=hidden_layer_sizes, alpha=alpha, max_iter=max_iter))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

