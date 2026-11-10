from imblearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import PowerTransformer
from imblearn.over_sampling import SMOTE
from sklearn.neighbors import KNeighborsClassifier

def build_model(X_train, y_train, imputation_strategy, method, k_neighbors, n_neighbors, weights):
    imputer = SimpleImputer(strategy=imputation_strategy)
    normalizer = PowerTransformer(method=method)
    smote = SMOTE(k_neighbors=k_neighbors, random_state=42)
    classifier = KNeighborsClassifier(n_neighbors=n_neighbors, weights=weights)

    pipeline = Pipeline(steps=[
        ('imputer', imputer),
        ('normalizer', normalizer),
        ('smote', smote),
        ('classifier', classifier)
    ])

    return pipeline
