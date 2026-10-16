# **Created at:** 2026-09-20 18:06:32 UTC

from sklearn.impute import SimpleImputer
from sklearn.preprocessing import KBinsDiscretizer, StandardScaler
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.ensemble import RandomForestClassifier
from imblearn.under_sampling import NearMiss
from imblearn.pipeline import Pipeline as ImbPipeline

def train_model(X_train, y_train, imputation_strategy, n_bins, encode, discretization_strategy, k, version, n_estimators, max_depth):
    steps = [
        ('imputation', SimpleImputer(strategy=imputation_strategy)),
        ('discretization', KBinsDiscretizer(n_bins=n_bins, encode=encode, strategy=discretization_strategy)),
        ('normalization', StandardScaler()),
        ('features', SelectKBest(score_func=f_classif, k=k)),
        ('rebalancing', NearMiss(version=version)),
        ('classification', RandomForestClassifier(n_estimators=n_estimators, max_depth=max_depth))
    ]
    pipeline = ImbPipeline(steps)
    pipeline.fit(X_train, y_train)
    return pipeline

