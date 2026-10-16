# **Created at:** 2026-09-18 15:42:29 UTC

import pandas as pd
from sklearn.preprocessing import PowerTransformer, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.tree import DecisionTreeClassifier
from imblearn.pipeline import Pipeline as ImbPipeline
from imblearn.over_sampling import SMOTE

def train_model(X_train, y_train, method, k_neighbors, max_depth, min_samples_split):
    numeric_features = X_train.select_dtypes(include=['int64', 'float64']).columns
    categorical_features = X_train.select_dtypes(include=['object']).columns
    
    preprocessor = ColumnTransformer(transformers=[
        ('num', PowerTransformer(method=method), numeric_features),
        ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_features)
    ])
    
    pipeline = ImbPipeline([
        ('preprocessor', preprocessor),
        ('rebalancing', SMOTE(k_neighbors=k_neighbors)),
        ('classification', DecisionTreeClassifier(max_depth=max_depth, min_samples_split=min_samples_split))
    ])
    
    pipeline.fit(X_train, y_train)
    return pipeline

