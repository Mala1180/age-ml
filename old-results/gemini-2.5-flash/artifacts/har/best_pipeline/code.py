# **Created at:** 2026-04-23 19:27:56 UTC

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPClassifier

def train_model(X_train, y_train, hidden_layer_sizes, alpha, max_iter):
    pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('nn', MLPClassifier(hidden_layer_sizes=hidden_layer_sizes, alpha=alpha, max_iter=max_iter, random_state=42))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

