from imblearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import RobustScaler
from sklearn.feature_selection import SelectKBest, f_classif
from imblearn.over_sampling import SMOTE
from sklearn.neighbors import KNeighborsClassifier

def build_model(X_train, y_train, imputation_strategy, quantile_range, k, k_neighbors, n_neighbors, weights):
    pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy=imputation_strategy)),
        ('scaler', RobustScaler(quantile_range=tuple(quantile_range))), # Ensure quantile_range is a tuple
        ('selector', SelectKBest(score_func=f_classif, k=k)),
        ('smote', SMOTE(k_neighbors=k_neighbors, random_state=42)),
        ('classifier', KNeighborsClassifier(n_neighbors=n_neighbors, weights=weights))
    ])
    return pipeline
