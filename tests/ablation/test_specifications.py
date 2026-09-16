from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import pytest
import yaml

from ageml.specification import Specification
from experiments.ablation.specifications import (
    GENERAL,
    POOR,
    SPECIFIC,
    VARIANTS,
    Variant,
    get_variant,
    specification_path,
)
from experiments.ablation.specifications.generator import (
    GeneratedSpecification,
    condition_operator,
    generate,
    is_dataset_condition,
    names_an_operator,
    operator_of,
)
from experiments.ablation.specifications.meta_features import (
    CLASSIFICATION,
    REGRESSION,
    DatasetMetaFeatures,
    resolve_target,
)
from experiments.ablation.specifications.search_space import (
    count_pipelines,
    is_totally_ordered,
)
from resources import DIR as RESOURCES_DIR

BASE: str = (RESOURCES_DIR / "general-specification.yml").read_text()
BASE_DOCUMENT: Dict[str, Any] = yaml.safe_load(BASE)


def meta_features(**overrides: Any) -> DatasetMetaFeatures:
    """A classification dataset with every relevant knob at a neutral value."""
    defaults: Dict[str, Any] = {
        "name": "synthetic",
        "task": CLASSIFICATION,
        "target": "class",
        "instances": 5_000,
        "features": 30,
        "numeric_features": 30,
        "categorical_features": 0,
        "missing_value_ratio": 0.1,
        "max_absolute_skew": 5.0,
        "imbalance_ratio": 4.0,
        "classes": 2,
    }
    return DatasetMetaFeatures(**{**defaults, **overrides})


def specialized(**overrides: Any) -> GeneratedSpecification:
    return generate(BASE, SPECIFIC, meta_features(**overrides))


#: One generated specification per variant, dataset-specific ones included.
EVERY_SPECIFICATION: List[GeneratedSpecification] = [
    generate(
        BASE, variant, meta_features(**overrides) if variant.dataset_specific else None
    )
    for variant in VARIANTS
    for overrides in ({}, {"task": REGRESSION, "imbalance_ratio": 1.0})[
        : 2 if variant.dataset_specific else 1
    ]
]


class TestInvariantsAcrossVariants:
    """What must stay fixed for the ablation to isolate a single variable."""

    @pytest.mark.parametrize("section", ["budgets", "technical_details"])
    @pytest.mark.parametrize("specification", EVERY_SPECIFICATION)
    def test_section_is_reproduced_verbatim(self, specification, section):
        assert specification.document[section] == BASE_DOCUMENT[section]

    @pytest.mark.parametrize("specification", EVERY_SPECIFICATION)
    def test_ordering_is_total_over_the_surviving_steps(self, specification):
        assert specification.document["ordering"] == [
            {"sequence": list(specification.steps)}
        ]
        assert is_totally_ordered(specification.document)

    @pytest.mark.parametrize("specification", EVERY_SPECIFICATION)
    def test_no_constraint_refers_to_a_missing_step_or_candidate(self, specification):
        steps: Dict[str, Tuple[str, ...]] = specification.steps

        def exists(step: Optional[str], candidate: Optional[str]) -> bool:
            return step in steps and (candidate is None or candidate in steps[step])

        for constraint in specification.document["constraints"]:
            step, candidate = condition_operator(constraint)
            assert step is None or exists(step, candidate)
            for kind in ("require", "forbid"):
                assert all(
                    exists(*operator_of(node)) for node in constraint.get(kind, [])
                )

    @pytest.mark.parametrize("specification", EVERY_SPECIFICATION)
    def test_it_is_parsable_by_the_framework(self, specification):
        parsed: Specification = Specification.parse(specification.to_yaml())
        assert {step.id for step in parsed.steps} == set(specification.steps)
        assert parsed.pipelines == 30 and parsed.workers == 8


class TestVariants:
    def test_the_general_variant_reproduces_the_base_specification(self):
        general = generate(BASE, GENERAL)
        assert general.document["pipeline"] == BASE_DOCUMENT["pipeline"]
        assert general.document["constraints"] == BASE_DOCUMENT["constraints"]

    def test_operator_knowledge_is_what_the_poor_variant_drops(self):
        knowledge = [c for c in BASE_DOCUMENT["constraints"] if names_an_operator(c)]
        structural = [
            c for c in BASE_DOCUMENT["constraints"] if not names_an_operator(c)
        ]
        assert len(knowledge) == 18  # 14 per-algorithm + 4 shared best practices
        assert len(structural) == 5  # 2 dataset conditions, 2 exclusions, 1 task rule

    def test_the_poor_variant_only_drops_constraints(self):
        poor, general = generate(BASE, POOR), generate(BASE, GENERAL)
        assert poor.document["pipeline"] == general.document["pipeline"]
        assert poor.document["ordering"] == general.document["ordering"]
        assert not any(names_an_operator(c) for c in poor.document["constraints"])
        assert len(poor.document["constraints"]) == 5

    def test_the_poor_variant_widens_the_search_space(self):
        for task in (CLASSIFICATION, REGRESSION):
            assert count_pipelines(
                generate(BASE, POOR).document, task
            ) > count_pipelines(generate(BASE, GENERAL).document, task)

    def test_get_variant_rejects_unknown_ids(self):
        assert get_variant(GENERAL.id) is GENERAL
        with pytest.raises(ValueError):
            get_variant("does-not-exist")

    def test_specification_path_is_a_directory_only_when_per_dataset(self, tmp_path):
        assert specification_path(GENERAL, tmp_path).suffix == ".yml"
        assert specification_path(SPECIFIC, tmp_path).suffix == ""


