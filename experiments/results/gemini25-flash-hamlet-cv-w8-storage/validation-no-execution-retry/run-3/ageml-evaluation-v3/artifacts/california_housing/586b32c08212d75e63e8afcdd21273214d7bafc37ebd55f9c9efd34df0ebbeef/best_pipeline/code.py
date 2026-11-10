from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.experimental import enable_iterative_imputer # Required for IterativeImputer
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import KBinsDiscretizer, StandardScaler, OneHotEncoder
from sklearn.decomposition import PCA
from sklearn.neighbors import KNeighborsRegressor
import numpy as np

def build_model(X_train, y_train, max_iter, n_bins, encode, discretization_strategy, n_components, n_neighbors, weights):
    # Identify numerical and categorical features
    numerical_features = X_train.select_dtypes(include=np.number).columns.tolist()
    categorical_features = X_train.select_dtypes(include='object').columns.tolist()

    # Define numerical pipeline steps
    numerical_transformer = Pipeline(steps=[
        ('imputer', IterativeImputer(max_iter=max_iter, random_state=42)), # Step 1: imputation
        ('discretizer', KBinsDiscretizer(n_bins=n_bins, encode=encode, strategy=discretization_strategy)), # Step 2: discretization
        ('scaler', StandardScaler()) # Step 3: normalization
    ])

    # Define categorical pipeline steps (OneHotEncoder is implicitly needed for subsequent steps like PCA and KNN)
    categorical_transformer = Pipeline(steps=[
        ('onehot', OneHotEncoder(handle_unknown='ignore'))
    ])

    # Create a preprocessor using ColumnTransformer to apply different transformations to different columns
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numerical_transformer, numerical_features),
            ('cat', categorical_transformer, categorical_features)
        ],
        remainder='passthrough' # Keep other columns if any, though not expected here
    )

    # Define the full pipeline
    model_pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('pca', PCA(n_components=n_components, random_state=42)), # Step 4: features
        ('regressor', KNeighborsRegressor(n_neighbors=n_neighbors, weights=weights)) # Step 5: regression
    ])

    return model_pipeline
