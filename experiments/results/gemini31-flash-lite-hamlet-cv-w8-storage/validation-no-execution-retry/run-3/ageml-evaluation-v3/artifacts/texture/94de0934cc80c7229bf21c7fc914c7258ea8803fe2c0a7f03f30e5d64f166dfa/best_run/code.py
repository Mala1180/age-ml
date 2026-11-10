from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import PowerTransformer
from sklearn.neural_network import MLPClassifier
from imblearn.pipeline import Pipeline
from imblearn.over_sampling import SMOTE

def build_model(X_train, y_train, max_iter, method, k_neighbors, hidden_layer_sizes, alpha):
    steps = [
        ('imputer', IterativeImputer(max_iter=max_iter, random_state=42)),
        ('scaler', PowerTransformer(method=method)),
        ('smote', SMOTE(k_neighbors=k_neighbors, random_state=42)),
        ('nn', MLPClassifier(hidden_layer_sizes=hidden_layer_sizes, alpha=alpha, max_iter=1000, random_state=42))
    ]
    return Pipeline(steps)
