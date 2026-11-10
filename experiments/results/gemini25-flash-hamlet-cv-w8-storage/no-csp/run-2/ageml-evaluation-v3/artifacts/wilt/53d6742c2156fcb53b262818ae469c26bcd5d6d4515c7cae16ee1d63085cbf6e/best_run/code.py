from sklearn.pipeline import Pipeline
from sklearn.feature_selection import SelectKBest
from sklearn.ensemble import RandomForestClassifier

def build_model(X_train, y_train, k, n_estimators, max_depth):
    pipeline = Pipeline([
        ('feature_selection', SelectKBest(k=k)),
        ('classifier', RandomForestClassifier(n_estimators=n_estimators, max_depth=max_depth, random_state=42))
    ])
    return pipeline
