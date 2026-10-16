# **Created at:** 2026-09-18 07:00:42 UTC

import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import RobustScaler
from sklearn.feature_selection import SelectKBest
from imblearn.pipeline import Pipeline as ImbPipeline
from imblearn.over_sampling import SMOTE
from sklearn.neighbors import KNeighborsClassifier

def train_model(X_train, y_train, max_iter, quantile_range, k, k_neighbors, n_neighbors, weights):
    imputer = IterativeImputer(max_iter=int(max_iter))
    scaler = RobustScaler(quantile_range=tuple(quantile_range))
    selector = SelectKBest(k=int(k))
    smote = SMOTE(k_neighbors=int(k_neighbors))
    knn = KNeighborsClassifier(n_neighbors=int(n_neighbors), weights=weights)
    pipeline = ImbPipeline([
        ('imputation', imputer),
        ('normalization', scaler),
        ('features', selector),
        ('rebalancing', smote),
        ('classification', knn)
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

