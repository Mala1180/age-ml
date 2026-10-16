# **Created at:** 2026-09-18 04:58:11 UTC

from sklearn.preprocessing import RobustScaler
from imblearn.over_sampling import SMOTE
from sklearn.neural_network import MLPClassifier
from imblearn.pipeline import Pipeline

def train_model(X_train, y_train, quantile_range, k_neighbors, hidden_layer_sizes, alpha, max_iter):
    scaler = RobustScaler(quantile_range=tuple(quantile_range))
    smote = SMOTE(k_neighbors=k_neighbors)
    clf = MLPClassifier(hidden_layer_sizes=hidden_layer_sizes, alpha=alpha, max_iter=max_iter)
    pipeline = Pipeline([
        ('normalization', scaler),
        ('rebalancing', smote),
        ('classification', clf)
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

