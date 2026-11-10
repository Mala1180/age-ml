from sklearn.experimental import enable_iterative_imputer
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import IterativeImputer, SimpleImputer
from sklearn.preprocessing import PowerTransformer, OneHotEncoder
from imblearn.over_sampling import SMOTE
from sklearn.neural_network import MLPClassifier
from imblearn.pipeline import Pipeline as ImbPipeline

def build_model(X_train, y_train, max_iter, method, k_neighbors, hidden_layer_sizes, alpha):
    numerical_features = X_train.select_dtypes(include=['int64', 'float64']).columns
    categorical_features = X_train.select_dtypes(include=['object', 'str']).columns

    numerical_transformer = Pipeline(steps=[
        ('imputer', IterativeImputer(max_iter=max_iter, random_state=42)),
        ('scaler', PowerTransformer(method=method))
    ])

    categorical_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='most_frequent')),
        ('onehot', OneHotEncoder(handle_unknown='ignore'))
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numerical_transformer, numerical_features),
            ('cat', categorical_transformer, categorical_features)
        ],
        remainder='passthrough'
    )

    pipeline = ImbPipeline(steps=[
        ('preprocessor', preprocessor),
        ('smote', SMOTE(random_state=42, k_neighbors=k_neighbors)),
        ('classifier', MLPClassifier(hidden_layer_sizes=hidden_layer_sizes, alpha=alpha, random_state=42, max_iter=1000))
    ])

    return pipeline
