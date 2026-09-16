"""Derivation of the specification variants from the general specification.

Whatever the variant, three parts of the general file are reproduced verbatim,
so that the variants stay comparable: the ``budgets`` section, which fixes the
computational effort; the hyper-parameter grid of every surviving operator; and
the relative ordering of the steps, restated over the surviving ones only -- a
partial ordering would let the planner permute the steps and would blow up the
search space combinatorially, confounding the ablation.
"""

import textwrap
from copy import deepcopy
from dataclasses import dataclass, field
from hashlib import sha256
from math import ceil
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import yaml

from experiments.ablation.specifications import Variant
from experiments.ablation.specifications.meta_features import (
    CLASSIFICATION,
    REGRESSION,
    DatasetMetaFeatures,
)

# --------------------------------------------------------------------------- #
# Thresholds of the dataset-specific specialization
# --------------------------------------------------------------------------- #

#: Below this number of input features, selection/extraction cannot pay off.
MIN_FEATURES_FOR_SELECTION: int = 20

#: Above this number of input features, binning every column is prohibitive.
MAX_FEATURES_FOR_DISCRETIZATION: int = 50

#: Binning transforms numeric features: it needs enough of them.
MIN_NUMERIC_RATIO_FOR_DISCRETIZATION: float = 0.5

#: Resampling a (nearly) balanced training set is useless at best.
MIN_IMBALANCE_RATIO_FOR_REBALANCING: float = 1.5

#: |skew| above which a distribution is considered heavy-tailed.
HEAVY_SKEW: float = 2.0

#: ``instances * features`` above which quadratic learners miss the budget.
MAX_CELLS_FOR_QUADRATIC_LEARNERS: int = 1_000_000

#: Below this number of instances, multi-layer perceptrons overfit.
MIN_INSTANCES_FOR_NEURAL_NETWORKS: int = 1_000

#: Learners whose fit/predict cost is (super-)quadratic in the training size.
QUADRATIC_LEARNERS: Tuple[str, ...] = ("knn", "svr", "knn_regressor")

#: Learners that need a substantial number of instances to be trainable.
NEURAL_LEARNERS: Tuple[str, ...] = ("nn", "nn_regressor")

#: Key order of the generated documents, mirroring the general specification.
SECTIONS: Tuple[str, ...] = (
    "budgets",
    "pipeline",
    "ordering",
    "constraints",
    "technical_details",
)

HEADER_WIDTH: int = 78


# --------------------------------------------------------------------------- #
# Reading the YAML document
# --------------------------------------------------------------------------- #


def operator_of(node: Any) -> Tuple[str, Optional[str]]:
    """The ``(step, candidate)`` a constraint node refers to.

    Handles both the entries of ``require``/``forbid`` (``normalization`` or
    ``{classification: knn}``) and the body of an ``if.step`` condition.
    """
    if isinstance(node, str):
        return node, None
    if isinstance(node, Mapping) and len(node) == 1:
        step, candidate = next(iter(node.items()))
        return str(step), candidate if isinstance(candidate, str) else None
    raise ValueError(f"Unsupported constraint node: {node!r}")


def condition_operator(
    constraint: Mapping[str, Any],
) -> Tuple[Optional[str], Optional[str]]:
    """The operator an ``if`` condition names, or ``(None, None)`` if it is a
    ``dataset`` or a natural language condition."""
    condition: Any = constraint["if"]
    if isinstance(condition, Mapping) and "step" in condition:
        return operator_of(condition["step"])
    return None, None


def names_an_operator(constraint: Mapping[str, Any]) -> bool:
    """Whether the constraint is about one specific operator.

    This is exactly what tells AutoML domain knowledge (``decision trees do not
    need normalization``, ``PCA requires normalization``) from the structural
    rules that keep a pipeline well-formed for its task.
    """
    return condition_operator(constraint)[1] is not None


def is_dataset_condition(constraint: Mapping[str, Any]) -> bool:
    condition: Any = constraint["if"]
    return isinstance(condition, Mapping) and "dataset" in condition


