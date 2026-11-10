from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import MinMaxScaler
from sklearn.decomposition import PCA
from sklearn.neural_network import MLPClassifier

def build_model(X_train, y_train, imputation_strategy, feature_range, n_components, hidden_layer_sizes, alpha, max_iter):
    pipeline = Pipeline([
        ('imputation', SimpleImputer(strategy=imputation_strategy)),
        ('normalization', MinMaxScaler(feature_range=tuple(feature_range))),
        ('features', PCA(n_components=n_components, random_state=42)),
        ('classification', MLPClassifier(hidden_layer_sizes=hidden_layer_sizes, alpha=alpha, max_iter=max_iter, random_state=42))
    ])
    return pipeline
