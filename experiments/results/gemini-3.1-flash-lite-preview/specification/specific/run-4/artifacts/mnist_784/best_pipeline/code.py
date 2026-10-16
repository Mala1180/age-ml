# **Created at:** 2026-09-21 18:04:30 UTC

from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline

def train_model(X_train, y_train, n_estimators, max_depth):
    pipeline = Pipeline([
        ('rf', RandomForestClassifier(n_estimators=n_estimators, max_depth=max_depth, random_state=42))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

