"""Specification variants for the ablation study of AGE-ML.

The main experiments feed AGE-ML a single, general specification for every
dataset. This package answers the reviewers' request for an ablation on that
input: it derives from that very same file three levels of a priori knowledge,
keeping everything else (budgets, candidate operators, hyper-parameter grids
and the ordering of the steps) fixed. The README describes what each variant
carries.

Run ``python -m experiments.ablation.specifications`` to (re)generate them.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

DIR: Path = Path(__file__).parent

#: Where the generated specifications are written.
GENERATED_DIR: Path = DIR / "generated"


@dataclass(frozen=True)
class Variant:
    """One level of a priori knowledge, i.e. one point of the ablation."""

    id: str
    title: str

    #: Drop the constraints whose condition names a specific operator, i.e. the
    #: per-algorithm rules and the shared best practices of the general file.
    drop_operator_knowledge: bool = False

    #: Derive one file per dataset, narrowed down to its meta-features. The
    #: task is then known a priori, so the ``dataset`` conditions are dropped.
    dataset_specific: bool = False


POOR: Variant = Variant(
    id="poor",
    title="Knowledge-poor specification",
    drop_operator_knowledge=True,
)

GENERAL: Variant = Variant(
    id="general",
    title="General specification (baseline)",
)

SPECIFIC: Variant = Variant(
    id="specific",
    title="Dataset-specific specification",
    dataset_specific=True,
)

#: Declared from the poorest to the richest, as in the tables of the paper.
VARIANTS: Tuple[Variant, ...] = (POOR, GENERAL, SPECIFIC)

VARIANTS_BY_ID: Dict[str, Variant] = {variant.id: variant for variant in VARIANTS}


def get_variant(variant_id: str) -> Variant:
    if variant_id not in VARIANTS_BY_ID:
        raise ValueError(
            f"Unknown specification variant '{variant_id}', "
            f"admissible values are {sorted(VARIANTS_BY_ID)}."
        )
    return VARIANTS_BY_ID[variant_id]


def specification_path(variant: Variant, generated_dir: Path = GENERATED_DIR) -> Path:
    """Where the generated specification(s) of ``variant`` live.

    A directory of ``<dataset>.yml`` files for the dataset-specific variant, a
    single file for the others -- which is exactly what ``run_suite`` accepts.
    """
    return generated_dir / (
        variant.id if variant.dataset_specific else f"{variant.id}.yml"
    )
