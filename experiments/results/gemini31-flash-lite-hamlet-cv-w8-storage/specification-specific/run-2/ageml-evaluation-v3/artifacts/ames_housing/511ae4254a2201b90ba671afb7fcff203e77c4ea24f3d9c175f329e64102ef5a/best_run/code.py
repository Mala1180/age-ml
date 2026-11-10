from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import PowerTransformer, OneHotEncoder
from sklearn.decomposition import PCA
from sklearn.linear_model import Lasso
from sklearn.compose import ColumnTransformer

def build_model(X_train, y_train, imputation_strategy, method, n_components, alpha):
    numeric_features = X_train.select_dtypes(include=['int64', 'float64']).columns
    categorical_features = X_train.select_dtypes(include=['object']).columns
    numeric_transformer = Pipeline(steps=[('imputer', SimpleImputer(strategy=imputation_strategy)), ('scaler', PowerTransformer(method=method))])
    categorical_transformer = Pipeline(steps=[('imputer', SimpleImputer(strategy='most_frequent')), ('encoder', OneHotEncoder(handle_unknown='ignore', sparse_output=False))])
    preprocessor = ColumnTransformer(transformers=[('num', numeric_transformer, numeric_features), ('cat', categorical_transformer, categorical_features)])
    pipeline = Pipeline(steps=[('preprocessor', preprocessor), ('pca', PCA(n_components=n_components)), ('regressor', Lasso(alpha=alpha))])
    return pipeline
