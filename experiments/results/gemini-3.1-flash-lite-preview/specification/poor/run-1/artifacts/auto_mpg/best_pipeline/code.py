# **Created at:** 2026-09-17 23:16:43 UTC

from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import RobustScaler
from sklearn.feature_selection import SelectKBest, f_regression
from sklearn.ensemble import RandomForestRegressor

def train_model(X_train, y_train, imputation_strategy, quantile_range, k, n_estimators, max_depth):
    pipe = Pipeline([
        ('imputer', SimpleImputer(strategy=imputation_strategy)),
        ('scaler', RobustScaler(quantile_range=tuple(quantile_range))),
        ('selector', SelectKBest(score_func=f_regression, k=k)),
        ('regressor', RandomForestRegressor(n_estimators=n_estimators, max_depth=max_depth, random_state=42))
    ])
    pipe.fit(X_train, y_train)
    return pipe

