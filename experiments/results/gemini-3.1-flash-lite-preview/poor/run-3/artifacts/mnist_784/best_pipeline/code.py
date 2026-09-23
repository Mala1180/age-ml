# **Created at:** 2026-09-20 20:46:59 UTC

from sklearn.impute import SimpleImputer
from sklearn.preprocessing import Binarizer, RobustScaler
from imblearn.under_sampling import NearMiss
from imblearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier

def train_model(X_train, y_train, imputation_strategy, threshold, quantile_range, version, n_estimators, max_depth):
    pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy=imputation_strategy)),
        ('binarizer', Binarizer(threshold=threshold)),
        ('scaler', RobustScaler(quantile_range=tuple(quantile_range))),
        ('sampler', NearMiss(version=version)),
        ('classifier', RandomForestClassifier(n_estimators=n_estimators, max_depth=max_depth, random_state=42))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

