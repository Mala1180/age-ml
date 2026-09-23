# **Created at:** 2026-09-21 04:10:34 UTC

from sklearn.pipeline import Pipeline
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import MinMaxScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.feature_selection import SelectKBest, f_regression
from sklearn.neighbors import KNeighborsRegressor

def train_model(X_train, y_train, max_iter, feature_range, k, n_neighbors, weights):
    numeric_features = X_train.select_dtypes(include=['int64', 'float64']).columns
    categorical_features = X_train.select_dtypes(include=['object']).columns
    preprocessor = ColumnTransformer(transformers=[('num', 'passthrough', numeric_features), ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_features)])
    pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('imputation', IterativeImputer(max_iter=max_iter)),
        ('normalization', MinMaxScaler(feature_range=tuple(feature_range))),
        ('features', SelectKBest(score_func=f_regression, k=k)),
        ('regression', KNeighborsRegressor(n_neighbors=n_neighbors, weights=weights))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

