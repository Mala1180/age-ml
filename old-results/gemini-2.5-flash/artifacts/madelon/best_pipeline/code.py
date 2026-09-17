# **Created at:** 2026-04-23 19:15:16 UTC

from sklearn.experimental import enable_iterative_imputer
import pandas as pd
import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import PowerTransformer
from sklearn.feature_selection import SelectKBest
from sklearn.neighbors import KNeighborsClassifier
from sklearn.linear_model import BayesianRidge

def train_model(X_train, y_train, max_iter, method, k, n_neighbors, weights):
    """
    Builds and trains a machine learning pipeline.

    Args:
        X_train (pandas.DataFrame or numpy.array): Training features.
        y_train (pandas.Series or numpy.array): Training target.
        max_iter (int): Hyperparameter for IterativeImputer.
        method (str): Hyperparameter for IterativeImputer (estimator type).
        k (int): Hyperparameter for SelectKBest.
        n_neighbors (int): Hyperparameter for KNeighborsClassifier.
        weights (str): Hyperparameter for KNeighborsClassifier.

    Returns:
        sklearn.pipeline.Pipeline: The trained machine learning model.
    """

    # Map method string to actual estimator
    if method == 'BayesianRidge':
        imputer_estimator = BayesianRidge()
    else:
        # Default to BayesianRidge if method is not recognized or provided
        imputer_estimator = BayesianRidge()

    pipeline = Pipeline([
        ('imputation', IterativeImputer(max_iter=max_iter, estimator=imputer_estimator, random_state=42)),
        ('normalization', PowerTransformer()),
        ('features', SelectKBest(k=k)),
        ('classification', KNeighborsClassifier(n_neighbors=n_neighbors, weights=weights))
    ])

    pipeline.fit(X_train, y_train)
    return pipeline

