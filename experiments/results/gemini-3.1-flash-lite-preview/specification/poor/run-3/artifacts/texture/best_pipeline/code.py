# **Created at:** 2026-09-20 17:56:55 UTC

from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import PowerTransformer
from imblearn.under_sampling import NearMiss
from sklearn.neighbors import KNeighborsClassifier
from imblearn.pipeline import Pipeline

def train_model(X_train, y_train, max_iter, method, version, n_neighbors, weights):
    pipeline = Pipeline([
        ('imputation', IterativeImputer(max_iter=max_iter)),
        ('normalization', PowerTransformer(method=method)),
        ('rebalancing', NearMiss(version=version)),
        ('classification', KNeighborsClassifier(n_neighbors=n_neighbors, weights=weights))
    ])
    
    pipeline.fit(X_train, y_train)
    return pipeline

