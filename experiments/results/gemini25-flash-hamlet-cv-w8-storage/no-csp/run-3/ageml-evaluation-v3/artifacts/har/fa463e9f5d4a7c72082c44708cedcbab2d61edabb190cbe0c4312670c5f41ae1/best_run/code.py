from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from imblearn.over_sampling import SMOTE
from sklearn.neural_network import MLPClassifier
from imblearn.pipeline import Pipeline as ImbPipeline

def build_model(X_train, y_train, imputation_strategy, n_components, k_neighbors, hidden_layer_sizes, alpha, max_iter):
    pipeline = ImbPipeline([
        ('imputation', SimpleImputer(strategy=imputation_strategy)),
        ('scaler', StandardScaler()),
        ('pca', PCA(n_components=n_components, random_state=42)),
        ('smote', SMOTE(k_neighbors=k_neighbors, random_state=42)),
        ('nn', MLPClassifier(hidden_layer_sizes=hidden_layer_sizes, alpha=alpha, max_iter=max_iter, random_state=42))
    ])
    return pipeline
