from imblearn.pipeline import Pipeline
from sklearn.preprocessing import RobustScaler
from imblearn.over_sampling import SMOTE
from sklearn.neural_network import MLPClassifier

def build_model(X_train, y_train, quantile_range, k_neighbors, hidden_layer_sizes, alpha, max_iter):
    pipeline = Pipeline([
        ('scaler', RobustScaler(quantile_range=tuple(quantile_range))),
        ('smote', SMOTE(k_neighbors=k_neighbors, random_state=42)),
        ('nn', MLPClassifier(hidden_layer_sizes=hidden_layer_sizes, alpha=alpha, max_iter=max_iter, random_state=42))
    ])
    return pipeline
