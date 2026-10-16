# **Created at:** 2026-09-22 13:06:01 UTC

import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import KBinsDiscretizer
from sklearn.decomposition import PCA
from sklearn.svm import SVR

def train_model(X_train, y_train, max_iter, n_bins, encode, discretization_strategy, n_components, kernel, C, epsilon):
    pipeline = Pipeline([
        ('imputation', IterativeImputer(max_iter=max_iter)),
        ('discretization', KBinsDiscretizer(n_bins=n_bins, encode=encode, strategy=discretization_strategy)),
        ('features', PCA(n_components=n_components)),
        ('regression', SVR(kernel=kernel, C=C, epsilon=epsilon))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

