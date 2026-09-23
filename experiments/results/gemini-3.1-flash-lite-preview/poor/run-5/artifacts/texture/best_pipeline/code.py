# **Created at:** 2026-09-21 18:29:24 UTC

from sklearn.preprocessing import KBinsDiscretizer, StandardScaler
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline

def train_model(X_train, y_train, n_bins, encode, discretization_strategy, hidden_layer_sizes, alpha, max_iter):
    pipeline = Pipeline([
        ('discretization', KBinsDiscretizer(n_bins=n_bins, encode=encode, strategy=discretization_strategy)),
        ('normalization', StandardScaler(with_mean=False)),
        ('classification', MLPClassifier(hidden_layer_sizes=hidden_layer_sizes, alpha=alpha, max_iter=max_iter))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

