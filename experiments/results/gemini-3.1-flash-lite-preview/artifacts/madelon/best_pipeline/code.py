# **Created at:** 2026-04-23 15:24:13 UTC

from sklearn.impute import SimpleImputer
from sklearn.preprocessing import PowerTransformer
from sklearn.feature_selection import SelectKBest
from sklearn.neighbors import KNeighborsClassifier
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline

def train_model(X_train, y_train, imputation_strategy, method, k, k_neighbors, n_neighbors, weights):
    steps = [
        ('imputer', SimpleImputer(strategy=imputation_strategy)),
        ('scaler', PowerTransformer(method=method)),
        ('feature_selector', SelectKBest(k=k)),
        ('smote', SMOTE(k_neighbors=k_neighbors)),
        ('classifier', KNeighborsClassifier(n_neighbors=n_neighbors, weights=weights))
    ]
    pipeline = Pipeline(steps)
    pipeline.fit(X_train, y_train)
    return pipeline

