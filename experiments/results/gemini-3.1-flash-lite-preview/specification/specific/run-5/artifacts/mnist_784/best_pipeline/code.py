# **Created at:** 2026-09-23 17:08:01 UTC

from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline

def train_model(X_train, y_train, n_estimators, max_depth):
    pipeline = Pipeline([
        ('classification', RandomForestClassifier(n_estimators=n_estimators, max_depth=max_depth))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

