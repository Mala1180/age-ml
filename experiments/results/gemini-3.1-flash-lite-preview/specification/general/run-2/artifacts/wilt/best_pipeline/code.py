# **Created at:** 2026-09-18 18:04:21 UTC

from sklearn.impute import SimpleImputer
from sklearn.preprocessing import MinMaxScaler
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.neural_network import MLPClassifier
from imblearn.pipeline import Pipeline as ImbPipeline
from imblearn.over_sampling import SMOTE

def train_model(X_train, y_train, imputation_strategy, feature_range, k, k_neighbors, hidden_layer_sizes, alpha, max_iter):
    pipeline = ImbPipeline([
        ('imputer', SimpleImputer(strategy=imputation_strategy)),
        ('scaler', MinMaxScaler(feature_range=tuple(feature_range))),
        ('selector', SelectKBest(score_func=f_classif, k=k)),
        ('sampler', SMOTE(k_neighbors=k_neighbors)),
        ('classifier', MLPClassifier(hidden_layer_sizes=hidden_layer_sizes, alpha=alpha, max_iter=max_iter, random_state=42))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

