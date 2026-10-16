# **Created at:** 2026-09-17 23:26:02 UTC

from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import StandardScaler
from sklearn.feature_selection import SelectKBest
from sklearn.neighbors import KNeighborsClassifier
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline

def train_model(X_train, y_train, max_iter, k, k_neighbors, n_neighbors, weights):
    pipeline = Pipeline([
        ('imputation', IterativeImputer(max_iter=max_iter)),
        ('normalization', StandardScaler()),
        ('features', SelectKBest(k=k)),
        ('rebalancing', SMOTE(k_neighbors=k_neighbors)),
        ('classification', KNeighborsClassifier(n_neighbors=n_neighbors, weights=weights))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

