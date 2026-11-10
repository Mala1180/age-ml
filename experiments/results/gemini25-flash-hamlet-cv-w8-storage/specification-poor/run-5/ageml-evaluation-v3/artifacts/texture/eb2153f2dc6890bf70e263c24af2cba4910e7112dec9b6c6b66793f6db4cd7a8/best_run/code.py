from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline

def build_model(X_train, y_train, max_iter, n_neighbors, weights):
    pipeline = Pipeline([
        ('imputation', IterativeImputer(max_iter=max_iter, random_state=42)),
        ('knn', KNeighborsClassifier(n_neighbors=n_neighbors, weights=weights))
    ])
    return pipeline
