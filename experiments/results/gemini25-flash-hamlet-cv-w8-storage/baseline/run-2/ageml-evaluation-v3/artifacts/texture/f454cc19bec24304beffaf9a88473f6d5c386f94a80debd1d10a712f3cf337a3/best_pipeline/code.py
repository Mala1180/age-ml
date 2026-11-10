from sklearn.impute import IterativeImputer
from sklearn.preprocessing import StandardScaler
from imblearn.over_sampling import SMOTE
from sklearn.neural_network import MLPClassifier
from imblearn.pipeline import Pipeline

def build_model(X_train, y_train, max_iter, k_neighbors, hidden_layer_sizes, alpha):
    pipeline_steps = [
        ('imputer', IterativeImputer(max_iter=max_iter, random_state=42)),
        ('scaler', StandardScaler()),
        ('smote', SMOTE(k_neighbors=k_neighbors, random_state=42)),
        ('classifier', MLPClassifier(hidden_layer_sizes=hidden_layer_sizes, alpha=alpha, max_iter=max_iter, random_state=42))
    ]
    pipeline = Pipeline(pipeline_steps)
    return pipeline
