# **Created at:** 2026-09-17 20:36:56 UTC

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.feature_selection import SelectKBest, f_classif
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline
from sklearn.ensemble import RandomForestClassifier

def train_model(X_train, y_train, k, k_neighbors, n_estimators, max_depth):
    numeric_features = X_train.select_dtypes(include=['int64', 'float64']).columns
    categorical_features = X_train.select_dtypes(include=['object']).columns
    preprocessor = ColumnTransformer(transformers=[
        ('num', StandardScaler(), numeric_features),
        ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_features)
    ])
    pipeline = ImbPipeline([
        ('preprocessor', preprocessor),
        ('features', SelectKBest(score_func=f_classif, k=k)),
        ('rebalancing', SMOTE(k_neighbors=min(k_neighbors, len(X_train) - 1))),
        ('classification', RandomForestClassifier(n_estimators=n_estimators, max_depth=max_depth, random_state=42))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

