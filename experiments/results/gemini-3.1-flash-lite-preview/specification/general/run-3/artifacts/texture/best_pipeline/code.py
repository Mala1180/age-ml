# **Created at:** 2026-09-21 00:16:45 UTC

from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import StandardScaler
from imblearn.under_sampling import NearMiss
from sklearn.neural_network import MLPClassifier
from imblearn.pipeline import Pipeline

def train_model(X_train, y_train, max_iter, version, hidden_layer_sizes, alpha):
    pipeline = Pipeline([
        ('imputation', IterativeImputer(max_iter=max_iter, random_state=version)),
        ('normalization', StandardScaler()),
        ('rebalancing', NearMiss()),
        ('classification', MLPClassifier(hidden_layer_sizes=hidden_layer_sizes, alpha=alpha, max_iter=max_iter, random_state=version))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

