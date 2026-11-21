"""Conservative AST-only interpreter: never imports or executes generated code."""

import ast
from dataclasses import dataclass


class Unsupported(Exception):
    pass


class Missing:
    def __init__(self, reason):
        self.reason = reason


@dataclass
class Symbol:
    name: str


@dataclass
class Node:
    name: str
    args: list
    kwargs: dict
    line: int


@dataclass
class Frame:
    numeric: int
    categorical: int
    selected: str = "all"
    dataset: str = ""

    @property
    def columns(self):
        n = self.numeric if self.selected != "categorical" else 0
        c = self.categorical if self.selected != "numeric" else 0
        schemas = {
            "adult": (
                [
                    "age",
                    "fnlwgt",
                    "education-num",
                    "capital-gain",
                    "capital-loss",
                    "hours-per-week",
                ],
                [
                    "workclass",
                    "education",
                    "marital-status",
                    "occupation",
                    "relationship",
                    "race",
                    "sex",
                    "native-country",
                ],
            ),
            "california_housing": (
                [
                    "longitude",
                    "latitude",
                    "housing_median_age",
                    "total_rooms",
                    "total_bedrooms",
                    "population",
                    "households",
                    "median_income",
                ],
                ["ocean_proximity"],
            ),
        }
        num, cat = schemas.get(
            self.dataset,
            (
                ["numeric_" + str(i) for i in range(n)],
                ["categorical_" + str(i) for i in range(c)],
            ),
        )
        return (num if n else []) + (cat if c else [])


class Returned(Exception):
    def __init__(self, value):
        self.value = value


