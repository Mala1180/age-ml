# **Created at:** 2026-09-18 04:56:03 UTC

from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import PowerTransformer
from sklearn.decomposition import PCA
from sklearn.neighbors import KNeighborsRegressor

def train_model(X_train, y_train, imputation_strategy, method, n_components, n_neighbors, weights):
    pipeline = Pipeline([
        ('imputation', SimpleImputer(strategy=imputation_strategy)),
        ('normalization', PowerTransformer(method=method)),
        ('features', PCA(n_components=n_components)),
        ('classification', KNeighborsRegressor(n_neighbors=n_neighbors, weights=weights))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

