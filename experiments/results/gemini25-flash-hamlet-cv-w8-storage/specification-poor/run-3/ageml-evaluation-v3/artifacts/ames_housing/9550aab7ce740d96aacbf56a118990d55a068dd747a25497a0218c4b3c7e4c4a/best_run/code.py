from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import KBinsDiscretizer, RobustScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
import pandas as pd

def build_model(X_train, y_train, max_iter, n_bins, encode, discretization_strategy, quantile_range, n_estimators, max_depth):
    numerical_features = X_train.select_dtypes(include=['int64', 'float64']).columns

    numerical_pipeline = Pipeline(steps=[
        ('imputer', IterativeImputer(max_iter=max_iter, random_state=42)),
        ('discretizer', KBinsDiscretizer(n_bins=n_bins, encode=encode, strategy=discretization_strategy)),
        ('scaler', RobustScaler(quantile_range=tuple(quantile_range)))
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numerical_pipeline, numerical_features)
        ],
        remainder='drop'
    )

    pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('regressor', RandomForestRegressor(n_estimators=n_estimators, max_depth=max_depth, random_state=42))
    ])

    return pipeline
