# **Created at:** 2026-09-17 23:20:20 UTC

from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import MinMaxScaler
from sklearn.feature_selection import SelectKBest
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline
from sklearn.neural_network import MLPClassifier

def train_model(X_train, y_train, max_iter, feature_range, k, k_neighbors, hidden_layer_sizes, alpha):
    pipeline = ImbPipeline([
        ('imputer', IterativeImputer(max_iter=max_iter)),
        ('scaler', MinMaxScaler(feature_range=tuple(feature_range))),
        ('selector', SelectKBest(k=k)),
        ('smote', SMOTE(k_neighbors=k_neighbors)),
        ('classifier', MLPClassifier(hidden_layer_sizes=hidden_layer_sizes, alpha=alpha, max_iter=max_iter))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

