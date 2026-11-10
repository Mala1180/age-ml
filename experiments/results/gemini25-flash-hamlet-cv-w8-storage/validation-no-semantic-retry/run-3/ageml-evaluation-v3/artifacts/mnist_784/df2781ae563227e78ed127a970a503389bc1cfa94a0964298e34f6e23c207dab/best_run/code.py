from imblearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import MinMaxScaler
from sklearn.decomposition import PCA
from imblearn.over_sampling import SMOTE
from sklearn.neighbors import KNeighborsClassifier

def build_model(X_train, y_train, imputation_strategy, feature_range, n_components, k_neighbors, n_neighbors, weights):
    pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy=imputation_strategy)),
        ('scaler', MinMaxScaler(feature_range=tuple(feature_range))),
        ('pca', PCA(n_components=n_components, random_state=42)),
        ('smote', SMOTE(k_neighbors=k_neighbors, random_state=42)),
        ('knn', KNeighborsClassifier(n_neighbors=n_neighbors, weights=weights))
    ])
    return pipeline
