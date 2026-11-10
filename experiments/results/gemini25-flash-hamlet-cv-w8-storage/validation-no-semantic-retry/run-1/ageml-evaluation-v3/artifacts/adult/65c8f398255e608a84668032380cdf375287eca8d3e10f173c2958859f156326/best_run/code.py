from sklearn.experimental import enable_iterative_imputer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline
from sklearn.neural_network import MLPClassifier
import numpy as np

def build_model(X_train, y_train, max_iter, k_neighbors, hidden_layer_sizes, alpha):
    numerical_features = X_train.select_dtypes(include=np.number).columns.tolist()
    categorical_features = X_train.select_dtypes(include='object').columns.tolist()

    preprocessor_initial = ColumnTransformer(
        transformers=[
            ('num', 'passthrough', numerical_features),
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), categorical_features)
        ],
        remainder='passthrough'
    )

    imputer_step = IterativeImputer(max_iter=max_iter, random_state=42)

    scaler_step = StandardScaler()

    smote_step = SMOTE(random_state=42, k_neighbors=k_neighbors)

    nn_classifier = MLPClassifier(
        hidden_layer_sizes=hidden_layer_sizes,
        alpha=alpha,
        random_state=42
    )

    pipeline = ImbPipeline(steps=[
        ('initial_preprocessing', preprocessor_initial),
        ('imputer', imputer_step),
        ('scaler', scaler_step),
        ('smote', smote_step),
        ('classifier', nn_classifier)
    ])

    return pipeline
