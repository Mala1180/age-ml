from imblearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.feature_selection import SelectKBest
from imblearn.over_sampling import SMOTE
from sklearn.ensemble import RandomForestClassifier

def build_model(X_train, y_train, imputation_strategy, k, k_neighbors, n_estimators, max_depth):
    pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy=imputation_strategy)),
        ('selector', SelectKBest(k=k)),
        ('smote', SMOTE(random_state=42, k_neighbors=k_neighbors)),
        ('classifier', RandomForestClassifier(random_state=42, n_estimators=n_estimators, max_depth=max_depth))
    ])
    return pipeline
