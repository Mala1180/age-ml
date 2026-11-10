from sklearn.preprocessing import RobustScaler
from sklearn.neural_network import MLPClassifier
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline

def build_model(X_train, y_train, quantile_range, k_neighbors, hidden_layer_sizes, alpha, max_iter):
    scaler = RobustScaler(quantile_range=tuple(quantile_range))
    smote = SMOTE(k_neighbors=k_neighbors)
    nn = MLPClassifier(hidden_layer_sizes=hidden_layer_sizes, alpha=alpha, max_iter=max_iter, random_state=42)
    pipeline = Pipeline([
        ('normalization', scaler),
        ('rebalancing', smote),
        ('classification', nn)
    ])
    return pipeline
