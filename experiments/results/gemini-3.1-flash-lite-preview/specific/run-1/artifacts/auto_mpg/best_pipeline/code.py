# **Created at:** 2026-09-18 06:31:44 UTC

import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR

def train_model(X_train, y_train, max_iter, kernel, C, epsilon):
    pipeline = Pipeline([
        ('imputation', IterativeImputer(max_iter=max_iter)),
        ('normalization', StandardScaler()),
        ('regression', SVR(kernel=kernel, C=C, epsilon=epsilon))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