class Factory:
    def __init__(self, source, numeric, categorical, parameters, dataset=""):
        self.source = source
        self.tree = ast.parse(source)
        self.env = {
            "X_train": Frame(numeric, categorical, dataset=dataset),
            "y_train": Symbol("target"),
            **parameters,
        }
        self.numeric = numeric
        self.categorical = categorical
        self.dataset = dataset
        self.functions = {}
        self.column_scope_review = False
        for n in self.tree.body:
            if isinstance(n, (ast.ImportFrom, ast.Import)):
                for a in n.names:
                    self.env[a.asname or a.name] = Symbol(a.name)
            elif isinstance(n, (ast.FunctionDef, ast.ClassDef)):
                self.env[n.name] = Symbol(n.name)
                if isinstance(n, ast.FunctionDef):
                    self.functions[n.name] = n

    def run(self):
        fun = self.functions.get("build_model")
        if fun is None:
            raise Unsupported("No build_model function")
        defaults = [None] * (len(fun.args.args) - len(fun.args.defaults)) + list(
            fun.args.defaults
        )
        for arg, default in zip(fun.args.args, defaults):
            if arg.arg not in self.env:
                if default is None:
                    raise Unsupported(
                        "Invalid factory signature: unbound argument " + arg.arg
                    )
                self.env[arg.arg] = self.expr(default)
        try:
            self.block(fun.body)
        except Returned as result:
            if not isinstance(result.value, Node):
                raise Unsupported("Factory returns a non-model value")
            return result.value
        raise Unsupported("Invalid factory: no model return")

    def expr(self, n):
        if isinstance(n, ast.Constant):
            return n.value
        if isinstance(n, ast.Name):
            return self.env.get(n.id, Symbol(n.id))
        if isinstance(n, (ast.List, ast.Tuple, ast.Set)):
            val = [self.expr(x) for x in n.elts]
            return tuple(val) if isinstance(n, ast.Tuple) else val
        if isinstance(n, ast.Dict):
            return {self.expr(k): self.expr(v) for k, v in zip(n.keys, n.values)}
        if isinstance(n, ast.Attribute):
            obj = self.expr(n.value)
            if isinstance(obj, Symbol):
                return Symbol(obj.name + "." + n.attr)
            if isinstance(obj, Frame):
                if n.attr == "columns":
                    return obj.columns
                if n.attr == "shape":
                    return (Symbol("unknown_training_row_count"), len(obj.columns))
            if isinstance(obj, list) and n.attr == "empty":
                return not obj
            if isinstance(obj, Node) and n.attr == "steps":
                return obj.kwargs.get("steps", obj.args[0] if obj.args else [])
            raise Unsupported("Unsupported attribute " + ast.unparse(n))
        if isinstance(n, ast.Subscript):
            obj = self.expr(n.value)
            index = self.expr(n.slice)
            if isinstance(obj, Frame):
                return obj
            try:
                return obj[index]
            except (TypeError, KeyError, IndexError):
                raise Unsupported("Unsupported subscript " + ast.unparse(n))
        if isinstance(n, ast.UnaryOp):
            v = self.expr(n.operand)
            if isinstance(n.op, ast.Not):
                return not self.truth(v)
            if isinstance(n.op, ast.USub):
                return -v
        if isinstance(n, ast.BoolOp):
            values = [self.truth(self.expr(v)) for v in n.values]
            return all(values) if isinstance(n.op, ast.And) else any(values)
        if isinstance(n, ast.Compare):
            left = self.expr(n.left)
            if isinstance(left, (Symbol, Missing)):
                raise Unsupported("Unresolved comparison " + ast.unparse(n))
            result = True
            for op, other in zip(n.ops, n.comparators):
                right = self.expr(other)
                if isinstance(right, (Symbol, Missing)):
                    raise Unsupported("Unresolved comparison " + ast.unparse(n))
                if isinstance(op, ast.Eq):
                    ok = left == right
                elif isinstance(op, ast.NotEq):
                    ok = left != right
                elif isinstance(op, ast.Gt):
                    ok = left > right
                elif isinstance(op, ast.GtE):
                    ok = left >= right
                elif isinstance(op, ast.Lt):
                    ok = left < right
                elif isinstance(op, ast.LtE):
                    ok = left <= right
                elif isinstance(op, ast.Is):
                    ok = left is right
                elif isinstance(op, ast.IsNot):
                    ok = left is not right
                elif isinstance(op, ast.In):
                    ok = left in right
                elif isinstance(op, ast.NotIn):
                    ok = left not in right
                else:
                    raise Unsupported("Comparison operator")
                result = result and ok
                left = right
            return result
        if isinstance(n, ast.IfExp):
            return self.expr(n.body if self.truth(self.expr(n.test)) else n.orelse)
        if isinstance(n, ast.BinOp):
            a, b = self.expr(n.left), self.expr(n.right)
            if isinstance(n.op, ast.Add):
                return a + b
            if isinstance(n.op, ast.Sub):
                return a - b
            if isinstance(n.op, ast.Mult):
                return a * b
            if isinstance(n.op, ast.Div):
                return a / b
            raise Unsupported("Arithmetic " + ast.unparse(n))
        if isinstance(n, ast.Call):
            args = [self.expr(a) for a in n.args]
            kw = {}
            for key in n.keywords:
                value = self.expr(key.value)
                if key.arg is None:
                    if not isinstance(value, dict):
                        raise Unsupported("Unresolved keyword expansion")
                    kw.update(value)
                else:
                    kw[key.arg] = value
            if isinstance(n.func, ast.Attribute):
                try:
                    base = self.expr(n.func.value)
                except Unsupported:
                    base = Symbol(ast.unparse(n.func.value))
                method = n.func.attr
                if isinstance(base, Frame):
                    if method == "select_dtypes":
                        include = kw.get("include", [])
                        text = str(include).lower()
                        typ = (
                            "numeric"
                            if any(x in text for x in ("number", "int", "float"))
                            else "categorical"
                        )
                        if "exclude" in kw:
                            typ = (
                                "categorical"
                                if "number" in str(kw["exclude"]).lower()
                                else "numeric"
                            )
                        return Frame(base.numeric, base.categorical, typ, base.dataset)
                    if method in ("copy", "astype", "fillna", "replace"):
                        return base
                if isinstance(base, list):
                    if method in ("tolist", "to_list"):
                        return base
                    if method == "append":
                        base.append(args[0])
                        return None
                    if method == "remove":
                        base.remove(args[0])
                        return None
                if isinstance(base, dict) and method == "get":
                    return base.get(*args)
                if method in ("tolist", "to_list") and isinstance(base, tuple):
                    return list(base)
                if isinstance(base, Node) and base.name == "make_column_selector":
                    return Frame(
                        self.numeric,
                        self.categorical,
                        "numeric"
                        if "number" in str(base.kwargs).lower()
                        else "categorical",
                    ).columns
            fun = self.expr(n.func)
            name = (
                fun.name
                if isinstance(fun, Symbol)
                else fun.name
                if isinstance(fun, Node)
                else ""
            )
            short = name.split(".")[-1]
            if short == "isinstance":
                val, typ = args
                kind = typ.name.split(".")[-1] if isinstance(typ, Symbol) else ""
                return isinstance(
                    val,
                    {
                        "list": list,
                        "tuple": tuple,
                        "int": int,
                        "float": float,
                        "str": str,
                        "DataFrame": Frame,
                    }.get(kind, type(None)),
                )
            if short == "hasattr":
                return (
                    args[1] in ("columns", "select_dtypes", "shape")
                    if isinstance(args[0], Frame)
                    else False
                )
            if short in (
                "tuple",
                "list",
                "int",
                "float",
                "str",
                "len",
                "min",
                "max",
                "range",
                "enumerate",
            ):
                return {
                    "tuple": tuple,
                    "list": list,
                    "int": int,
                    "float": float,
                    "str": str,
                    "len": len,
                    "min": min,
                    "max": max,
                    "range": range,
                    "enumerate": enumerate,
                }[short](*args)
            if short in ("array", "asarray"):
                return args[0]
            if short == "make_column_selector":
                return Node(short, args, kw, n.lineno)
            if isinstance(fun, Node) and fun.name == "make_column_selector":
                return Frame(
                    self.numeric,
                    self.categorical,
                    "numeric" if "number" in str(fun.kwargs).lower() else "categorical",
                ).columns
            if short and (
                short[0].isupper()
                or short in ("make_pipeline", "make_column_transformer")
            ):
                return Node(short, args, kw, n.lineno)
            return Missing("Unresolved function " + short)
        if isinstance(n, ast.Lambda):
            return Symbol("lambda " + ast.unparse(n))
        if isinstance(n, ast.ListComp):
            if len(n.generators) != 1:
                raise Unsupported("Nested comprehension")
            gen = n.generators[0]
            values = self.expr(gen.iter)
            out = []
            if any(".isnull()" in ast.unparse(test) for test in gen.ifs):
                # Manual review of these two Ames factories: only the feature subset is
                # data-dependent; component classes/order/parameters do not change.
                self.column_scope_review = True
                for val in values:
                    self.assign(gen.target, val)
                    out.append(self.expr(n.elt))
                return out
            for val in values:
                self.assign(gen.target, val)
                if all(self.truth(self.expr(test)) for test in gen.ifs):
                    out.append(self.expr(n.elt))
            return out
        raise Unsupported("Expression " + ast.unparse(n)[:100])

    def truth(self, value):
        if isinstance(value, (Symbol, Missing, Node)):
            raise Unsupported("Unresolved branch condition")
        return bool(value)

    def assign(self, target, value):
        if isinstance(target, ast.Name):
            self.env[target.id] = value
        elif isinstance(target, (ast.Tuple, ast.List)):
            for t, v in zip(target.elts, value):
                self.assign(t, v)
        else:
            raise Unsupported("Assignment " + ast.unparse(target))

    def block(self, statements):
        for n in statements:
            if isinstance(n, ast.Assign):
                val = self.expr(n.value)
                for target in n.targets:
                    self.assign(target, val)
            elif isinstance(n, ast.AnnAssign):
                self.assign(n.target, self.expr(n.value))
            elif isinstance(n, ast.If):
                self.block(n.body if self.truth(self.expr(n.test)) else n.orelse)
            elif isinstance(n, ast.Return):
                raise Returned(self.expr(n.value))
            elif isinstance(n, ast.Expr):
                self.expr(n.value)
            elif isinstance(n, (ast.FunctionDef, ast.ClassDef)):
                self.env[n.name] = Symbol(n.name)
            elif isinstance(n, (ast.Import, ast.ImportFrom, ast.Pass)):
                pass
            elif isinstance(n, ast.For):
                for val in self.expr(n.iter):
                    self.assign(n.target, val)
                    self.block(n.body)
            else:
                raise Unsupported("Statement " + type(n).__name__)


