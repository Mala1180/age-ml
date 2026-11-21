"""Static contract checks; never execute generated source."""

import itertools
import json

if __package__:
    from ._compliance_static import (
        Factory,
        Missing,
        Node,
        Symbol,
        graph_nodes,
        graph_paths,
    )
else:
    from _compliance_static import (
        Factory,
        Missing,
        Node,
        Symbol,
        graph_nodes,
        graph_paths,
    )
CLASSES = {
    "simple_imputer": "SimpleImputer",
    "iterative_imputer": "IterativeImputer",
    "kbins": "KBinsDiscretizer",
    "binarizer": "Binarizer",
    "power_transformer": "PowerTransformer",
    "robust_scaler": "RobustScaler",
    "standard": "StandardScaler",
    "minmax": "MinMaxScaler",
    "select_k_best": "SelectKBest",
    "pca": "PCA",
    "near_miss": "NearMiss",
    "smote": "SMOTE",
    "decision_tree": "DecisionTreeClassifier",
    "knn": "KNeighborsClassifier",
    "naive_bayes": "GaussianNB",
    "nn": "MLPClassifier",
    "random_forest": "RandomForestClassifier",
    "ada_boost": "AdaBoostClassifier",
    "linear": "LinearRegression",
    "ridge": "Ridge",
    "lasso": "Lasso",
    "elastic_net": "ElasticNet",
    "svr": "SVR",
    "knn_regressor": "KNeighborsRegressor",
    "random_forest_regressor": "RandomForestRegressor",
    "nn_regressor": "MLPRegressor",
}
DEFAULTS = {
    "SimpleImputer": {"strategy": "mean"},
    "IterativeImputer": {"max_iter": 10},
    "KBinsDiscretizer": {"n_bins": 5, "encode": "onehot", "strategy": "quantile"},
    "Binarizer": {"threshold": 0.0},
    "PowerTransformer": {"method": "yeo-johnson"},
    "RobustScaler": {"quantile_range": (25.0, 75.0)},
    "MinMaxScaler": {"feature_range": (0, 1)},
    "SelectKBest": {"k": 10},
    "PCA": {"n_components": None},
    "NearMiss": {"version": 1},
    "SMOTE": {"k_neighbors": 5},
    "DecisionTreeClassifier": {"max_depth": None, "min_samples_split": 2},
    "KNeighborsClassifier": {"n_neighbors": 5, "weights": "uniform"},
    "GaussianNB": {"var_smoothing": 1e-9},
    "MLPClassifier": {"hidden_layer_sizes": (100,), "alpha": 0.0001, "max_iter": 200},
    "RandomForestClassifier": {"n_estimators": 100, "max_depth": None},
    "AdaBoostClassifier": {"n_estimators": 50, "learning_rate": 1.0},
    "Ridge": {"alpha": 1.0},
    "Lasso": {"alpha": 1.0},
    "ElasticNet": {"alpha": 1.0, "l1_ratio": 0.5},
    "SVR": {"kernel": "rbf", "C": 1.0, "epsilon": 0.1},
    "KNeighborsRegressor": {"n_neighbors": 5, "weights": "uniform"},
    "RandomForestRegressor": {"n_estimators": 100, "max_depth": None},
    "MLPRegressor": {"hidden_layer_sizes": (100,), "alpha": 0.0001, "max_iter": 200},
}
ALIASES = {"imputation_strategy": "strategy", "discretization_strategy": "strategy"}
POSARGS = {
    "PCA": ["n_components"],
    "SimpleImputer": ["missing_values"],
    "IterativeImputer": ["estimator"],
    "KBinsDiscretizer": ["n_bins"],
    "Binarizer": [],
    "PowerTransformer": [],
    "RobustScaler": [],
    "StandardScaler": [],
    "MinMaxScaler": ["feature_range"],
    "SelectKBest": ["score_func"],
    "NearMiss": [],
    "SMOTE": [],
    "KNeighborsClassifier": ["n_neighbors"],
    "KNeighborsRegressor": ["n_neighbors"],
    "Ridge": ["alpha"],
    "Lasso": ["alpha"],
    "ElasticNet": ["alpha", "l1_ratio"],
    "MLPClassifier": ["hidden_layer_sizes", "activation"],
}


def norm(v):
    if isinstance(v, (list, tuple)):
        return tuple(norm(x) for x in v)
    if isinstance(v, dict):
        return {k: norm(x) for k, x in v.items()}
    if isinstance(v, str):
        try:
            return float(v) if any(x in v for x in ".eE") else v
        except ValueError:
            return v
    return v


def basic(c):
    return {
        k: c[k]
        for k in [
            "condition",
            "dataset",
            "repetition",
            "run_identity",
            "pipeline_id",
            "code_sha256",
        ]
    }


