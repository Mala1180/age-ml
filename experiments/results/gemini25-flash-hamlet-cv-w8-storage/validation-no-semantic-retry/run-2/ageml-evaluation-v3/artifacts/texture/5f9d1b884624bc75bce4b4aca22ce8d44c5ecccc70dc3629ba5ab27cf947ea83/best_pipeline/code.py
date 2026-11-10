from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import PowerTransformer
from imblearn.over_sampling import SMOTE
from sklearn.neural_network import MLPClassifier
from imblearn.pipeline import Pipeline

def build_model(X_train, y_train, max_iter, method, k_neighbors, hidden_layer_sizes, alpha):
    steps = [
        ('imputation', IterativeImputer(random_state=42)),
        ('normalization', PowerTransformer(method=method)),
        ('rebalancing', SMOTE(random_state=42, k_neighbors=k_neighbors)),
        ('classification', MLPClassifier(random_state=42, max_iter=max_iter,
                                         hidden_layer_sizes=hidden_layer_sizes,
                                         alpha=alpha))
    ]
    pipeline = Pipeline(steps=steps)
    return pipeline
