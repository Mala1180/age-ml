# **Created at:** 2026-09-18 17:55:35 UTC

import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.linear_model import Ridge
from sklearn.compose import ColumnTransformer

def train_model(X_train, y_train, imputation_strategy, alpha):
    numeric_features = X_train.select_dtypes(include=['int64', 'float64']).columns
    categorical_features = X_train.select_dtypes(include=['object']).columns
    numeric_transformer = Pipeline(steps=[('imputer', SimpleImputer(strategy=imputation_strategy)), ('scaler', StandardScaler())])
    categorical_transformer = Pipeline(steps=[('imputer', SimpleImputer(strategy='most_frequent')), ('encoder', OneHotEncoder(handle_unknown='ignore')), ('scaler', StandardScaler(with_mean=False))])
    preprocessor = ColumnTransformer(transformers=[('num', numeric_transformer, numeric_features), ('cat', categorical_transformer, categorical_features)])
    model = Pipeline(steps=[('preprocessor', preprocessor), ('regressor', Ridge(alpha=alpha))])
    model.fit(X_train, y_train)
    return model