def audit_candidates(cs, codes):
    rows = []
    details = []
    unresolved = []
    for c in cs:
        steps = c["requested_steps"]
        if steps is None:
            unresolved.append(
                {
                    **basic(c),
                    "status": "unresolved_recipe",
                    "reason": "No uniquely hash-verified requested recipe",
                }
            )
            continue
        expected = {CLASSES[s["candidate"]]: s for s in steps}
        issues = []
        param_issues = []
        unknown_params = []
        status = "resolved"
        reason = ""
        node_list = []
        try:
            factory = Factory(
                codes[c["code_sha256"]],
                c["numeric_features"],
                c["discrete_features"],
                c["parameters"],
                c["dataset"],
            )
            model = factory.run()
            node_list = list(graph_nodes(model))
        except SyntaxError as e:
            status = "invalid_source"
            reason = f"{e.msg}, line {e.lineno}"
        except Exception as e:  # noqa: BLE001 - unsupported source must remain auditable as unknown
            reason = str(e)
            status = (
                "invalid_factory"
                if reason.startswith("Invalid factory")
                else "unresolved_factory"
            )
        if status == "resolved":
            names = {n.name for n in node_list}
            task = c["problem"]
            for step in steps:
                if (
                    step["name"] in ("classification", "regression")
                    and step["name"] != task
                ):
                    issues.append(
                        {
                            "key": "task:" + step["name"],
                            "type": "wrong_task_recipe",
                            "component": CLASSES.get(
                                step["candidate"], step["candidate"]
                            ),
                            "expected": task,
                            "observed": step["name"],
                            "line": None,
                        }
                    )
            for name, step in expected.items():
                if name not in names:
                    issues.append(
                        {
                            "key": "missing:" + name,
                            "type": "missing_declared_component",
                            "component": name,
                            "expected": name,
                            "observed": "No reachable component of this class in returned model",
                            "line": None,
                        }
                    )
            for n in node_list:
                if n.name not in expected:
                    issues.append(
                        {
                            "key": "extra:" + n.name,
                            "type": "unlisted_component",
                            "component": n.name,
                            "expected": "Only declared components",
                            "observed": n.name,
                            "scope": getattr(n, "scope", "global"),
                            "line": n.line,
                        }
                    )
                if n.name in expected:
                    step = expected[n.name]
                    for parameter, allowed in step["hyperparameters"].items():
                        key = ALIASES.get(parameter, parameter)
                        # The frozen per-component grid disambiguates colliding parameter names.
                        owners = [s for s in steps if parameter in s["hyperparameters"]]
                        desired = c["parameters"].get(parameter)
                        if len(owners) > 1:
                            desired_values = allowed
                            criterion = "frozen_component_grid"
                        else:
                            desired_values = [desired]
                            criterion = "selected_parameter_value"
                        kw = dict(zip(POSARGS.get(n.name, []), n.args))
                        kw.update(n.kwargs)
                        observed = kw.get(
                            key,
                            DEFAULTS.get(n.name, {}).get(
                                key, Missing("No verified default")
                            ),
                        )
                        if isinstance(observed, (Missing, Symbol, Node)):
                            unknown_params.append(f"{n.name}.{key}: unresolved value")
                            continue
                        if not any(norm(observed) == norm(a) for a in desired_values):
                            param_issues.append(
                                {
                                    "key": "parameter:" + n.name + "." + key,
                                    "type": "hyperparameter_mismatch",
                                    "component": n.name,
                                    "parameter": key,
                                    "expected": desired_values,
                                    "observed": observed,
                                    "criterion": criterion,
                                    "scope": getattr(n, "scope", "global"),
                                    "line": n.line,
                                }
                            )
            ranks = {
                CLASSES[step["candidate"]]: index for index, step in enumerate(steps)
            }
            for path in graph_paths(model):
                present = [n for n in path if n.name in ranks]
                for a, b in itertools.pairwise(present):
                    if ranks[a.name] > ranks[b.name]:
                        issues.append(
                            {
                                "key": "order:" + a.name + ">" + b.name,
                                "type": "declared_order_violation",
                                "component": a.name + ">" + b.name,
                                "expected": "Declared stage order",
                                "observed": a.name + " precedes " + b.name,
                                "line": a.line,
                            }
                        )
            issues = list({i["key"]: i for i in issues}.values())
            param_issues = list({i["key"]: i for i in param_issues}.values())
            parameter_scope_reviews = [
                i
                for i in param_issues
                if i.get("scope") == "categorical" and i["component"] == "SimpleImputer"
            ]
            param_issues = [i for i in param_issues if i not in parameter_scope_reviews]
        else:
            unresolved.append({**basic(c), "status": status, "reason": reason})
        row = {
            **basic(c),
            "run_id": c["run_id"],
            "candidate_key": c["candidate_key"],
            "fit_attempt": c.get("fit_attempt"),
            "grid_position": c.get("grid_position"),
            "fit_succeeded": str(c.get("fit_succeeded")).lower() == "true",
            "eligible": str(c.get("eligible")).lower() == "true",
            "audit_status": status,
            "unresolved_reason": reason,
            "structural_violation_count": len(issues) if status == "resolved" else None,
            "parameter_violation_count": len(param_issues)
            if status == "resolved"
            else None,
            "any_structural_violation": bool(issues) if status == "resolved" else None,
            "any_parameter_violation": bool(param_issues)
            if status == "resolved"
            else None,
            "any_violation": bool(issues or param_issues)
            if status == "resolved"
            else None,
            "column_scope_review": factory.column_scope_review
            if status == "resolved"
            else False,
            "unresolved_parameters": "; ".join(unknown_params),
            "requested_steps": json.dumps(steps, sort_keys=True),
            "selected_parameters": json.dumps(c["parameters"], sort_keys=True),
            "validation_score": c.get("validation_score"),
            "source_member": c["matching_code_members"][0],
            "parameter_scope_reviews": json.dumps(parameter_scope_reviews)
            if status == "resolved"
            else "",
        }
        rows.append(row)
        for issue in issues + param_issues:
            details.append({**basic(c), "run_id": c["run_id"], **issue})
    return rows, details, unresolved
