# **Created at:** 2026-09-18 05:00:11 UTC

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import RobustScaler
from sklearn.neural_network import MLPClassifier

def train_model(X_train, y_train, quantile_range, hidden_layer_sizes, alpha, max_iter):
    pipeline = Pipeline([
        ('normalization', RobustScaler(quantile_range=tuple(quantile_range))),
        ('classification', MLPClassifier(hidden_layer_sizes=hidden_layer_sizes, alpha=alpha, max_iter=max_iter, random_state=42))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

