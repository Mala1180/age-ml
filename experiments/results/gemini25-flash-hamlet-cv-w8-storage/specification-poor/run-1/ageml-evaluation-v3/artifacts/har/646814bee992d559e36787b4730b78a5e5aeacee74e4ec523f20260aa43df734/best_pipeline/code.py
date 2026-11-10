from sklearn.impute import SimpleImputer
from sklearn.preprocessing import PowerTransformer
from imblearn.over_sampling import SMOTE
from sklearn.neighbors import KNeighborsClassifier
from imblearn.pipeline import Pipeline

def build_model(X_train, y_train, imputation_strategy, method, k_neighbors, n_neighbors, weights):
    pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy=imputation_strategy)),
        ('scaler', PowerTransformer(method=method)),
        ('smote', SMOTE(k_neighbors=k_neighbors, random_state=42)),
        ('knn', KNeighborsClassifier(n_neighbors=n_neighbors, weights=weights))
    ])
    return pipeline
