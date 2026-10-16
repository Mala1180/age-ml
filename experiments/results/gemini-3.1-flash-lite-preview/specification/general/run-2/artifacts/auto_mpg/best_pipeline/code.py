# **Created at:** 2026-09-20 16:28:53 UTC

import pandas as pd
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import RobustScaler
from sklearn.feature_selection import SelectKBest, f_regression
from sklearn.svm import SVR
from sklearn.pipeline import Pipeline

def train_model(X_train, y_train, max_iter, quantile_range, k, kernel, C, epsilon):
    pipeline = Pipeline([
        ('imputer', IterativeImputer(max_iter=max_iter)),
        ('scaler', RobustScaler(quantile_range=tuple(quantile_range))),
        ('selector', SelectKBest(score_func=f_regression, k=k)),
        ('svr', SVR(kernel=kernel, C=C, epsilon=epsilon))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

