from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline

def build_model(X_train, y_train, n_estimators, max_depth):
    """
    Builds an unfitted machine learning pipeline with a RandomForestClassifier.

    Args:
        X_train: Training features (pandas DataFrame or numpy array).
        y_train: Training target (pandas Series or numpy array).
        n_estimators: The number of trees in the forest.
        max_depth: The maximum depth of the tree.

    Returns:
        An unfitted sklearn-compatible estimator or pipeline.
    """
    pipeline = Pipeline([
        ('random_forest', RandomForestClassifier(n_estimators=n_estimators, max_depth=max_depth, random_state=42))
    ])
    return pipeline
