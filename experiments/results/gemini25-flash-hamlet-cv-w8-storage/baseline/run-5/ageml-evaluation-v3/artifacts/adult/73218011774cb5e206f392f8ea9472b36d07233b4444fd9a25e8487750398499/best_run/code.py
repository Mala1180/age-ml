from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import IterativeImputer, SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline
from sklearn.neural_network import MLPClassifier
import numpy as np
from sklearn.experimental import enable_iterative_imputer # Required for IterativeImputer

def build_model(X_train, y_train, max_iter, k_neighbors, hidden_layer_sizes, alpha):
    numerical_features = X_train.select_dtypes(include=np.number).columns.tolist()
    categorical_features = X_train.select_dtypes(include='object').columns.tolist()

    categorical_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='most_frequent')),
        ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False)) # Ensure dense output
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ('cat', categorical_transformer, categorical_features),
            ('num', 'passthrough', numerical_features)
        ],
        remainder='drop'
    )

    pipeline = ImbPipeline(steps=[
        ('preprocessor', preprocessor),
        ('iterative_imputer', IterativeImputer(max_iter=max_iter, random_state=42)),
        ('scaler', StandardScaler()),
        ('smote', SMOTE(random_state=42, k_neighbors=k_neighbors)),
        ('classifier', MLPClassifier(
            hidden_layer_sizes=hidden_layer_sizes,
            alpha=alpha,
            random_state=42
        ))
    ])

    return pipeline
