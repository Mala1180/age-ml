from sklearn.impute import SimpleImputer
from sklearn.preprocessing import MinMaxScaler
from sklearn.decomposition import PCA
from sklearn.neighbors import KNeighborsClassifier
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline

def build_model(X_train, y_train, imputation_strategy, feature_range, n_components, k_neighbors, n_neighbors, weights):
    steps = [
        ('imputer', SimpleImputer(strategy=imputation_strategy)),
        ('scaler', MinMaxScaler(feature_range=tuple(feature_range))),
        ('pca', PCA(n_components=n_components)),
        ('smote', SMOTE(k_neighbors=k_neighbors)),
        ('knn', KNeighborsClassifier(n_neighbors=n_neighbors, weights=weights))
    ]
    return Pipeline(steps)
