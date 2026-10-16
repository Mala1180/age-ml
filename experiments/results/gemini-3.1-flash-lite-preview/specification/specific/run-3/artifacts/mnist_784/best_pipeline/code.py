# **Created at:** 2026-09-21 05:19:20 UTC

from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline

def train_model(X_train, y_train, n_estimators, max_depth):
    pipeline = Pipeline([
        ('clf', RandomForestClassifier(n_estimators=n_estimators, max_depth=max_depth, random_state=42))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

