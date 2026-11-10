import pandas as pd
import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import PowerTransformer
from sklearn.feature_selection import SelectKBest, f_regression
from sklearn.neural_network import MLPRegressor
from sklearn.compose import ColumnTransformer, make_column_selector

def build_model(X_train, y_train, imputation_strategy, method, k, hidden_layer_sizes, alpha, max_iter):
    # Define preprocessing for numerical features
    numerical_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy=imputation_strategy)),
        ('normalizer', PowerTransformer(method=method))
    ])

    # Create a preprocessor to apply transformations only to numerical columns
    # Categorical columns will be dropped by default (remainder='drop')
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numerical_transformer, make_column_selector(dtype_include=np.number))
        ],
        remainder='drop'
    )

    # Create the full pipeline
    model = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('selector', SelectKBest(score_func=f_regression, k=k)),
        ('regressor', MLPRegressor(hidden_layer_sizes=hidden_layer_sizes, alpha=alpha, max_iter=max_iter, random_state=42))
    ])

    return model
