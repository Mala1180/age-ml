# **Created at:** 2026-09-21 08:03:26 UTC

from sklearn.impute import SimpleImputer
from sklearn.preprocessing import Binarizer, MinMaxScaler
from sklearn.ensemble import RandomForestClassifier
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline

def train_model(X_train, y_train, imputation_strategy, threshold, feature_range, k_neighbors, n_estimators, max_depth):
    pipeline = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy=imputation_strategy)),
        ('binarizer', Binarizer(threshold=threshold)),
        ('scaler', MinMaxScaler(feature_range=tuple(feature_range))),
        ('smote', SMOTE(k_neighbors=k_neighbors)),
        ('classifier', RandomForestClassifier(n_estimators=n_estimators, max_depth=max_depth))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

