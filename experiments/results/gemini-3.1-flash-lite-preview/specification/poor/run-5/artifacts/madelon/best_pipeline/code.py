# **Created at:** 2026-09-21 18:56:08 UTC

from sklearn.impute import SimpleImputer
from sklearn.feature_selection import SelectKBest
from sklearn.tree import DecisionTreeClassifier
from imblearn.under_sampling import NearMiss
from imblearn.pipeline import Pipeline

def train_model(X_train, y_train, imputation_strategy, k, version, max_depth, min_samples_split):
    pipeline = Pipeline([
        ('imputation', SimpleImputer(strategy=imputation_strategy)),
        ('features', SelectKBest(k=k)),
        ('rebalancing', NearMiss(version=version)),
        ('classification', DecisionTreeClassifier(max_depth=max_depth, min_samples_split=min_samples_split))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

