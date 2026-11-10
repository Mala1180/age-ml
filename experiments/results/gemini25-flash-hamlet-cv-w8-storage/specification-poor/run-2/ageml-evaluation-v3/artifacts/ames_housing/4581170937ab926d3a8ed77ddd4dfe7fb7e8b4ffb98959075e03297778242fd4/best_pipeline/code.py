from sklearn.pipeline import Pipeline
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import KBinsDiscretizer, RobustScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.compose import ColumnTransformer
import numpy as np

def build_model(X_train, y_train, max_iter, n_bins, encode, discretization_strategy, quantile_range, n_estimators, max_depth):
    numerical_features = X_train.select_dtypes(include=np.number).columns

    numerical_transformer = Pipeline([
        ('imputer', IterativeImputer(max_iter=max_iter, random_state=42)),
        ('discretizer', KBinsDiscretizer(n_bins=n_bins, encode=encode, strategy=discretization_strategy, random_state=42)),
        ('scaler', RobustScaler(quantile_range=tuple(quantile_range)))
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numerical_transformer, numerical_features)
        ],
        remainder='drop'
    )

    pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('regressor', RandomForestRegressor(n_estimators=n_estimators, max_depth=max_depth, random_state=42))
    ])
    return pipeline
