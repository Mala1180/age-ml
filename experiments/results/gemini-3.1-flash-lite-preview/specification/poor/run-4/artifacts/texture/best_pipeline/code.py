# **Created at:** 2026-09-21 05:45:39 UTC

from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import MinMaxScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline

def train_model(X_train, y_train, max_iter, feature_range, n_estimators, max_depth):
    pipeline = Pipeline([
        ('imputation', IterativeImputer(max_iter=max_iter)),
        ('normalization', MinMaxScaler(feature_range=tuple(feature_range))),
        ('classification', RandomForestClassifier(n_estimators=n_estimators, max_depth=max_depth))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

