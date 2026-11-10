from sklearn.experimental import enable_iterative_imputer
import pandas as pd
from imblearn.pipeline import Pipeline as ImbPipeline
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import PowerTransformer
from sklearn.decomposition import PCA
from imblearn.over_sampling import SMOTE
from sklearn.neural_network import MLPClassifier

def build_model(X_train, y_train, max_iter, method, n_components, k_neighbors, hidden_layer_sizes, alpha):
    pipeline = ImbPipeline([
        ('imputation', IterativeImputer(max_iter=max_iter, random_state=42)),
        ('normalization', PowerTransformer(method=method)),
        ('features', PCA(n_components=n_components, random_state=42)),
        ('rebalancing', SMOTE(k_neighbors=k_neighbors, random_state=42)),
        ('classification', MLPClassifier(hidden_layer_sizes=hidden_layer_sizes, alpha=alpha, random_state=42))
    ])
    return pipeline
