# **Created at:** 2026-09-21 01:46:47 UTC

from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.feature_selection import SelectKBest, f_classif
from imblearn.over_sampling import SMOTE
from sklearn.neural_network import MLPClassifier
from imblearn.pipeline import Pipeline as ImbPipeline

def train_model(X_train, y_train, max_iter, k, k_neighbors, hidden_layer_sizes, alpha):
    numeric_features = X_train.select_dtypes(include=['int64', 'float64']).columns
    categorical_features = X_train.select_dtypes(include=['object']).columns
    preprocessor = ColumnTransformer([
        ('num', 'passthrough', numeric_features),
        ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), categorical_features)
    ])
    pipeline = ImbPipeline([
        ('preprocessor', preprocessor),
        ('imputation', IterativeImputer(max_iter=max_iter)),
        ('normalization', StandardScaler()),
        ('features', SelectKBest(score_func=f_classif, k=k)),
        ('rebalancing', SMOTE(k_neighbors=k_neighbors)),
        ('classification', MLPClassifier(hidden_layer_sizes=hidden_layer_sizes, alpha=alpha, max_iter=1000))
    ])
    pipeline.fit(X_train, y_train)
    return pipeline

