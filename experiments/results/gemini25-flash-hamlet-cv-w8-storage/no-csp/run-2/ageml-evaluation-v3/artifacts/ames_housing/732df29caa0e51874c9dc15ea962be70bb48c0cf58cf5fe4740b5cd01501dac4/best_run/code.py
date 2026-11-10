from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import PowerTransformer
from sklearn.feature_selection import SelectKBest
from sklearn.neural_network import MLPRegressor
from sklearn.compose import ColumnTransformer
import pandas as pd

def build_model(X_train, y_train, imputation_strategy, method, k, hidden_layer_sizes, alpha, max_iter):
    numerical_cols = X_train.select_dtypes(include=['int64', 'float64']).columns

    numerical_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy=imputation_strategy)),
        ('scaler', PowerTransformer(method=method))
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numerical_transformer, numerical_cols)
        ],
        remainder='drop'
    )

    pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('selector', SelectKBest(k=k)),
        ('regressor', MLPRegressor(hidden_layer_sizes=hidden_layer_sizes, alpha=alpha, max_iter=max_iter, random_state=42))
    ])
    return pipeline
