# **Created at:** 2026-04-23 22:55:43 UTC

from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import RobustScaler, OneHotEncoder
from sklearn.linear_model import Lasso
from sklearn.compose import ColumnTransformer
import pandas as pd

def train_model(X_train, y_train, imputation_strategy, quantile_range, alpha):
    numerical_cols = X_train.select_dtypes(include=['number']).columns
    categorical_cols = X_train.select_dtypes(include=['object', 'category']).columns

    # Ensure quantile_range is a tuple for RobustScaler
    if isinstance(quantile_range, list):
        quantile_range_tuple = tuple(quantile_range)
    else:
        quantile_range_tuple = quantile_range

    numerical_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy=imputation_strategy)),
        ('scaler', RobustScaler(quantile_range=quantile_range_tuple))
    ])

    categorical_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='most_frequent')),
        ('onehot', OneHotEncoder(handle_unknown='ignore'))
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numerical_transformer, numerical_cols),
            ('cat', categorical_transformer, categorical_cols)
        ],
        remainder='passthrough'
    )

    pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('regressor', Lasso(alpha=alpha))
    ])

    pipeline.fit(X_train, y_train)

    return pipeline