def candidate_name(candidate: Any) -> str:
    return candidate if isinstance(candidate, str) else str(next(iter(candidate)))


def steps_of(document: Mapping[str, Any]) -> Dict[str, Tuple[str, ...]]:
    """Map every step of ``document`` to the names of its candidates."""
    return {
        step_id: tuple(candidate_name(c) for c in step.get("candidates") or [])
        for step_id, step in document["pipeline"]["steps"].items()
    }


def mandatory_steps_of(document: Mapping[str, Any]) -> Tuple[str, ...]:
    pipeline: Mapping[str, Any] = document["pipeline"]
    default: bool = bool(pipeline.get("defaults", {}).get("mandatory", False))
    return tuple(
        step_id
        for step_id, step in pipeline["steps"].items()
        if bool(step.get("mandatory", default))
    )


# --------------------------------------------------------------------------- #
# Dataset-specific specialization
# --------------------------------------------------------------------------- #


def specialize(document: Dict[str, Any], meta: DatasetMetaFeatures) -> List[str]:
    """Narrow ``document`` down to what suits ``meta``, in place.

    Returns one line of rationale per decision taken, which ends up in the
    header of the generated file. Every decision below reads the meta-features
    and nothing else: no rule may look at a dataset name or at the outcome of a
    previous run, so the variant cannot be tuned on the results it is evaluated
    on.
    """
    steps: Dict[str, Any] = document["pipeline"]["steps"]
    rationale: List[str] = []

    def drop_step(step_id: str, reason: str) -> None:
        if steps.pop(step_id, None) is not None:
            rationale.append(f"[{step_id}] dropped: {reason}")

    def drop_candidates(step_id: str, names: Sequence[str], reason: str) -> None:
        candidates: List[Any] = steps.get(step_id, {}).get("candidates", [])
        dropped: List[str] = [
            candidate_name(c) for c in candidates if candidate_name(c) in names
        ]
        if not dropped:
            return
        kept: List[Any] = [c for c in candidates if candidate_name(c) not in names]
        if not kept:
            raise ValueError(
                f"Specializing '{step_id}' for '{meta.name}' would leave it "
                "without any candidate; refine the thresholds instead."
            )
        steps[step_id]["candidates"] = kept
        rationale.append(f"[{step_id}] {_quoted(dropped)} dropped: {reason}")

    def override(step_id: str, name: str, params: Dict[str, Any], why: str) -> None:
        for candidate in steps.get(step_id, {}).get("candidates", []):
            if candidate_name(candidate) == name:
                candidate[name].setdefault("params", {}).update(params)
                rationale.append(f"[{step_id}] '{name}' re-parametrized: {why}")

    # The task is known a priori: only its estimator survives, and it is
    # mandatory. The dataset conditions that used to tell the two tasks apart
    # are dropped by `generate` below.
    steps[meta.task]["mandatory"] = True
    rationale.append(f"[{meta.task}] mandatory: the task is known to be {meta.task}")
    drop_step(
        REGRESSION if meta.task == CLASSIFICATION else CLASSIFICATION,
        f"the dataset poses a {meta.task} problem",
    )

    if meta.missing_value_ratio == 0.0:
        drop_step("imputation", "the dataset has no missing value")

    if meta.task != CLASSIFICATION:
        drop_step("rebalancing", "rebalancing is not defined for a numeric target")
    elif meta.imbalance_ratio < MIN_IMBALANCE_RATIO_FOR_REBALANCING:
        drop_step(
            "rebalancing",
            f"the imbalance ratio is {meta.imbalance_ratio:.2f} < "
            f"{MIN_IMBALANCE_RATIO_FOR_REBALANCING}, resampling is not warranted",
        )

    if meta.features < MIN_FEATURES_FOR_SELECTION:
        drop_step(
            "features",
            f"{meta.features} < {MIN_FEATURES_FOR_SELECTION} input features "
            "leave nothing worth selecting or extracting",
        )
    else:
        selected: List[int] = sorted(
            {
                min(meta.features, max(5, ceil(meta.features / 10))),
                min(meta.features, max(10, ceil(meta.features / 4))),
            }
        )
        override(
            "features",
            "select_k_best",
            {"k": selected},
            f"with {meta.features} input features, k is scaled to {selected} "
            "(about a tenth and a quarter of them)",
        )

    if meta.features > MAX_FEATURES_FOR_DISCRETIZATION:
        drop_step(
            "discretization",
            f"binning {meta.features} > {MAX_FEATURES_FOR_DISCRETIZATION} "
            "features is prohibitive",
        )
    elif meta.numeric_ratio < MIN_NUMERIC_RATIO_FOR_DISCRETIZATION:
        drop_step(
            "discretization",
            f"only {meta.numeric_features}/{meta.features} input features are "
            "numeric, so there is little to discretize",
        )

    heavy_tailed: bool = meta.max_absolute_skew >= HEAVY_SKEW
    drop_candidates(
        "normalization",
        ("minmax",) if heavy_tailed else ("power_transformer",),
        f"the largest absolute skewness is {meta.max_absolute_skew:.2f} "
        + (
            f">= {HEAVY_SKEW}, min-max scaling would be dominated by the "
            "outliers of the heavy-tailed features"
            if heavy_tailed
            else f"< {HEAVY_SKEW}, the features are well-behaved and do not "
            "justify the cost of a power transform"
        ),
    )

    if meta.cells > MAX_CELLS_FOR_QUADRATIC_LEARNERS:
        drop_candidates(
            meta.task,
            QUADRATIC_LEARNERS,
            f"with {meta.instances} x {meta.features} cells, instance- and "
            "kernel-based learners do not fit the time budget",
        )
    if meta.instances < MIN_INSTANCES_FOR_NEURAL_NETWORKS:
        drop_candidates(
            meta.task,
            NEURAL_LEARNERS,
            f"only {meta.instances} < {MIN_INSTANCES_FOR_NEURAL_NETWORKS} "
            "instances are available, too few to train a neural network",
        )
    return rationale


