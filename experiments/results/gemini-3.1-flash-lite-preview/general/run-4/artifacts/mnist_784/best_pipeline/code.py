# **Created at:** 2026-09-21 13:40:43 UTC

from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import MinMaxScaler
from sklearn.decomposition import PCA
from sklearn.neighbors import KNeighborsClassifier

def train_model(X_train, y_train, imputation_strategy, feature_range, n_components, n_neighbors, weights):
    pipeline = Pipeline([
        ('imputation', SimpleImputer(strategy=imputation_strategy)),
        ('normalization', MinMaxScaler(feature_range=tuple(feature_range))),
        ('features', PCA(n_components=n_components)),
        ('classification', KNeighborsClassifier(n_neighbors=n_neighbors, weights=weights))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

