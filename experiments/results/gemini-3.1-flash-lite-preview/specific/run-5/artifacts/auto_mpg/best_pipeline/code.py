# **Created at:** 2026-09-23 17:33:30 UTC

from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import MinMaxScaler
from sklearn.svm import SVR
from sklearn.pipeline import Pipeline

def train_model(X_train, y_train, max_iter, feature_range, kernel, C, epsilon):
    pipeline = Pipeline([
        ('imputer', IterativeImputer(max_iter=max_iter)),
        ('scaler', MinMaxScaler(feature_range=tuple(feature_range))),
        ('regressor', SVR(kernel=kernel, C=C, epsilon=epsilon))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

