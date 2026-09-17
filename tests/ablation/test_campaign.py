"""The bookkeeping of the repeated campaign: repetition ids, and resuming."""

from pathlib import Path
from typing import List

import pytest

from experiments.ablation.__main__ import DEFAULT_REPETITIONS, repetition_ids
from experiments.results_csv import SUMMARY_COLUMNS
from experiments.suite import already_recorded


def test_a_count_of_repetitions_is_expanded_into_ids_starting_at_one() -> None:
    assert repetition_ids(DEFAULT_REPETITIONS) == [1, 2, 3, 4, 5]
    assert repetition_ids(1) == [1]


@pytest.mark.parametrize("requested", [(4, 5), ["4", "5"]])
def test_explicit_repetitions_are_run_as_given(requested: List[int]) -> None:
    """How an interrupted campaign is resumed, or split across machines.

    ``fire`` hands over a tuple for ``--repetitions=4,5``, and strings when
    the value went through a shell that quoted it.
    """
    assert repetition_ids(requested) == [4, 5]


def test_nothing_is_recorded_without_a_results_file(tmp_path: Path) -> None:
    assert already_recorded(tmp_path / "results.csv") == set()

    empty: Path = tmp_path / "empty.csv"
    empty.touch()
    assert already_recorded(empty) == set()


def test_the_datasets_of_an_interrupted_suite_are_recorded(tmp_path: Path) -> None:
    """They are the ones ``run_suite`` skips instead of appending them twice."""
    results: Path = tmp_path / "results.csv"
    header: str = ",".join(SUMMARY_COLUMNS.values())
    row = lambda dataset: f"40983,{dataset}," + "," * (len(SUMMARY_COLUMNS) - 3)  # noqa: E731
    results.write_text("\n".join([header, row("wilt"), row("texture")]))

    assert already_recorded(results) == {"wilt", "texture"}
