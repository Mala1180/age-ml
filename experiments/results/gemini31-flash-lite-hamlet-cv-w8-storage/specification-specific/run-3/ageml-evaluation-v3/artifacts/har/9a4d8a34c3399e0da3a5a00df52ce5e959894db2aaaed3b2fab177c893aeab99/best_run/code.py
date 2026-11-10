from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PowerTransformer
from sklearn.neural_network import MLPClassifier

def build_model(X_train, y_train, method, hidden_layer_sizes, alpha, max_iter):
    pipeline = Pipeline([
        ('normalization', PowerTransformer(method=method)),
        ('classification', MLPClassifier(hidden_layer_sizes=hidden_layer_sizes, alpha=alpha, max_iter=max_iter, random_state=42))
    ])
    return pipeline
