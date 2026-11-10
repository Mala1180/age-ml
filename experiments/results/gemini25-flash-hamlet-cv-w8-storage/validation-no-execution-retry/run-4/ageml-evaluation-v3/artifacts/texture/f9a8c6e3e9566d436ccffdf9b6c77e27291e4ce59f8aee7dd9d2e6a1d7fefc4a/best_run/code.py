import pandas as pd
import numpy as np
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import PowerTransformer
from imblearn.over_sampling import SMOTE
from sklearn.neural_network import MLPClassifier
from imblearn.pipeline import Pipeline

def build_model(X_train, y_train, max_iter, method, k_neighbors, hidden_layer_sizes, alpha):
    imputer = IterativeImputer(max_iter=max_iter, random_state=42)
    normalizer = PowerTransformer(method=method)
    smote = SMOTE(random_state=42, k_neighbors=k_neighbors)
    classifier = MLPClassifier(hidden_layer_sizes=hidden_layer_sizes, alpha=alpha, random_state=42)

    pipeline = Pipeline(steps=[
        ('imputer', imputer),
        ('normalizer', normalizer),
        ('smote', smote),
        ('classifier', classifier)
    ])

    return pipeline
