import pandas as pd
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, RobustScaler
from sklearn.impute import SimpleImputer
from sklearn.experimental import enable_iterative_imputer # noqa
from sklearn.impute import IterativeImputer
from sklearn.ensemble import RandomForestClassifier
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline

def build_model(X_train, y_train, max_iter, quantile_range, k_neighbors, n_estimators, max_depth):
    numerical_features = X_train.select_dtypes(include=np.number).columns.tolist()
    categorical_features = X_train.select_dtypes(include='object').columns.tolist()

    numerical_transformer = ImbPipeline(steps=[
        ('imputer', IterativeImputer(max_iter=max_iter, random_state=42)),
        ('scaler', RobustScaler(quantile_range=tuple(quantile_range)))
    ])

    categorical_transformer = ImbPipeline(steps=[
        ('imputer', SimpleImputer(strategy='most_frequent')),
        ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
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
        ('classifier', RandomForestClassifier(random_state=42, n_estimators=n_estimators, max_depth=max_depth))
    ])

    return pipeline
