# **Created at:** 2026-09-17 19:19:20 UTC

from sklearn.impute import SimpleImputer
from sklearn.preprocessing import RobustScaler
from sklearn.feature_selection import SelectKBest
from imblearn.under_sampling import NearMiss
from sklearn.ensemble import RandomForestClassifier
from imblearn.pipeline import Pipeline

def train_model(X_train, y_train, imputation_strategy, quantile_range, k, version, n_estimators, max_depth):
    pipeline = Pipeline([
        ('imputation', SimpleImputer(strategy=imputation_strategy)),
        ('normalization', RobustScaler(quantile_range=tuple(quantile_range))),
        ('features', SelectKBest(k=k)),
        ('rebalancing', NearMiss(version=version)),
        ('classification', RandomForestClassifier(n_estimators=n_estimators, max_depth=max_depth))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

