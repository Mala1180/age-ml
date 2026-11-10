from sklearn.pipeline import Pipeline
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR

def build_model(X_train, y_train, max_iter, kernel, C, epsilon):
    pipeline = Pipeline([
        ('imputer', IterativeImputer(max_iter=max_iter, random_state=42)),
        ('scaler', StandardScaler()),
        ('regressor', SVR(kernel=kernel, C=C, epsilon=epsilon))
    ])
    return pipeline
