# **Created at:** 2026-09-21 05:43:45 UTC

import pandas as pd
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier
from imblearn.pipeline import Pipeline as ImbPipeline
from imblearn.over_sampling import SMOTE

def train_model(X_train, y_train, max_iter, k_neighbors, max_depth, min_samples_split):
    pipeline = ImbPipeline([
        ('imputation', IterativeImputer(max_iter=max_iter)),
        ('normalization', StandardScaler()),
        ('rebalancing', SMOTE(k_neighbors=k_neighbors)),
        ('classification', DecisionTreeClassifier(max_depth=max_depth, min_samples_split=min_samples_split))
    ])
    
    pipeline.fit(X_train, y_train)
    return pipeline

