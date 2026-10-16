# **Created at:** 2026-09-21 05:40:16 UTC

from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import MinMaxScaler
from sklearn.svm import SVR

def train_model(X_train, y_train, imputation_strategy, feature_range, kernel, C, epsilon):
    pipeline = Pipeline(steps=[
        ('imputation', SimpleImputer(strategy=imputation_strategy)),
        ('normalization', MinMaxScaler(feature_range=tuple(feature_range))),
        ('regression', SVR(kernel=kernel, C=C, epsilon=epsilon))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

