# **Created at:** 2026-09-17 19:52:30 UTC

from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import MinMaxScaler
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline

def train_model(X_train, y_train, max_iter, feature_range, hidden_layer_sizes, alpha):
    pipeline = Pipeline([
        ('imputer', IterativeImputer(max_iter=max_iter)),
        ('scaler', MinMaxScaler(feature_range=tuple(feature_range))),
        ('classifier', MLPClassifier(hidden_layer_sizes=hidden_layer_sizes, alpha=alpha, max_iter=max_iter))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

