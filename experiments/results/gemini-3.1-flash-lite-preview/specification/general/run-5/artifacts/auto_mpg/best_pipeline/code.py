# **Created at:** 2026-09-23 14:47:20 UTC

from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.feature_selection import SelectKBest, f_regression
from sklearn.ensemble import RandomForestRegressor

def train_model(X_train, y_train, imputation_strategy, k, n_estimators, max_depth):
    pipeline = Pipeline([
        ('imputation', SimpleImputer(strategy=imputation_strategy)),
        ('features', SelectKBest(score_func=f_regression, k=k)),
        ('classification', RandomForestRegressor(n_estimators=n_estimators, max_depth=max_depth))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

