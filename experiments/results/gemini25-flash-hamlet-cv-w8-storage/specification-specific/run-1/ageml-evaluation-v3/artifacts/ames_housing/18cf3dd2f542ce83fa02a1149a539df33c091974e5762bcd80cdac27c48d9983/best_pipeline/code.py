from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.feature_selection import SelectKBest, f_regression
from sklearn.ensemble import RandomForestRegressor
from sklearn.compose import ColumnTransformer
import numpy as np

def build_model(X_train, y_train, imputation_strategy, k, n_estimators, max_depth):
    numerical_cols = X_train.select_dtypes(include=np.number).columns

    # Create a preprocessor that applies SimpleImputer to numerical columns
    # and drops all other columns (including categorical ones) to ensure
    # subsequent steps receive only numerical data.
    preprocessor = ColumnTransformer(
        transformers=[
            ('num_imputer', SimpleImputer(strategy=imputation_strategy), numerical_cols)
        ],
        remainder='drop'
    )

    pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('selector', SelectKBest(score_func=f_regression, k=k)),
        ('regressor', RandomForestRegressor(n_estimators=n_estimators, max_depth=max_depth, random_state=42))
    ])
    return pipeline
