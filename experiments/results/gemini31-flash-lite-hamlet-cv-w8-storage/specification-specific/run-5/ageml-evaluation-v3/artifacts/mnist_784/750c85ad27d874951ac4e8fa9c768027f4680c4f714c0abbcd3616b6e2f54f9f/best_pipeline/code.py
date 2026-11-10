from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier

def build_model(X_train, y_train, n_estimators, max_depth):
    pipeline = Pipeline([
        ('classification', RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=42
        ))
    ])
    return pipeline
