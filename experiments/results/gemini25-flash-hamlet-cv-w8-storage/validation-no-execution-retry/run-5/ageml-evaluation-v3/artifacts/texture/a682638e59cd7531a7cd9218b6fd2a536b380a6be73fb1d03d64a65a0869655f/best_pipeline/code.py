from imblearn.pipeline import Pipeline
from sklearn.preprocessing import KBinsDiscretizer
from imblearn.under_sampling import NearMiss
from sklearn.ensemble import RandomForestClassifier

def build_model(X_train, y_train, n_bins, encode, discretization_strategy, version, n_estimators, max_depth):
    pipeline = Pipeline([
        ('discretization', KBinsDiscretizer(n_bins=n_bins, encode=encode, strategy=discretization_strategy)),
        ('rebalancing', NearMiss(version=version)),
        ('classifier', RandomForestClassifier(n_estimators=n_estimators, max_depth=max_depth))
    ])
    return pipeline
