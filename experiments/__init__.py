"""The experimental campaign of AGE-ML.

``python -m experiments`` runs the dataset suite once, with a single
specification; :mod:`experiments.ablation` runs it once per specification
variant, repeated as many times as the statistics of the paper require.
"""

from pathlib import Path

#: Root of every result of the campaign, one subtree per LLM backend.
RESULTS_DIR: Path = Path(__file__).parent / "results"
