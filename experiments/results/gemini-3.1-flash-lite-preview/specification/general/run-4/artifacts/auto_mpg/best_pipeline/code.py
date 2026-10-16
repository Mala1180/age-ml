# **Created at:** 2026-09-21 15:41:50 UTC

from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestRegressor

def train_model(X_train, y_train, imputation_strategy, n_estimators, max_depth):
    pipeline = Pipeline([
        ('imputation', SimpleImputer(strategy=imputation_strategy)),
        ('regression', RandomForestRegressor(n_estimators=n_estimators, max_depth=max_depth, random_state=42))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

