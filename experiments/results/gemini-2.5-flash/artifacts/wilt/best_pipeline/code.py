# **Created at:** 2026-04-23 19:07:25 UTC

import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import PowerTransformer
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline
from sklearn.neural_network import MLPClassifier

def train_model(X_train, y_train, imputation_strategy, method, k_neighbors, hidden_layer_sizes, alpha, max_iter):
    pipeline = ImbPipeline([
        ('imputer', SimpleImputer(strategy=imputation_strategy)),
        ('normalizer', PowerTransformer(method=method)),
        ('smote', SMOTE(k_neighbors=k_neighbors, random_state=42)),
        ('classifier', MLPClassifier(hidden_layer_sizes=hidden_layer_sizes, alpha=alpha, max_iter=max_iter, random_state=42))
    ])
    
    model = pipeline.fit(X_train, y_train)
    return model

