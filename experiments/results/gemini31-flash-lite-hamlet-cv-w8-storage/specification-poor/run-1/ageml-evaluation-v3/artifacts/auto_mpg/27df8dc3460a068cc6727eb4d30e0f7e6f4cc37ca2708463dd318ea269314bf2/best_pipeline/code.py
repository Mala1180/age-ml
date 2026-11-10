from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import KBinsDiscretizer, PowerTransformer
from sklearn.decomposition import PCA
from sklearn.svm import SVR

def build_model(X_train, y_train, imputation_strategy, n_bins, encode, discretization_strategy, method, n_components, kernel, C, epsilon):
    pipeline = Pipeline([
        ('imputation', SimpleImputer(strategy=imputation_strategy)),
        ('discretization', KBinsDiscretizer(n_bins=n_bins, encode=encode, strategy=discretization_strategy)),
        ('normalization', PowerTransformer(method=method)),
        ('features', PCA(n_components=n_components)),
        ('regression', SVR(kernel=kernel, C=C, epsilon=epsilon))
    ])
    return pipeline
