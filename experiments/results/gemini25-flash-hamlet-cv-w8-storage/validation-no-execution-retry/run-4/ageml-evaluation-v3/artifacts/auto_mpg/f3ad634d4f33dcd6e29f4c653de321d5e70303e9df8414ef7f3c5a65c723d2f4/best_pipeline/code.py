from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import KBinsDiscretizer, StandardScaler
from sklearn.decomposition import PCA
from sklearn.neighbors import KNeighborsRegressor
from sklearn.pipeline import Pipeline

def build_model(X_train, y_train, max_iter, n_bins, encode, discretization_strategy, n_components, n_neighbors, weights):
    pipeline = Pipeline([
        ('imputer', IterativeImputer(max_iter=max_iter, random_state=42)),
        ('discretizer', KBinsDiscretizer(n_bins=n_bins, encode=encode, strategy=discretization_strategy)),
        ('scaler', StandardScaler()),
        ('pca', PCA(n_components=n_components, random_state=42)),
        ('regressor', KNeighborsRegressor(n_neighbors=n_neighbors, weights=weights))
    ])
    return pipeline
