# **Created at:** 2026-09-21 10:31:14 UTC

from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import MinMaxScaler
from sklearn.feature_selection import SelectKBest, f_regression
from sklearn.neighbors import KNeighborsRegressor

def train_model(X_train, y_train, imputation_strategy, feature_range, k, n_neighbors, weights):
    pipeline = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy=imputation_strategy)),
        ('scaler', MinMaxScaler(feature_range=tuple(feature_range))),
        ('selector', SelectKBest(score_func=f_regression, k=k)),
        ('regressor', KNeighborsRegressor(n_neighbors=n_neighbors, weights=weights))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

