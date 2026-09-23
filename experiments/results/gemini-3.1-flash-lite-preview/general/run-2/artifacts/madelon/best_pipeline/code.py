# **Created at:** 2026-09-18 18:11:37 UTC

from sklearn.pipeline import Pipeline
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.ensemble import RandomForestClassifier

def train_model(X_train, y_train, k, n_estimators, max_depth):
    pipeline = Pipeline([
        ('features', SelectKBest(score_func=f_classif, k=k)),
        ('classification', RandomForestClassifier(n_estimators=n_estimators, max_depth=max_depth, random_state=42))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

