# AGE-ML

**AGE-ML** is a framework for automatic generation and execution of end-to-end machine learning pipelines from explicit, human-readable specifications.

It shifts AutoML from a model-centric to a data-centric approach, enabling users to define high-level requirements and constraints for their ML workflows, including data preprocessing, feature engineering, model selection, and hyperparameter tuning.

The architecture combines symbolic reasoning with LLM-based code generation to derive admissible pipelines, synthesize implementations, execute them systematically, and preserve a traceable record of the entire process.

The workflow has three stages:
- **Planning**: parse a specification and enumerate valid pipeline structures.
- **Execution**: generate Python training code for each planned pipeline, validate it, run hyperparameter combinations, and track runs with `MLflow`.
- **Evaluation**: compare all generated models across all pipelines and pick the best overall model according to the selected metric.

## Repository Structure

- `ageml/planning/`: planning agent and constraint solver logic.
- `ageml/execution/`: code generation, validation, execution, and `MLflow` integration.
- `ageml/evaluation/`: cross-pipeline model evaluation and best-model selection.
- `ageml/specification/`: YAML parser, types, and validation logic.
- `resources/`: sample specifications and datasets.
- `tests/`: parser and specification validation tests.
- `out/`: downloaded artifacts for the best run and best pipeline.

## Requirements

- Python `>3.11,<4.0`
- Poetry for dependency management
- API key for the configured LLM provider

The project currently instantiates `ChatGoogleGenerativeAI` in [`ageml/common/model.py`](ageml/common/model.py), 
so you should provide a valid Google API key via environment (for example in `.env`, initialized from `.env.example`).

## Installation

If you don't have Poetry, install it with:
```bash
pip install -r requirements.txt
```

Then, install the project dependencies and set up the environment with:
```bash
poetry install
```

## Quick Start

Download the OpenML datasets used by experiments:

```bash
poetry run python -m experiments.download_datasets
```

Optional arguments:
- `--base_dir=<path>` to choose the root output folder (default: `resources/datasets`).
  The command will create/use `classification/` and `regression/` subfolders under that path.

Run the full workflow:

```bash
poetry run python -m ageml \
  --spec_path resources/general-specification.yml \
  --dataset_path resources/datasets/classification/adult.csv \
  --validation_metric balanced_accuracy \
  --maximize True
```

### Parameters

| Parameter           | Required | Default             | Description                                                                                                                                |
|---------------------|----------|---------------------|--------------------------------------------------------------------------------------------------------------------------------------------|
| `spec_path`         | Yes      | -                   | Filesystem path to the YAML specification file                                                                                             |
| `dataset_path`      | Yes      | -                   | Filesystem path to the input dataset (CSV)                                                                                                 |
| `validation_metric` | No       | `balanced_accuracy` | Metric for model selection. Supported: `accuracy`, `balanced_accuracy`, `f1`, `precision`, `recall`, `roc_auc`, `mse`, `rmse`, `mae`, `r2` |
| `maximize`          | No       | `True`              | Whether to maximize (`True`) or minimize (`False`) the metric                                                                              |

What this does:
1. Automatically identifies the most likely target column from the dataset.
2. Generates all feasible pipelines according to the provided specification.
3. Sets/uses the MLflow experiment named like the dataset (for example, `adult` for `adult.csv`).
4. Generates and executes code of generated pipelines in parallel processes.
5. Uses MLflow to track runs, logging parameters, metrics, and artifacts.
6. Evaluates models from all pipelines, compares them, and selects the best overall model.
7. Downloads the selected best-run and best-pipeline artifacts into `out/`.

## Run Full Experiments

To run the full experiments suite (all datasets in [download_datasets.py](experiments/download_datasets.py)):

```bash
poetry run python -m experiments
```

This command:
1. Downloads datasets from OpenML into `resources/datasets/classification` and `resources/datasets/regression`.
2. Runs the AutoML workflow on every dataset using `resources/general-specification.yml`.
3. Saves a summary CSV in `experiments/results/<model_name>/results.csv`.

## Specification Format

A specification file defines:
- `budgets.pipelines`: maximum number of planned pipelines to sample/execute (default: 20).
- `budgets.time`: runtime budget for exploration/execution scheduling. You can set `hours`, `minutes`, and/or `seconds` (default: `minutes: 60`).
- `budgets.workers`: number of execution workers used for concurrent pipeline runs (default: 5).
- `budgets.generation_attempts`: max retries per pipeline for code validation/execution loops (default: 5).
- `pipeline.defaults`: default attributes for steps (`mandatory`, `candidates`).
- `pipeline.steps`: admissible steps and candidates with parameter grids.
- `ordering`: ordering constraints (supports `sequence` shorthand).
- `constraints`: conditional `require` / `forbid` rules.
- `technical_details`: extra implementation requirements passed to the execution agent.

See examples:
- `resources/general-specification.yml`
- `resources/adult-specification.yml`
- `resources/housing-specification.yml`

## Outputs

The evaluation stage compares models across all pipelines and reports the best pipeline/run based on the selected metric.

After evaluation, the framework downloads selected artifacts into:
- `out/best_run/`: artifacts for the best hyperparameter run.
- `out/best_pipeline/`: artifacts for the best pipeline run, including generated pipeline code and explanation.


> MLflow tracks parent/child runs for pipeline/hyperparameter exploration.
> You can view results from the mlflow ui (`mlflow server`).

## Development Commands

Using Poe tasks (configured in `pyproject.toml`):

```bash
poetry run poe test
poetry run poe static-checks
poetry run poe format
poetry run poe coverage
```

## Paper

The corresponding paper of this framework is currently under review at the Future Generation Computer Systems (FGCS) journal.

## License

Apache 2.0. See `LICENSE`.
