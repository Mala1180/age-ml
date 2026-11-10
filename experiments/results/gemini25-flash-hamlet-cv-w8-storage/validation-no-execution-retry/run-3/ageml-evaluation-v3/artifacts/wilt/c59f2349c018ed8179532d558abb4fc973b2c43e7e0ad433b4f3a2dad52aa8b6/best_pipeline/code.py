from imblearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.feature_selection import SelectKBest, f_classif
from imblearn.over_sampling import SMOTE
from sklearn.neural_network import MLPClassifier

def build_model(X_train, y_train, imputation_strategy, k, k_neighbors, hidden_layer_sizes, alpha, max_iter):
    pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy=imputation_strategy)),
        ('scaler', StandardScaler()),
        ('selector', SelectKBest(score_func=f_classif, k=k)),
        ('smote', SMOTE(random_state=42, k_neighbors=k_neighbors)),
        ('classifier', MLPClassifier(hidden_layer_sizes=hidden_layer_sizes, alpha=alpha, max_iter=max_iter, random_state=42))
    ])
    return pipeline
