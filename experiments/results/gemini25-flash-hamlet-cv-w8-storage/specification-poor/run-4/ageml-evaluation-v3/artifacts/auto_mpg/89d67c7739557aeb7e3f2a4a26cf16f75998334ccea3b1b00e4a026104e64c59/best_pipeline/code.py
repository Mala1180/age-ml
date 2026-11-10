from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import KBinsDiscretizer, PowerTransformer
from sklearn.decomposition import PCA
from sklearn.svm import SVR

def build_model(X_train, y_train, imputation_strategy, n_bins, encode, discretization_strategy, method, n_components, kernel, C, epsilon):
    pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy=imputation_strategy)),
        ('discretizer', KBinsDiscretizer(n_bins=n_bins, encode=encode, strategy=discretization_strategy, subsample=None)),
        ('normalizer', PowerTransformer(method=method)),
        ('pca', PCA(n_components=n_components, random_state=42)),
        ('regressor', SVR(kernel=kernel, C=C, epsilon=epsilon))
    ])
    return pipeline
