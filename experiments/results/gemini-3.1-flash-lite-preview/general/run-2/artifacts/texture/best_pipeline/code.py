# **Created at:** 2026-09-18 18:08:40 UTC

from sklearn.pipeline import Pipeline
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import RobustScaler
from sklearn.neural_network import MLPClassifier

def train_model(X_train, y_train, max_iter, quantile_range, hidden_layer_sizes, alpha):
    pipeline = Pipeline([
        ('imputation', IterativeImputer(max_iter=max_iter)),
        ('normalization', RobustScaler(quantile_range=tuple(quantile_range))),
        ('classification', MLPClassifier(hidden_layer_sizes=hidden_layer_sizes, alpha=alpha, max_iter=1000))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

