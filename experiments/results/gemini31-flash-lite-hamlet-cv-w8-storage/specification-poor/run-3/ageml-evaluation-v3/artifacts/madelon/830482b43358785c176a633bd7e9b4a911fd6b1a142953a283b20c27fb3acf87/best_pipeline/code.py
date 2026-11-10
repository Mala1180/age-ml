from sklearn.impute import SimpleImputer
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.neighbors import KNeighborsClassifier
from imblearn.under_sampling import NearMiss
from imblearn.pipeline import Pipeline

def build_model(X_train, y_train, imputation_strategy, k, version, n_neighbors, weights):
    steps = [
        ('imputation', SimpleImputer(strategy=imputation_strategy)),
        ('features', SelectKBest(score_func=f_classif, k=k)),
        ('rebalancing', NearMiss(version=version)),
        ('classification', KNeighborsClassifier(n_neighbors=n_neighbors, weights=weights))
    ]
    return Pipeline(steps)
