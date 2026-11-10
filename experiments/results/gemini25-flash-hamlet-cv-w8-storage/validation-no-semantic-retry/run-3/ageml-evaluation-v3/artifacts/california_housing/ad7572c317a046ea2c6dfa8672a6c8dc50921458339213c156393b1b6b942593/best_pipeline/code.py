from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import RobustScaler, OneHotEncoder
from sklearn.decomposition import PCA
from sklearn.neighbors import KNeighborsRegressor
from sklearn.compose import ColumnTransformer

def build_model(X_train, y_train, imputation_strategy, quantile_range, n_components, n_neighbors, weights):
    # Ensure quantile_range is a tuple as required by RobustScaler
    if not isinstance(quantile_range, tuple):
        quantile_range = tuple(quantile_range)

    # Identify numerical and categorical columns
    numerical_cols = X_train.select_dtypes(include=['number']).columns
    categorical_cols = X_train.select_dtypes(include=['object', 'category']).columns

    # Create preprocessing pipelines for numerical and categorical features
    numerical_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy=imputation_strategy)),
        ('scaler', RobustScaler(quantile_range=quantile_range))
    ])

    categorical_transformer = Pipeline(steps=[
        ('cat_imputer', SimpleImputer(strategy='most_frequent')), # Impute categorical NaNs
        ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False)) # Ensure dense output for PCA
    ])

    # Create a preprocessor using ColumnTransformer to apply different transformations to different columns
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numerical_transformer, numerical_cols),
            ('cat', categorical_transformer, categorical_cols)
        ],
        remainder='passthrough' # Keep other columns if any, though not expected here
    )

    # Create the full pipeline
    pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('pca', PCA(n_components=n_components)),
        ('regressor', KNeighborsRegressor(n_neighbors=n_neighbors, weights=weights))
    ])
    return pipeline