# --------------------------------------------------------------------------- #
# Generation
# --------------------------------------------------------------------------- #


def prune_constraints(
    constraints: Sequence[Mapping[str, Any]], steps: Mapping[str, Tuple[str, ...]]
) -> List[Dict[str, Any]]:
    """Drop every reference to a step or candidate that no longer exists.

    A constraint whose condition became unsatisfiable, or that lost all of its
    effects, is dropped altogether.
    """

    def exists(step: Optional[str], candidate: Optional[str]) -> bool:
        return (
            step is not None
            and step in steps
            and (candidate is None or candidate in steps[step])
        )

    pruned: List[Dict[str, Any]] = []
    for constraint in constraints:
        step, candidate = condition_operator(constraint)
        if step is not None and not exists(step, candidate):
            continue
        kept: Dict[str, Any] = {"if": constraint["if"]}
        for kind in ("require", "forbid"):
            effects = [
                node for node in constraint.get(kind, []) if exists(*operator_of(node))
            ]
            if effects:
                kept[kind] = effects
        if len(kept) > 1:
            pruned.append(kept)
    return pruned


def generate(
    base_specification: str,
    variant: Variant,
    meta: Optional[DatasetMetaFeatures] = None,
) -> "GeneratedSpecification":
    """Derive the specification of ``variant`` (for ``meta``, when needed)."""
    if variant.dataset_specific and meta is None:
        raise ValueError(
            f"Variant '{variant.id}' is dataset-specific: "
            "meta-features are required to generate it."
        )

    base: Dict[str, Any] = yaml.safe_load(base_specification)
    document: Dict[str, Any] = deepcopy(base)
    rationale: List[str] = (
        specialize(document, meta) if variant.dataset_specific and meta else []
    )

    steps: Dict[str, Tuple[str, ...]] = steps_of(document)
    document["ordering"] = [{"sequence": list(steps)}]
    document["constraints"] = prune_constraints(
        [
            constraint
            for constraint in base.get("constraints", [])
            if not (variant.drop_operator_knowledge and names_an_operator(constraint))
            and not (variant.dataset_specific and is_dataset_condition(constraint))
        ],
        steps,
    )
    return GeneratedSpecification(
        variant=variant,
        document={section: document[section] for section in SECTIONS},
        meta=meta if variant.dataset_specific else None,
        rationale=rationale,
        base_digest=sha256(base_specification.encode("utf-8")).hexdigest(),
    )


