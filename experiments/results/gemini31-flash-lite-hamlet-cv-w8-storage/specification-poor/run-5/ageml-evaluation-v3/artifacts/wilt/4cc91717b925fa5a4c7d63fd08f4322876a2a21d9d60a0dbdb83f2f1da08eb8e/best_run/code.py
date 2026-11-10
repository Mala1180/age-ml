from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import PowerTransformer
from sklearn.tree import DecisionTreeClassifier
from imblearn.pipeline import Pipeline as ImbPipeline
from imblearn.over_sampling import SMOTE

def build_model(X_train, y_train, imputation_strategy, method, k_neighbors, max_depth, min_samples_split):
    steps = [
        ('imputation', SimpleImputer(strategy=imputation_strategy)),
        ('normalization', PowerTransformer(method=method)),
        ('rebalancing', SMOTE(k_neighbors=k_neighbors)),
        ('classification', DecisionTreeClassifier(max_depth=max_depth, min_samples_split=min_samples_split))
    ]
    return ImbPipeline(steps)
