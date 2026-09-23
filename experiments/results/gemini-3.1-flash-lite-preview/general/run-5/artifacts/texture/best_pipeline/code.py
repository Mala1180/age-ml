# **Created at:** 2026-09-22 13:16:31 UTC

from sklearn.pipeline import Pipeline
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPClassifier

def train_model(X_train, y_train, max_iter, hidden_layer_sizes, alpha):
    pipeline = Pipeline([
        ('imputation', IterativeImputer()),
        ('normalization', StandardScaler()),
        ('classification', MLPClassifier(max_iter=max_iter, hidden_layer_sizes=hidden_layer_sizes, alpha=alpha))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

