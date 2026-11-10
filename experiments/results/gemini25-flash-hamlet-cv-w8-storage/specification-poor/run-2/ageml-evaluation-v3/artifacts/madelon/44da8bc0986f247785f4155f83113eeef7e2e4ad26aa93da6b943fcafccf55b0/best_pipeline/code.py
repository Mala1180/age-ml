import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.feature_selection import SelectKBest, f_classif
from imblearn.under_sampling import NearMiss
from sklearn.neighbors import KNeighborsClassifier
from imblearn.pipeline import Pipeline as ImbPipeline

def build_model(X_train, y_train, imputation_strategy, k, version, n_neighbors, weights):
    imputer = SimpleImputer(strategy=imputation_strategy)
    selector = SelectKBest(score_func=f_classif, k=k)
    resampler = NearMiss(version=version, n_jobs=-1)
    classifier = KNeighborsClassifier(n_neighbors=n_neighbors, weights=weights)

    pipeline = ImbPipeline(steps=[
        ('imputation', imputer),
        ('feature_selection', selector),
        ('rebalancing', resampler),
        ('classifier', classifier)
    ])

    return pipeline
