from sklearn.pipeline import Pipeline
from sklearn.preprocessing import KBinsDiscretizer, MinMaxScaler
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.ensemble import RandomForestClassifier

def build_model(X_train, y_train, n_bins, encode, discretization_strategy, feature_range, k, n_estimators, max_depth):
    pipeline = Pipeline([
        ('discretization', KBinsDiscretizer(n_bins=n_bins, encode=encode, strategy=discretization_strategy, subsample=200000, random_state=42)),
        ('normalization', MinMaxScaler(feature_range=tuple(feature_range))),
        ('features', SelectKBest(score_func=f_classif, k=k)),
        ('classification', RandomForestClassifier(n_estimators=n_estimators, max_depth=max_depth, random_state=42))
    ])
    return pipeline
