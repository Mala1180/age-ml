from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline
from sklearn.neural_network import MLPClassifier
import numpy as np

def build_model(X_train, y_train, imputation_strategy, k_neighbors, hidden_layer_sizes, alpha, max_iter):
    # Identify numerical and categorical features
    numerical_features = X_train.select_dtypes(include=np.number).columns
    categorical_features = X_train.select_dtypes(include='object').columns

    # Preprocessing for numerical features
    numerical_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy=imputation_strategy)),
        ('scaler', StandardScaler())
    ])

    # Preprocessing for categorical features
    # For categorical features, 'most_frequent' is a common and robust imputation strategy.
    categorical_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='most_frequent')),
        ('onehot', OneHotEncoder(handle_unknown='ignore'))
    ])

    # Create a preprocessor using ColumnTransformer
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numerical_transformer, numerical_features),
            ('cat', categorical_transformer, categorical_features)
        ],
        remainder='passthrough'
    )

    # Define the full pipeline using imblearn's Pipeline to correctly handle SMOTE
    model_pipeline = ImbPipeline(steps=[
        ('preprocessor', preprocessor),
        ('smote', SMOTE(random_state=42, k_neighbors=k_neighbors)),
        ('classifier', MLPClassifier(hidden_layer_sizes=hidden_layer_sizes,
                                     alpha=alpha,
                                     max_iter=max_iter,
                                     random_state=42))
    ])

    return model_pipeline
