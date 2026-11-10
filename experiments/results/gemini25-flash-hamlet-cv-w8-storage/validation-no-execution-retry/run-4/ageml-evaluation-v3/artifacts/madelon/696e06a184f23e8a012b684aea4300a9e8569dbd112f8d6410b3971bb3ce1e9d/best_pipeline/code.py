from sklearn.preprocessing import PowerTransformer
from sklearn.feature_selection import SelectKBest, f_classif
from imblearn.under_sampling import NearMiss
from sklearn.neighbors import KNeighborsClassifier
from imblearn.pipeline import Pipeline

def build_model(X_train, y_train, method, k, version, n_neighbors, weights):
    pipeline_steps = [
        ('power_transformer', PowerTransformer(method=method)),
        ('select_k_best', SelectKBest(score_func=f_classif, k=k)),
        ('near_miss', NearMiss(version=version)),
        ('knn', KNeighborsClassifier(n_neighbors=n_neighbors, weights=weights))
    ]
    pipeline = Pipeline(pipeline_steps)
    return pipeline
