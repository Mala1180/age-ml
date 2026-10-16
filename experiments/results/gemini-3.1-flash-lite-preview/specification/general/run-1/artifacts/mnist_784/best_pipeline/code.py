# **Created at:** 2026-09-18 04:15:10 UTC

import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import Binarizer
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline
from sklearn.ensemble import RandomForestClassifier

def train_model(X_train, y_train, imputation_strategy, threshold, k_neighbors, n_estimators, max_depth):
    pipeline = ImbPipeline([
        ('imputer', SimpleImputer(strategy=imputation_strategy)),
        ('binarizer', Binarizer(threshold=threshold)),
        ('smote', SMOTE(k_neighbors=k_neighbors)),
        ('classifier', RandomForestClassifier(n_estimators=n_estimators, max_depth=max_depth))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

