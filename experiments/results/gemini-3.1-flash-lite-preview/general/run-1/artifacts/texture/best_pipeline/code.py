# **Created at:** 2026-09-17 23:23:25 UTC

from sklearn.impute import SimpleImputer
from sklearn.preprocessing import RobustScaler
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline
from sklearn.neural_network import MLPClassifier

def train_model(X_train, y_train, imputation_strategy, quantile_range, k_neighbors, hidden_layer_sizes, alpha, max_iter):
    pipeline = Pipeline([
        ('imputation', SimpleImputer(strategy=imputation_strategy)),
        ('normalization', RobustScaler(quantile_range=tuple(quantile_range))),
        ('rebalancing', SMOTE(k_neighbors=k_neighbors)),
        ('classification', MLPClassifier(hidden_layer_sizes=hidden_layer_sizes, alpha=alpha, max_iter=max_iter, random_state=42))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