class TestDatasetSpecificVariant:
    def test_it_requires_meta_features(self):
        with pytest.raises(ValueError):
            generate(BASE, SPECIFIC)

    def test_it_keeps_only_the_estimator_of_the_task(self):
        classification = specialized()
        regression = specialized(task=REGRESSION, imbalance_ratio=1.0)
        assert "regression" not in classification.steps
        assert "classification" not in regression.steps
        for specification, estimator in (
            (classification, CLASSIFICATION),
            (regression, REGRESSION),
        ):
            step = specification.document["pipeline"]["steps"][estimator]
            assert step["mandatory"] is True

    def test_it_drops_the_dataset_conditions(self):
        assert not any(
            is_dataset_condition(c) for c in specialized().document["constraints"]
        )

    @pytest.mark.parametrize(
        "overrides, absent_step",
        [
            ({"missing_value_ratio": 0.0}, "imputation"),
            ({"imbalance_ratio": 1.0}, "rebalancing"),
            ({"features": 10, "numeric_features": 10}, "features"),
            ({"features": 500, "numeric_features": 500}, "discretization"),
            ({"numeric_features": 1}, "discretization"),
        ],
    )
    def test_a_step_is_dropped_when_the_meta_features_say_so(
        self, overrides, absent_step
    ):
        assert absent_step in specialized().steps
        assert absent_step not in specialized(**overrides).steps

    def test_selected_features_scale_with_the_dimensionality(self):
        candidates = specialized(features=800, numeric_features=800).document[
            "pipeline"
        ]["steps"]["features"]["candidates"]
        select_k_best = next(
            c["select_k_best"] for c in candidates if "select_k_best" in c
        )
        assert select_k_best["params"]["k"] == [80, 200]

    def test_the_normalizers_match_the_skewness(self):
        heavy_tailed = specialized(max_absolute_skew=10.0).steps["normalization"]
        well_behaved = specialized(max_absolute_skew=0.5).steps["normalization"]
        assert "minmax" not in heavy_tailed and "power_transformer" in heavy_tailed
        assert "minmax" in well_behaved and "power_transformer" not in well_behaved

    def test_learners_that_do_not_scale_are_dropped(self):
        assert "knn" in specialized().steps["classification"]
        assert (
            "knn"
            not in specialized(instances=100_000, features=500).steps["classification"]
        )
        assert (
            "nn" not in specialized(instances=200, features=5).steps["classification"]
        )

    def test_it_narrows_the_search_space(self):
        assert count_pipelines(
            specialized().document, CLASSIFICATION
        ) < count_pipelines(generate(BASE, GENERAL).document, CLASSIFICATION)

    def test_every_surviving_step_keeps_at_least_one_candidate(self):
        for specification in EVERY_SPECIFICATION:
            assert all(candidates for candidates in specification.steps.values())

    def test_the_header_reports_every_decision(self):
        specification = specialized(missing_value_ratio=0.0)
        # the header wraps its lines, so compare on normalized whitespace
        header: str = " ".join(specification.header().replace("#", " ").split())
        assert "[imputation] dropped" in header
        assert all(
            " ".join(reason.split()) in header for reason in specification.rationale
        )


class TestTargetResolution:
    @pytest.mark.parametrize(
        "columns, task, expected",
        [
            (["a", "b", "class"], CLASSIFICATION, "class"),
            (["a", "b", "label"], CLASSIFICATION, "label"),
            (["a", "b", "c"], CLASSIFICATION, "c"),
            # a categorical last column cannot be a regression target
            (["value", "category"], REGRESSION, "value"),
        ],
    )
    def test_the_target_is_resolved_deterministically(self, columns, task, expected):
        size: int = 200
        frame = pd.DataFrame(
            {
                column: list(range(size))
                if column == "value"
                else [index % 3 for index in range(size)]
                for column in columns
            }
        )
        assert resolve_target(frame, task) == expected


class TestSearchSpace:
    def test_a_partial_ordering_is_detected(self):
        document = generate(BASE, GENERAL).document
        assert is_totally_ordered(document)
        assert not is_totally_ordered(
            {**document, "ordering": [{"sequence": ["imputation", "features"]}]}
        )

    def test_mandatory_steps_rule_out_the_empty_pipeline(self):
        document = generate(BASE, POOR).document
        assert count_pipelines(document) > count_pipelines(document, CLASSIFICATION)


def test_every_variant_is_declared_from_the_poorest_to_the_richest():
    assert [variant.id for variant in VARIANTS] == [
        "poor",
        "general",
        "specific",
    ]
    assert all(isinstance(variant, Variant) for variant in VARIANTS)
