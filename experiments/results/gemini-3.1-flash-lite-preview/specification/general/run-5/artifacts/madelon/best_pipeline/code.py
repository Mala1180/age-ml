# **Created at:** 2026-09-22 13:37:29 UTC

from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import RobustScaler
from sklearn.feature_selection import SelectKBest
from sklearn.neighbors import KNeighborsClassifier

def train_model(X_train, y_train, imputation_strategy, quantile_range, k, n_neighbors, weights):
    pipeline = Pipeline([
        ('imputation', SimpleImputer(strategy=imputation_strategy)),
        ('normalization', RobustScaler(quantile_range=tuple(quantile_range))),
        ('features', SelectKBest(k=k)),
        ('classification', KNeighborsClassifier(n_neighbors=n_neighbors, weights=weights))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

