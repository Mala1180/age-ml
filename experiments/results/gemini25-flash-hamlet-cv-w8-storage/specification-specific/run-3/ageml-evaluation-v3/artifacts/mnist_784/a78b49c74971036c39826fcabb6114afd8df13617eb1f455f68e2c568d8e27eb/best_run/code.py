from sklearn.ensemble import RandomForestClassifier

def build_model(X_train, y_train, n_estimators, max_depth):
    """
    Builds an unfitted RandomForestClassifier model.

    Args:
        X_train: Training features (pandas DataFrame or numpy array)
        y_train: Training target (pandas Series or numpy array)
        n_estimators: Number of trees in the forest.
        max_depth: Maximum depth of the tree.

    Returns:
        An unfitted sklearn-compatible RandomForestClassifier estimator.
    """
    model = RandomForestClassifier(n_estimators=n_estimators, max_depth=max_depth, random_state=42)
    return model
