# **Created at:** 2026-04-23 19:09:59 UTC

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PowerTransformer
from sklearn.neural_network import MLPClassifier

def train_model(X_train, y_train, method, hidden_layer_sizes, alpha, max_iter):
    pipeline = Pipeline([
        ('power_transformer', PowerTransformer()),
        ('nn', MLPClassifier(hidden_layer_sizes=hidden_layer_sizes, alpha=alpha, max_iter=max_iter, random_state=42))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

