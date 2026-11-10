from sklearn.compose import ColumnTransformer
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer, SimpleImputer
from sklearn.preprocessing import RobustScaler, OneHotEncoder
from imblearn.over_sampling import SMOTE
from sklearn.ensemble import RandomForestClassifier
from imblearn.pipeline import Pipeline as ImbPipeline

def build_model(X_train, y_train, max_iter, quantile_range, k_neighbors, n_estimators, max_depth):
    # Define column indices based on the dataset description
    # Numerical columns: 'age', 'fnlwgt', 'education-num', 'capital-gain', 'capital-loss', 'hours-per-week'
    numerical_indices = [0, 2, 4, 10, 11, 12]
    # Categorical columns: 'workclass', 'education', 'marital-status', 'occupation', 'relationship', 'race', 'sex', 'native-country'
    categorical_indices = [1, 3, 5, 6, 7, 8, 9, 13]

    # Preprocessing for numerical features
    numerical_transformer = ImbPipeline(steps=[
        ('imputer', IterativeImputer(max_iter=max_iter, random_state=42)),
        ('scaler', RobustScaler(quantile_range=tuple(quantile_range)))
    ])

    # Preprocessing for categorical features
    # Use SimpleImputer to handle string 'nan' values by filling them with a constant 'missing'
    categorical_transformer = ImbPipeline(steps=[
        ('imputer', SimpleImputer(strategy='constant', fill_value='missing')),
        ('onehot', OneHotEncoder(handle_unknown='ignore'))
    ])

    # Create a preprocessor using ColumnTransformer with integer indices
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numerical_transformer, numerical_indices),
            ('cat', categorical_transformer, categorical_indices)
        ],
        remainder='passthrough'
    )

    # Define the full pipeline
    pipeline = ImbPipeline(steps=[
        ('preprocessor', preprocessor),
        ('smote', SMOTE(random_state=42, k_neighbors=k_neighbors)),
        ('classifier', RandomForestClassifier(random_state=42, n_estimators=n_estimators, max_depth=max_depth))
    ])

    return pipeline
