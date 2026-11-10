from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MinMaxScaler
from sklearn.neural_network import MLPClassifier

def build_model(X_train, y_train, feature_range, hidden_layer_sizes, alpha, max_iter):
    # Ensure feature_range is a tuple as required by MinMaxScaler
    feature_range_tuple = tuple(feature_range)
    
    pipeline = Pipeline([
        ('normalize', MinMaxScaler(feature_range=feature_range_tuple)),
        ('nn', MLPClassifier(hidden_layer_sizes=hidden_layer_sizes, alpha=alpha, max_iter=max_iter, random_state=42))
    ])
    return pipeline
