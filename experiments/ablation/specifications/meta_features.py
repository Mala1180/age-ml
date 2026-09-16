"""Deterministic dataset meta-features used to specialize specifications.

The dataset-specific variant of the ablation must not be hand-tuned per
dataset: every pruning decision is a pure function of the meta-features
computed here, so the whole family of specifications is reproducible from the
raw CSVs.
"""

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from pandas.api.types import is_bool_dtype, is_numeric_dtype

CLASSIFICATION: str = "classification"
REGRESSION: str = "regression"

#: Column names that usually denote the target, mirroring the hints given to
#: the LLM in :func:`ageml.app.identify_target_feature`.
TARGET_NAME_HINTS: frozenset = frozenset({"class", "target", "label", "y", "outcome"})

#: A categorical target has at most this many distinct values; a numeric one
#: has more than this (absolute, and relative to the number of instances).
MAX_CLASSES: int = 50
MIN_REGRESSION_CARDINALITY: int = 20
MIN_REGRESSION_CARDINALITY_RATIO: float = 0.05


@dataclass(frozen=True)
class DatasetMetaFeatures:
    """The dataset descriptors the specialization is allowed to look at."""

    name: str
    task: str
    target: str
    instances: int
    features: int
    numeric_features: int
    categorical_features: int
    missing_value_ratio: float
    max_absolute_skew: float
    imbalance_ratio: float
    classes: int

    @property
    def numeric_ratio(self) -> float:
        """Fraction of input features that are numeric (non-boolean)."""
        return self.numeric_features / self.features if self.features else 0.0

    @property
    def cells(self) -> int:
        """``instances * features``, a proxy for the cost of a single fit."""
        return self.instances * self.features

    def as_row(self) -> Dict[str, Any]:
        """The meta-features as one row of ``meta-features.csv``."""
        row: Dict[str, Any] = asdict(self)
        for key in ("missing_value_ratio", "max_absolute_skew", "imbalance_ratio"):
            row[key] = round(row[key], 6)
        return row


def _is_numeric(series: pd.Series) -> bool:
    return bool(is_numeric_dtype(series) and not is_bool_dtype(series))


def _is_plausible_target(series: pd.Series, task: str) -> bool:
    cardinality: int = int(series.nunique(dropna=True))
    if task == REGRESSION:
        minimum: float = max(
            MIN_REGRESSION_CARDINALITY,
            MIN_REGRESSION_CARDINALITY_RATIO * len(series),
        )
        return _is_numeric(series) and cardinality > minimum
    return 1 < cardinality <= MAX_CLASSES


def resolve_target(df: pd.DataFrame, task: str) -> str:
    """Pick the target column of ``df`` deterministically.

    The framework asks the LLM to identify the target
    (:func:`ageml.app.identify_target_feature`), but meta-feature extraction
    cannot depend on a stochastic component: the heuristics stated in that very
    prompt are applied here instead -- a name hint first, then the right-most
    column whose data type and cardinality fit ``task``, then the last column.
    """
    columns: List[str] = [str(column) for column in df.columns]
    hinted: List[str] = [
        column for column in columns if column.strip().lower() in TARGET_NAME_HINTS
    ]
    for candidates in (hinted, columns):
        for column in reversed(candidates):
            if _is_plausible_target(df[column], task):
                return column
    return columns[-1]


def compute_meta_features(
    dataset_path: Path,
    task: str,
    name: Optional[str] = None,
    target: Optional[str] = None,
) -> DatasetMetaFeatures:
    """Compute the meta-features of the dataset stored at ``dataset_path``."""
    df: pd.DataFrame = pd.read_csv(dataset_path)
    resolved_target: str = target or resolve_target(df, task)
    features: pd.DataFrame = df.drop(columns=[resolved_target])
    numeric: List[str] = [
        column for column in features.columns if _is_numeric(features[column])
    ]
    skew = features[numeric].skew(numeric_only=True).abs().to_numpy() if numeric else []
    counts = (
        df[resolved_target].value_counts(dropna=True)
        if task == CLASSIFICATION
        else pd.Series(dtype=float)
    )
    return DatasetMetaFeatures(
        name=name or dataset_path.stem,
        task=task,
        target=resolved_target,
        instances=int(df.shape[0]),
        features=int(features.shape[1]),
        numeric_features=len(numeric),
        categorical_features=int(features.shape[1]) - len(numeric),
        missing_value_ratio=float(features.isna().to_numpy().mean())
        if features.size
        else 0.0,
        max_absolute_skew=float(np.nanmax(skew))
        if len(skew) and not bool(np.all(np.isnan(skew)))
        else 0.0,
        imbalance_ratio=float(counts.max() / counts.min())
        if not counts.empty and int(counts.min()) > 0
        else 1.0,
        classes=int(counts.size),
    )
