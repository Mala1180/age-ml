# **Created at:** 2026-04-23 22:44:09 UTC

from sklearn.pipeline import Pipeline
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import ElasticNet

def train_model(X_train, y_train, max_iter, alpha, l1_ratio):
    numerical_features = X_train.select_dtypes(include=['number']).columns
    categorical_features = X_train.select_dtypes(include=['object', 'category']).columns

    numerical_transformer = Pipeline(steps=[
        ('imputer', IterativeImputer(max_iter=max_iter, random_state=0)),
        ('scaler', StandardScaler())
    ])

    categorical_transformer = OneHotEncoder(handle_unknown='ignore')

    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numerical_transformer, numerical_features),
            ('cat', categorical_transformer, categorical_features)
        ],
        remainder='passthrough'
    )

    pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('regression', ElasticNet(alpha=alpha, l1_ratio=l1_ratio, random_state=0))
    ])

    pipeline.fit(X_train, y_train)
    return pipeline

