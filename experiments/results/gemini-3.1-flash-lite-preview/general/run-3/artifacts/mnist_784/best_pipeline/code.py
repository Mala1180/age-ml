# **Created at:** 2026-09-21 02:27:36 UTC

from sklearn.impute import SimpleImputer
from sklearn.preprocessing import Binarizer
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline
from sklearn.ensemble import RandomForestClassifier

def train_model(X_train, y_train, imputation_strategy, threshold, k_neighbors, n_estimators, max_depth):
    pipeline = ImbPipeline([
        ('imputation', SimpleImputer(strategy=imputation_strategy)),
        ('discretization', Binarizer(threshold=threshold)),
        ('rebalancing', SMOTE(k_neighbors=k_neighbors)),
        ('classification', RandomForestClassifier(n_estimators=n_estimators, max_depth=max_depth))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

