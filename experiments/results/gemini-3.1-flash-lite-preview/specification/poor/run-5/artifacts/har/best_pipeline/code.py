# **Created at:** 2026-09-21 19:29:35 UTC

from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import MinMaxScaler
from sklearn.ensemble import RandomForestClassifier

def train_model(X_train, y_train, imputation_strategy, feature_range, n_estimators, max_depth):
    imputer = SimpleImputer(strategy=imputation_strategy)
    scaler = MinMaxScaler(feature_range=tuple(feature_range))
    rf_params = {'random_state': 42}
    if n_estimators is not None:
        rf_params['n_estimators'] = int(n_estimators)
    if max_depth is not None:
        rf_params['max_depth'] = int(max_depth)
    classifier = RandomForestClassifier(**rf_params)
    pipeline = Pipeline([
        ('imputer', imputer),
        ('scaler', scaler),
        ('classifier', classifier)
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

