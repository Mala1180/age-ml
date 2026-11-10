from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import PowerTransformer
from sklearn.decomposition import PCA
from sklearn.linear_model import ElasticNet

def build_model(X_train, y_train, imputation_strategy, method, n_components, alpha, l1_ratio):
    pipeline = Pipeline([
        ('imputation', SimpleImputer(strategy=imputation_strategy)),
        ('normalization', PowerTransformer(method=method)),
        ('features', PCA(n_components=n_components)),
        ('regression', ElasticNet(alpha=alpha, l1_ratio=l1_ratio))
    ])
    return pipeline
