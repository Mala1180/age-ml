# **Created at:** 2026-09-18 06:16:23 UTC

from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier

def train_model(X_train, y_train, n_estimators, max_depth):
    pipeline = Pipeline([
        ('classification', RandomForestClassifier(n_estimators=n_estimators, max_depth=max_depth))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

