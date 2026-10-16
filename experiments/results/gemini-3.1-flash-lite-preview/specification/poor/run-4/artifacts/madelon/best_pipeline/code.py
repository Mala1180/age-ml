# **Created at:** 2026-09-21 05:53:26 UTC

import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import KBinsDiscretizer, StandardScaler
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.tree import DecisionTreeClassifier
from imblearn.under_sampling import NearMiss
from imblearn.pipeline import Pipeline as ImbPipeline

def train_model(X_train, y_train, imputation_strategy, n_bins, encode, discretization_strategy, k, version, max_depth, min_samples_split):
    pipeline = ImbPipeline([
        ('imputation', SimpleImputer(strategy=imputation_strategy)),
        ('discretization', KBinsDiscretizer(n_bins=n_bins, encode=encode, strategy=discretization_strategy)),
        ('normalization', StandardScaler()),
        ('features', SelectKBest(score_func=f_classif, k=k)),
        ('rebalancing', NearMiss(version=version)),
        ('classification', DecisionTreeClassifier(max_depth=max_depth, min_samples_split=min_samples_split))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

