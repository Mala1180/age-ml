# **Created at:** 2026-09-18 15:53:32 UTC

from sklearn.impute import SimpleImputer
from sklearn.preprocessing import Binarizer
from sklearn.ensemble import RandomForestClassifier
from imblearn.under_sampling import NearMiss
from imblearn.pipeline import Pipeline as ImbPipeline

def train_model(X_train, y_train, imputation_strategy, threshold, version, n_estimators, max_depth):
    pipeline = ImbPipeline([
        ('imputer', SimpleImputer(strategy=imputation_strategy)),
        ('binarizer', Binarizer(threshold=threshold)),
        ('rebalancer', NearMiss(version=version)),
        ('classifier', RandomForestClassifier(n_estimators=n_estimators, max_depth=max_depth, random_state=42))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

