# **Created at:** 2026-09-18 06:37:37 UTC

from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPClassifier
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline

def train_model(X_train, y_train, imputation_strategy, k_neighbors, hidden_layer_sizes, alpha, max_iter):
    pipeline = ImbPipeline([
        ('imputer', SimpleImputer(strategy=imputation_strategy)),
        ('scaler', StandardScaler()),
        ('smote', SMOTE(k_neighbors=k_neighbors)),
        ('nn', MLPClassifier(hidden_layer_sizes=hidden_layer_sizes, alpha=alpha, max_iter=max_iter, random_state=42))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

