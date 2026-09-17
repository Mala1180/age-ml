# **Created at:** 2026-04-23 20:39:44 UTC

from imblearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import KBinsDiscretizer, PowerTransformer
from sklearn.decomposition import PCA
from imblearn.over_sampling import SMOTE
from sklearn.neighbors import KNeighborsClassifier

def train_model(X_train, y_train, imputation_strategy, n_bins, encode, discretization_strategy, method, n_components, k_neighbors, n_neighbors, weights):
    pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy=imputation_strategy)),
        ('discretizer', KBinsDiscretizer(n_bins=n_bins, encode=encode, strategy=discretization_strategy)),
        ('normalizer', PowerTransformer(method=method)),
        ('pca', PCA(n_components=n_components)),
        ('smote', SMOTE(k_neighbors=k_neighbors)),
        ('classifier', KNeighborsClassifier(n_neighbors=n_neighbors, weights=weights))
    ])
    
    model = pipeline.fit(X_train, y_train)
    return model

