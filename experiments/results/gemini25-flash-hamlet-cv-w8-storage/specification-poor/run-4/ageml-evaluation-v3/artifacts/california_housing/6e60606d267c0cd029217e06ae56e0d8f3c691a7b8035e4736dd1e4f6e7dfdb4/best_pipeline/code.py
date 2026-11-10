from sklearn.pipeline import Pipeline
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import KBinsDiscretizer, RobustScaler, OneHotEncoder
from sklearn.ensemble import RandomForestRegressor
from sklearn.compose import ColumnTransformer

def build_model(X_train, y_train, max_iter, n_bins, encode, discretization_strategy, quantile_range, n_estimators, max_depth):
    
    numerical_features = X_train.select_dtypes(include=['int64', 'float64']).columns
    categorical_features = X_train.select_dtypes(include=['object', 'category']).columns

    numerical_transformer = Pipeline([
        ('imputer', IterativeImputer(max_iter=max_iter, random_state=42)),
        ('discretizer', KBinsDiscretizer(n_bins=n_bins, encode=encode, strategy=discretization_strategy)),
        ('scaler', RobustScaler(quantile_range=tuple(quantile_range)))
    ])

    categorical_transformer = Pipeline([
        ('onehot', OneHotEncoder(handle_unknown='ignore'))
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numerical_transformer, numerical_features),
            ('cat', categorical_transformer, categorical_features)
        ],
        remainder='passthrough'
    )

    pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('regressor', RandomForestRegressor(n_estimators=n_estimators, max_depth=max_depth, random_state=42))
    ])
    return pipeline
