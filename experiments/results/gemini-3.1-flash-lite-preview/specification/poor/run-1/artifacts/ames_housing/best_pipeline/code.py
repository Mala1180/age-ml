# **Created at:** 2026-09-17 23:14:13 UTC

from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import KBinsDiscretizer, StandardScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.compose import ColumnTransformer

def train_model(X_train, y_train, imputation_strategy, n_bins, encode, discretization_strategy, n_estimators, max_depth):
    numeric_features = X_train.select_dtypes(include=['int64', 'float64']).columns
    numeric_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy=imputation_strategy)),
        ('discretization', KBinsDiscretizer(n_bins=n_bins, encode=encode, strategy=discretization_strategy)),
        ('scaler', StandardScaler(with_mean=False))
    ])
    preprocessor = ColumnTransformer(transformers=[('num', numeric_transformer, numeric_features)], remainder='drop')
    pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('regressor', RandomForestRegressor(n_estimators=n_estimators, max_depth=max_depth))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

