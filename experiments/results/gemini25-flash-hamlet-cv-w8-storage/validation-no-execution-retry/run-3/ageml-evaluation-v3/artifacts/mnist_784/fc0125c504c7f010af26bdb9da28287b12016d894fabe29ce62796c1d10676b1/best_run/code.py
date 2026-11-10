from sklearn.pipeline import Pipeline
from sklearn.preprocessing import KBinsDiscretizer, PowerTransformer
from sklearn.decomposition import PCA
from sklearn.neighbors import KNeighborsClassifier

def build_model(X_train, y_train, n_bins, encode, discretization_strategy, method, n_components, n_neighbors, weights):
    pipeline = Pipeline([
        ('discretization', KBinsDiscretizer(n_bins=n_bins, encode=encode, strategy=discretization_strategy, random_state=42)),
        ('normalization', PowerTransformer(method=method)),
        ('features', PCA(n_components=n_components, random_state=42)),
        ('classification', KNeighborsClassifier(n_neighbors=n_neighbors, weights=weights))
    ])
    return pipeline
