# **Created at:** 2026-10-16 10:58:36 UTC

from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier

def train_model(X_train, y_train, imputation_strategy, n_components, k_neighbors, n_estimators, max_depth):
    pipeline = Pipeline([
        ('imputation', SimpleImputer(strategy=imputation_strategy)),
        ('normalization', StandardScaler()),
        ('features', PCA(n_components=n_components)),
        ('rebalancing', SMOTE(k_neighbors=k_neighbors)),
        ('classification', RandomForestClassifier(n_estimators=n_estimators, max_depth=max_depth))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

