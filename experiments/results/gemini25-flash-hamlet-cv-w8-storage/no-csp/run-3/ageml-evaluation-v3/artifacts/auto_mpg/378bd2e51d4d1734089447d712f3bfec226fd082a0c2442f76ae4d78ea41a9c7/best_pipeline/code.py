from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestRegressor

def build_model(X_train, y_train, imputation_strategy, n_estimators, max_depth):
    pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy=imputation_strategy)),
        ('regressor', RandomForestRegressor(n_estimators=n_estimators, max_depth=max_depth, random_state=42))
    ])
    return pipeline
