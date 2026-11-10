import pandas as pd
from imblearn.pipeline import Pipeline as ImbPipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import IterativeImputer, SimpleImputer
from sklearn.preprocessing import RobustScaler, OneHotEncoder
from imblearn.over_sampling import SMOTE
from sklearn.neural_network import MLPClassifier

def build_model(X_train, y_train, max_iter, quantile_range, k_neighbors, hidden_layer_sizes, alpha):
    numerical_cols = ['age', 'fnlwgt', 'education-num', 'capital-gain', 'capital-loss', 'hours-per-week']
    categorical_cols = ['workclass', 'education', 'marital-status', 'occupation', 'relationship', 'race', 'sex', 'native-country']

    numerical_transformer = ImbPipeline(steps=[
        ('imputer', IterativeImputer(max_iter=max_iter, random_state=42)),
        ('scaler', RobustScaler(quantile_range=tuple(quantile_range)))
    ])

    categorical_transformer = ImbPipeline(steps=[
        ('imputer', SimpleImputer(strategy='most_frequent')),
        ('onehot', OneHotEncoder(handle_unknown='ignore'))
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numerical_transformer, numerical_cols),
            ('cat', categorical_transformer, categorical_cols)
        ],
        remainder='passthrough'
    )

    pipeline_steps = [
        ('preprocessor', preprocessor),
        ('smote', SMOTE(k_neighbors=k_neighbors, random_state=42)),
        ('classifier', MLPClassifier(hidden_layer_sizes=hidden_layer_sizes, alpha=alpha, random_state=42, max_iter=200))
    ]
    pipeline = ImbPipeline(steps=pipeline_steps)
    return pipeline
