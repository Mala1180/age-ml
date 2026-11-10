from sklearn.impute import SimpleImputer
from sklearn.preprocessing import PowerTransformer
from imblearn.over_sampling import SMOTE
from sklearn.tree import DecisionTreeClassifier
from imblearn.pipeline import Pipeline

def build_model(X_train, y_train, imputation_strategy, method, k_neighbors, max_depth, min_samples_split):
    pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy=imputation_strategy)),
        ('normalizer', PowerTransformer(method=method)),
        ('smote', SMOTE(random_state=42, k_neighbors=k_neighbors)),
        ('classifier', DecisionTreeClassifier(random_state=42, max_depth=max_depth, min_samples_split=min_samples_split))
    ])
    return pipeline
