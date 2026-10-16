# **Created at:** 2026-09-23 14:54:23 UTC

from sklearn.preprocessing import PowerTransformer
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline
from sklearn.neural_network import MLPClassifier

def train_model(X_train, y_train, method, k_neighbors, hidden_layer_sizes, alpha, max_iter):
    pipeline = ImbPipeline([
        ('normalization', PowerTransformer(method=method)),
        ('rebalancing', SMOTE(k_neighbors=k_neighbors)),
        ('classification', MLPClassifier(hidden_layer_sizes=hidden_layer_sizes, alpha=alpha, max_iter=max_iter))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

