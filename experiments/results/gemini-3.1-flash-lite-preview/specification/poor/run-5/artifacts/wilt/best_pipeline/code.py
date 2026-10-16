# **Created at:** 2026-09-21 18:24:09 UTC

import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import PowerTransformer
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.neural_network import MLPClassifier
from imblearn.pipeline import Pipeline
from imblearn.over_sampling import SMOTE

def train_model(X_train, y_train, imputation_strategy, method, k, k_neighbors, hidden_layer_sizes, alpha, max_iter):
    pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy=imputation_strategy)),
        ('transformer', PowerTransformer(method=method)),
        ('feature_selection', SelectKBest(score_func=f_classif, k=k)),
        ('smote', SMOTE(k_neighbors=k_neighbors)),
        ('nn', MLPClassifier(hidden_layer_sizes=hidden_layer_sizes, alpha=alpha, max_iter=max_iter, random_state=42))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