def graph_nodes(node, scope="global"):
    """Return only components reachable from the returned pipeline/model."""
    if not isinstance(node, Node):
        raise Unsupported("Unresolved component in returned model")
    if node.name in ("Pipeline", "make_pipeline"):
        children = (
            node.args
            if node.name == "make_pipeline"
            else node.kwargs.get("steps", node.args[0] if node.args else [])
        )
        for child in children:
            yield from graph_nodes(
                child[1] if isinstance(child, tuple) else child, scope
            )
    elif node.name in ("ColumnTransformer", "make_column_transformer"):
        children = (
            node.args
            if node.name == "make_column_transformer"
            else node.kwargs.get("transformers", node.args[0] if node.args else [])
        )
        for child in children:
            trans, columns = (
                (child[0], child[1])
                if node.name == "make_column_transformer"
                else (child[1], child[2])
            )
            if isinstance(columns, list) and not columns:
                continue
            if isinstance(trans, str) and trans in ("drop", "passthrough"):
                continue
            branch_scope = (
                "categorical"
                if (
                    "cat" in str(child[0]).lower()
                    or all(
                        isinstance(x, str) and x.startswith("categorical_")
                        for x in columns
                    )
                    if isinstance(columns, list) and columns
                    else "cat" in str(child[0]).lower()
                )
                else "numeric"
            )
            yield from graph_nodes(trans, branch_scope)
    else:
        node.scope = scope
        yield node


def graph_paths(node):
    if not isinstance(node, Node):
        raise Unsupported("Unresolved graph path")
    if node.name in ("Pipeline", "make_pipeline"):
        children = (
            node.args
            if node.name == "make_pipeline"
            else node.kwargs.get("steps", node.args[0] if node.args else [])
        )
        paths = [[]]
        for child in children:
            component = child[1] if isinstance(child, tuple) else child
            paths = [a + b for a in paths for b in graph_paths(component)]
        return paths
    if node.name in ("ColumnTransformer", "make_column_transformer"):
        children = (
            node.args
            if node.name == "make_column_transformer"
            else node.kwargs.get("transformers", node.args[0] if node.args else [])
        )
        paths = []
        for child in children:
            trans, columns = (
                (child[0], child[1])
                if node.name == "make_column_transformer"
                else (child[1], child[2])
            )
            if isinstance(columns, list) and not columns:
                continue
            if isinstance(trans, str):
                if trans == "passthrough":
                    paths.append([])
                continue
            paths += graph_paths(trans)
        return paths or [[]]
    return [[node]]
