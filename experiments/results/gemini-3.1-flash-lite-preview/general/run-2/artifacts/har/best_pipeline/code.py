# **Created at:** 2026-09-18 18:32:09 UTC

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MinMaxScaler
from sklearn.neural_network import MLPClassifier

def train_model(X_train, y_train, feature_range, hidden_layer_sizes, alpha, max_iter):
    pipeline = Pipeline([
        ('normalization', MinMaxScaler(feature_range=tuple(feature_range))),
        ('classification', MLPClassifier(hidden_layer_sizes=hidden_layer_sizes, alpha=alpha, max_iter=max_iter))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

