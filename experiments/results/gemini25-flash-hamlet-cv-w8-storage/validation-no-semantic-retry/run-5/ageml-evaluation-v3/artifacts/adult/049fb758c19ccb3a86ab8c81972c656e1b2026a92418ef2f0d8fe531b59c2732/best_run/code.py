import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer, SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from imblearn.over_sampling import SMOTE
from sklearn.neural_network import MLPClassifier
from imblearn.pipeline import Pipeline as ImbPipeline

def build_model(X_train, y_train, max_iter, k_neighbors, hidden_layer_sizes, alpha):
    numerical_features = X_train.select_dtypes(include=['int64', 'float64']).columns
    categorical_features = X_train.select_dtypes(include=['object', 'category']).columns

    preprocessor = ColumnTransformer(
        transformers=[
            ('num_imputer', IterativeImputer(max_iter=max_iter, random_state=42), numerical_features),
            ('cat_imputer_encoder', Pipeline([
                ('imputer', SimpleImputer(strategy='most_frequent')),
                ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
            ]), categorical_features)
        ],
        remainder='drop'
    )

    pipeline = ImbPipeline([
        ('preprocessor', preprocessor),
        ('scaler', StandardScaler()),
        ('smote', SMOTE(random_state=42, k_neighbors=k_neighbors)),
        ('classifier', MLPClassifier(random_state=42, hidden_layer_sizes=hidden_layer_sizes, alpha=alpha, max_iter=1000))
    ])

    return pipeline
