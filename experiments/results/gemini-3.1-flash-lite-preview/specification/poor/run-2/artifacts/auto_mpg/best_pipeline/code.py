# **Created at:** 2026-09-18 18:00:59 UTC

from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import PowerTransformer
from sklearn.decomposition import PCA
from sklearn.svm import SVR

def train_model(X_train, y_train, imputation_strategy, method, n_components, kernel, C, epsilon):
    pipeline = Pipeline([
        ('imputation', SimpleImputer(strategy=imputation_strategy)),
        ('normalization', PowerTransformer(method=method)),
        ('features', PCA(n_components=n_components)),
        ('regression', SVR(kernel=kernel, C=C, epsilon=epsilon))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

