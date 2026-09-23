# **Created at:** 2026-09-20 19:26:35 UTC

from sklearn.pipeline import Pipeline
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.neural_network import MLPClassifier

def train_model(X_train, y_train, max_iter, hidden_layer_sizes, alpha):
    pipeline = Pipeline([
        ('imputation', IterativeImputer(random_state=42)),
        ('classification', MLPClassifier(max_iter=max_iter, hidden_layer_sizes=hidden_layer_sizes, alpha=alpha, random_state=42))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

