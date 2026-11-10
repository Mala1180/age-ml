from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline

def build_model(X_train, y_train, hidden_layer_sizes, alpha, max_iter):
    pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('nn', MLPClassifier(hidden_layer_sizes=hidden_layer_sizes, alpha=alpha, max_iter=max_iter, random_state=42))
    ])
    return pipeline
