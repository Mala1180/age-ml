from sklearn.pipeline import Pipeline
from sklearn.preprocessing import KBinsDiscretizer, RobustScaler
from sklearn.decomposition import PCA
from sklearn.neighbors import KNeighborsClassifier

def build_model(X_train, y_train, n_bins, encode, discretization_strategy, quantile_range, n_components, n_neighbors, weights):
    pipeline = Pipeline([
        ('discretization', KBinsDiscretizer(n_bins=n_bins, encode=encode, strategy=discretization_strategy)),
        ('normalization', RobustScaler(quantile_range=tuple(quantile_range))),
        ('features', PCA(n_components=n_components)),
        ('classification', KNeighborsClassifier(n_neighbors=n_neighbors, weights=weights))
    ])
    return pipeline
