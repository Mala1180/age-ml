from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import RobustScaler, OneHotEncoder
from sklearn.feature_selection import SelectKBest, f_classif
from imblearn.over_sampling import SMOTE
from sklearn.neural_network import MLPClassifier
from imblearn.pipeline import Pipeline as ImbPipeline
from sklearn.compose import ColumnTransformer

def build_model(X_train, y_train, max_iter, quantile_range, k, k_neighbors, hidden_layer_sizes, alpha):
    # Ensure quantile_range is a tuple as required by RobustScaler
    if isinstance(quantile_range, list):
        quantile_range = tuple(quantile_range)

    # Identify categorical and numerical features based on the dataset info
    # This assumes X_train is a pandas DataFrame or has consistent column order if it's a numpy array
    # and the ColumnTransformer uses string names.
    categorical_features = ['workclass', 'education', 'marital-status', 'occupation', 'relationship', 'race', 'sex', 'native-country']
    numerical_features = ['age', 'fnlwgt', 'education-num', 'capital-gain', 'capital-loss', 'hours-per-week']

    # Preprocessing step to handle categorical features (OneHotEncoder) and numerical features (passthrough)
    preprocessor = ColumnTransformer(
        transformers=[
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), categorical_features),
            ('num', 'passthrough', numerical_features)
        ],
        remainder='passthrough' # Keep any other columns not explicitly handled
    )

    pipeline = ImbPipeline([
        ('preprocessor', preprocessor),
        ('imputer', IterativeImputer(max_iter=max_iter, random_state=42)),
        ('scaler', RobustScaler(quantile_range=quantile_range)),
        ('selector', SelectKBest(score_func=f_classif, k=k)),
        ('smote', SMOTE(k_neighbors=k_neighbors, random_state=42)),
        ('classifier', MLPClassifier(hidden_layer_sizes=hidden_layer_sizes, alpha=alpha, random_state=42))
    ])
    return pipeline
