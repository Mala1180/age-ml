from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import PowerTransformer
from sklearn.feature_selection import SelectKBest, f_regression
from sklearn.linear_model import Ridge

def build_model(X_train, y_train, imputation_strategy, method, k, alpha):
    pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy=imputation_strategy)),
        ('normalizer', PowerTransformer(method=method)),
        ('feature_selector', SelectKBest(score_func=f_regression, k=k)),
        ('regressor', Ridge(alpha=alpha))
    ])
    return pipeline
