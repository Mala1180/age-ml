from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import Binarizer, RobustScaler
from sklearn.ensemble import RandomForestClassifier

def build_model(X_train, y_train, imputation_strategy, threshold, quantile_range, n_estimators, max_depth):
    # Ensure quantile_range is a tuple as required by RobustScaler
    quantile_range_tuple = tuple(quantile_range)

    pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy=imputation_strategy)),
        ('binarizer', Binarizer(threshold=threshold)),
        ('scaler', RobustScaler(quantile_range=quantile_range_tuple)),
        ('classifier', RandomForestClassifier(n_estimators=n_estimators, max_depth=max_depth, random_state=42))
    ])
    return pipeline
