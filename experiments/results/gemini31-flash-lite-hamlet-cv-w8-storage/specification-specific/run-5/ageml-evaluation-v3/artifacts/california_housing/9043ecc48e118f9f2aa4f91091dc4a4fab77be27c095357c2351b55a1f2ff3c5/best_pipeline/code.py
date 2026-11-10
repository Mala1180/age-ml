from sklearn.pipeline import Pipeline
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import PowerTransformer, OrdinalEncoder
from sklearn.neighbors import KNeighborsRegressor
from sklearn.compose import ColumnTransformer
import numpy as np

def build_model(X_train, y_train, max_iter, method, n_neighbors, weights):
    numeric_features = X_train.select_dtypes(include=['int64', 'float64']).columns
    categorical_features = X_train.select_dtypes(include=['object']).columns
    preprocessor = ColumnTransformer(transformers=[('num', 'passthrough', numeric_features), ('cat', OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=np.nan), categorical_features)])
    pipeline = Pipeline(steps=[('preprocessor', preprocessor), ('imputer', IterativeImputer(max_iter=max_iter)), ('scaler', PowerTransformer(method=method)), ('regressor', KNeighborsRegressor(n_neighbors=n_neighbors, weights=weights))])
    return pipeline
