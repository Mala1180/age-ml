# **Created at:** 2026-04-17 16:51:03 UTC

from sklearn.pipeline import Pipeline
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import RobustScaler
from sklearn.decomposition import PCA
from sklearn.neighbors import KNeighborsRegressor

def train_model(X_train, y_train, max_iter, quantile_range, n_components, n_neighbors, weights):
    pipeline = Pipeline([
        ('imputation', IterativeImputer(max_iter=int(max_iter))),
        ('normalization', RobustScaler(quantile_range=tuple(quantile_range))),
        ('features', PCA(n_components=n_components)),
        ('regression', KNeighborsRegressor(n_neighbors=n_neighbors, weights=weights))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

