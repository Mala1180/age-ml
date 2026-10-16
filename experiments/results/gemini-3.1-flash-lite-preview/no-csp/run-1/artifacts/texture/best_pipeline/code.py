# **Created at:** 2026-10-16 10:59:19 UTC

from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.neural_network import MLPClassifier
from imblearn.pipeline import Pipeline as ImbPipeline
from imblearn.over_sampling import SMOTE

def train_model(X_train, y_train, imputation_strategy, n_components, k_neighbors, hidden_layer_sizes, alpha, max_iter):
    pipeline = ImbPipeline([
        ('imputation', SimpleImputer(strategy=imputation_strategy)),
        ('normalization', StandardScaler()),
        ('features', PCA(n_components=n_components)),
        ('rebalancing', SMOTE(k_neighbors=k_neighbors)),
        ('classification', MLPClassifier(hidden_layer_sizes=hidden_layer_sizes, alpha=alpha, max_iter=max_iter, random_state=42))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

