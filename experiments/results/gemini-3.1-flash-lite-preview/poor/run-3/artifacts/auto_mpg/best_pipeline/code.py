# **Created at:** 2026-09-21 00:09:15 UTC

from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import PowerTransformer
from sklearn.decomposition import PCA
from sklearn.svm import SVR

def train_model(X_train, y_train, imputation_strategy, method, n_components, kernel, C, epsilon):
    pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy=imputation_strategy)),
        ('transformer', PowerTransformer(method=method)),
        ('pca', PCA(n_components=n_components)),
        ('svr', SVR(kernel=kernel, C=C, epsilon=epsilon))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