@dataclass(frozen=True)
class GeneratedSpecification:
    """A specification file, together with the provenance of its content."""

    variant: Variant
    document: Dict[str, Any]
    meta: Optional[DatasetMetaFeatures] = None
    rationale: List[str] = field(default_factory=list)
    base_digest: str = ""

    @property
    def name(self) -> str:
        return self.meta.name if self.meta else self.variant.id

    @property
    def steps(self) -> Dict[str, Tuple[str, ...]]:
        return steps_of(self.document)

    def header(self) -> str:
        meta: Optional[DatasetMetaFeatures] = self.meta
        lines: List[str] = [
            "=" * HEADER_WIDTH,
            f"AGE-ML ablation study -- {self.variant.title}",
            "-" * HEADER_WIDTH,
            "Generated by `python -m experiments.ablation.specifications`.",
            "Do not edit by hand: change the generator and regenerate.",
            "",
            f"variant : {self.variant.id}",
            f"base    : resources/general-specification.yml "
            f"(sha256:{self.base_digest[:16]})",
            *(
                [f"dataset : {meta.name} ({meta.task}, target '{meta.target}')"]
                if meta
                else []
            ),
            "",
            *textwrap.wrap(self.variant.description, HEADER_WIDTH - 2),
        ]
        if meta:
            lines += [
                "",
                "dataset meta-features:",
                f"  instances       = {meta.instances}",
                f"  features        = {meta.features} ({meta.numeric_features} "
                f"numeric, {meta.categorical_features} categorical)",
                f"  missing values  = {meta.missing_value_ratio:.4%}",
                f"  max |skewness|  = {meta.max_absolute_skew:.2f}",
                f"  imbalance ratio = {meta.imbalance_ratio:.2f}"
                + (f" over {meta.classes} classes" if meta.classes else ""),
                "",
                "specialization:",
                *(
                    f"  {line}"
                    for reason in self.rationale
                    for line in textwrap.wrap(
                        reason, HEADER_WIDTH - 4, subsequent_indent="      "
                    )
                ),
            ]
        lines.append("=" * HEADER_WIDTH)
        return "\n".join(f"# {line}".rstrip() for line in lines)

    def to_yaml(self) -> str:
        body: str = yaml.dump(
            self.document,
            Dumper=_Dumper,
            sort_keys=False,
            default_flow_style=False,
            width=100,
        )
        return f"{self.header()}\n\n{body}"


#: Scalar lists shorter than this are emitted inline, as in the hand-written
#: specifications (e.g. ``imputation_strategy: [mean, median]``).
MAX_INLINE_LIST_WIDTH: int = 72


class _Dumper(yaml.SafeDumper):
    """A ``SafeDumper`` keeping short scalar lists inline, as authors write them."""

    def represent_sequence(  # type: ignore[override]
        self, tag: str, sequence: Any, flow_style: Optional[bool] = None
    ) -> Any:
        items: List[Any] = list(sequence)
        inline: bool = (
            all(
                item is None or isinstance(item, (str, int, float, bool))
                for item in items
            )
            and len(", ".join(str(item) for item in items)) <= MAX_INLINE_LIST_WIDTH
        )
        return super().represent_sequence(tag, items, flow_style=inline or flow_style)


def _quoted(names: Sequence[str]) -> str:
    return ", ".join(f"'{name}'" for name in sorted(names))
