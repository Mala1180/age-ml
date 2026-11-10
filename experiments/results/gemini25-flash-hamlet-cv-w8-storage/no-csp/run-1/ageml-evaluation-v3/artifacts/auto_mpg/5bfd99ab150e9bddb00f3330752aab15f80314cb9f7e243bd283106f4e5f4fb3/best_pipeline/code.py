from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.feature_selection import SelectKBest
from sklearn.ensemble import RandomForestRegressor

def build_model(X_train, y_train, imputation_strategy, k, n_estimators, max_depth):
    imputer = SimpleImputer(strategy=imputation_strategy)
    selector = SelectKBest(k=k)
    regressor = RandomForestRegressor(n_estimators=n_estimators, max_depth=max_depth, random_state=42)

    pipeline = Pipeline(steps=[
        ('imputer', imputer),
        ('selector', selector),
        ('regressor', regressor)
    ])

    return pipeline
