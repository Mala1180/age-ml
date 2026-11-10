from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MinMaxScaler
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestClassifier

def build_model(X_train, y_train, feature_range, n_components, n_estimators, max_depth):
    pipeline = Pipeline([
        ('normalization', MinMaxScaler(feature_range=tuple(feature_range))),
        ('features', PCA(n_components=n_components)),
        ('classification', RandomForestClassifier(n_estimators=n_estimators, max_depth=max_depth, random_state=42))
    ])
    return pipeline
