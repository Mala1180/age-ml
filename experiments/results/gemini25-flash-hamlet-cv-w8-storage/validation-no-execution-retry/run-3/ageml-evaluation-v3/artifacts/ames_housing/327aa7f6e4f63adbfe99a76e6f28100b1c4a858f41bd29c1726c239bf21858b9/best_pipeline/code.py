import pandas as pd
import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import PowerTransformer
from sklearn.decomposition import PCA
from sklearn.linear_model import ElasticNet
from sklearn.compose import ColumnTransformer

def build_model(X_train, y_train, imputation_strategy, method, n_components, alpha, l1_ratio):
    numerical_cols = X_train.select_dtypes(include=np.number).columns.tolist()

    # Remove 'Id' if present, as it's typically an identifier and not a feature
    if 'Id' in numerical_cols:
        numerical_cols.remove('Id')

    numerical_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy=imputation_strategy)),
        ('power_transformer', PowerTransformer(method=method)),
        ('pca', PCA(n_components=n_components))
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numerical_transformer, numerical_cols)
        ],
        remainder='drop' # Drop columns not specified in transformers (e.g., categorical)
    )

    model_pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('regressor', ElasticNet(alpha=alpha, l1_ratio=l1_ratio, random_state=42))
    ])

    return model_pipeline
