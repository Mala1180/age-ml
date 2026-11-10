from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import Binarizer
from sklearn.ensemble import RandomForestClassifier

def build_model(X_train, y_train, imputation_strategy, threshold, n_estimators, max_depth):
    pipeline = Pipeline([
        ('imputation', SimpleImputer(strategy=imputation_strategy)),
        ('binarizer', Binarizer(threshold=threshold)),
        ('random_forest', RandomForestClassifier(n_estimators=n_estimators, max_depth=max_depth, random_state=42))
    ])
    return pipeline
