import sys
import unittest

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))
from scripts._compliance_static import Factory, Unsupported, graph_nodes, graph_paths


class AuditTests(unittest.TestCase):
    def graph(self, code, params=None, n=3, c=0):
        return Factory(code, n, c, params or {}).run()

    def test_keyword_expansion_is_bound(self):
        m = self.graph(
            'from sklearn.preprocessing import KBinsDiscretizer\ndef build_model(X_train,y_train,n_bins,encode,discretization_strategy):\n p={"n_bins":n_bins,"encode":encode,"strategy":discretization_strategy}\n return KBinsDiscretizer(**p)',
            {"n_bins": 10, "encode": "ordinal", "discretization_strategy": "quantile"},
        )
        self.assertEqual(
            m.kwargs, {"n_bins": 10, "encode": "ordinal", "strategy": "quantile"}
        )

    def test_only_returned_components_count(self):
        m = self.graph(
            "from sklearn.svm import SVC\nfrom sklearn.neural_network import MLPClassifier\ndef build_model(X_train,y_train):\n ignored=SVC()\n return MLPClassifier(max_iter=300)"
        )
        self.assertEqual([x.name for x in graph_nodes(m)], ["MLPClassifier"])

    def test_empty_categorical_branch_not_a_violation(self):
        s = 'from sklearn.compose import ColumnTransformer\nfrom sklearn.preprocessing import OneHotEncoder,StandardScaler\ndef build_model(X_train,y_train):\n num=X_train.select_dtypes(include=["number"]).columns\n cat=X_train.select_dtypes(include=["object"]).columns\n return ColumnTransformer([("num",StandardScaler(),num),("cat",OneHotEncoder(),cat)])'
        self.assertEqual(
            [x.name for x in graph_nodes(self.graph(s))], ["StandardScaler"]
        )
        self.assertEqual(
            [x.name for x in graph_nodes(self.graph(s, c=1))],
            ["StandardScaler", "OneHotEncoder"],
        )

    def test_internal_imputer_estimator_not_a_pipeline_stage(self):
        m = self.graph(
            "from sklearn.impute import IterativeImputer\nfrom sklearn.ensemble import ExtraTreesRegressor\ndef build_model(X_train,y_train):\n return IterativeImputer(estimator=ExtraTreesRegressor())"
        )
        self.assertEqual([x.name for x in graph_nodes(m)], ["IterativeImputer"])

    def test_required_unprovided_argument_not_compliant(self):
        with self.assertRaisesRegex(Unsupported, "Invalid factory signature"):
            self.graph("def build_model(X_train,y_train,random_state):\n return None")

    def test_syntax_error_remains_invalid(self):
        with self.assertRaises(SyntaxError):
            self.graph("from sklearn.experimental.enable_iterative_imputer")

    def test_alias_and_tuple_conversion(self):
        m = self.graph(
            'from sklearn.pipeline import Pipeline as P\nfrom sklearn.preprocessing import MinMaxScaler\ndef build_model(X_train,y_train,feature_range):\n return P([("s",MinMaxScaler(feature_range=tuple(feature_range)))])',
            {"feature_range": [0, 1]},
        )
        self.assertEqual(next(iter(graph_nodes(m))).kwargs["feature_range"], (0, 1))

    def test_hyperparameter_is_not_assumed_to_be_forwarded(self):
        m = self.graph(
            "from sklearn.neural_network import MLPClassifier\ndef build_model(X_train,y_train,max_iter):\n return MLPClassifier(max_iter=1000)",
            {"max_iter": 300},
        )
        self.assertEqual(m.kwargs["max_iter"], 1000)

    def test_parallel_branches_are_not_misread_as_sequential(self):
        m = self.graph(
            'from sklearn.pipeline import Pipeline\nfrom sklearn.compose import ColumnTransformer\nfrom sklearn.preprocessing import StandardScaler,OneHotEncoder\nfrom sklearn.linear_model import Ridge\ndef build_model(X_train,y_train):\n return Pipeline([("p",ColumnTransformer([("num",StandardScaler(),["n"]),("cat",OneHotEncoder(),["c"])])),("r",Ridge())])',
            c=1,
        )
        self.assertEqual(
            [[n.name for n in p] for p in graph_paths(m)],
            [["StandardScaler", "Ridge"], ["OneHotEncoder", "Ridge"]],
        )


if __name__ == "__main__":
    unittest.main()
