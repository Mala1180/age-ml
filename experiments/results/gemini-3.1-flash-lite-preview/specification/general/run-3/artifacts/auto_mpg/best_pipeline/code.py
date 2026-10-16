# **Created at:** 2026-09-21 04:18:28 UTC

from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import KBinsDiscretizer, MinMaxScaler
from sklearn.decomposition import PCA
from sklearn.neighbors import KNeighborsRegressor

def train_model(X_train, y_train, imputation_strategy, n_bins, encode, discretization_strategy, feature_range, n_components, n_neighbors, weights):
    pipeline = Pipeline([
        ('imputation', SimpleImputer(strategy=imputation_strategy)),
        ('discretization', KBinsDiscretizer(n_bins=n_bins, encode=encode, strategy=discretization_strategy)),
        ('normalization', MinMaxScaler(feature_range=tuple(feature_range))),
        ('features', PCA(n_components=n_components)),
        ('classification', KNeighborsRegressor(n_neighbors=n_neighbors, weights=weights))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

