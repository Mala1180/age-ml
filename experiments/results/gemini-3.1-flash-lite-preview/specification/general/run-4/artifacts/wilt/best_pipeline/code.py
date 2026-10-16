# **Created at:** 2026-09-21 10:34:00 UTC

from sklearn.impute import SimpleImputer
from sklearn.preprocessing import RobustScaler
from sklearn.feature_selection import SelectKBest
from imblearn.over_sampling import SMOTE
from sklearn.neural_network import MLPClassifier
from imblearn.pipeline import Pipeline

def train_model(X_train, y_train, imputation_strategy, quantile_range, k, k_neighbors, hidden_layer_sizes, alpha, max_iter):
    pipeline = Pipeline([
        ('imputation', SimpleImputer(strategy=imputation_strategy)),
        ('normalization', RobustScaler(quantile_range=tuple(quantile_range))),
        ('features', SelectKBest(k=k)),
        ('rebalancing', SMOTE(k_neighbors=k_neighbors)),
        ('classification', MLPClassifier(hidden_layer_sizes=hidden_layer_sizes, alpha=alpha, max_iter=max_iter, random_state=42))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

