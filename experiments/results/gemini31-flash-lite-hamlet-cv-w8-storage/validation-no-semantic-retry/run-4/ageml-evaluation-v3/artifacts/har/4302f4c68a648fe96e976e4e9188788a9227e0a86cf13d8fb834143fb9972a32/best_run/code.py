from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MinMaxScaler
from sklearn.neural_network import MLPClassifier

def build_model(X_train, y_train, feature_range, hidden_layer_sizes, alpha, max_iter):
    pipeline = Pipeline([
        ('normalization', MinMaxScaler(feature_range=tuple(feature_range))),
        ('classification', MLPClassifier(hidden_layer_sizes=hidden_layer_sizes, alpha=alpha, max_iter=max_iter, random_state=42))
    ])
    return pipeline
