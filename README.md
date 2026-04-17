# Agentic AutoML

Agentic AutoML is a Python project that uses LLM agents plus a constraint solver to design, implement, execute, and evaluate machine learning pipelines from a YAML specification.

The workflow has three stages:
- **Planning**: parse a specification and enumerate valid pipeline structures.
- **Execution**: generate Python training code for each planned pipeline, validate it, run hyperparameter combinations, and track runs with MLflow.
- **Evaluation**: compare all generated models across all pipelines and pick the best overall model according to the selected metric.

## Repository Structure

- `automlllm/planning/`: planning agent and constraint solver logic.
- `automlllm/execution/`: code generation, validation, execution, and MLflow integration.
- `automlllm/evaluation/`: cross-pipeline model evaluation and best-model selection.
- `automlllm/specification/`: YAML parser, types, and validation logic.
- `resources/`: sample specifications and datasets.
- `tests/`: parser and specification validation tests.
- `out/`: generated artifacts (`code.py`, `explanation.md`) per pipeline.

## Requirements

- Python `>3.11,<4.0`
- Poetry for dependency management
- API key for the configured LLM provider

The project currently instantiates `ChatGoogleGenerativeAI` in [`automlllm/common/model.py`](automlllm/common/model.py), 
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
poetry run python -m automlllm \
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
1. Generates all feasible pipelines according to the provided specification.
2. Sets/uses MLflow experiment `adult-experiment`.
3. Generates and executes code of generated pipelines in parallel processes.
4. Uses MLflow to track runs, logging parameters, metrics, and artifacts.
5. Evaluates models from all pipelines, compares them, and selects the best overall model.
6. Writes generated files in `out/pipeline_<id>/`.

## Run Full Experiments

To run the full experiments suite (all datasets in `classification` and `regression`):

```bash
poetry run python -m experiments
```

This command:
1. Downloads all OpenML datasets into `resources/datasets/classification` and `resources/datasets/regression`.
2. Runs the AutoML workflow on every dataset using `resources/general-specification.yml`.
3. Saves a summary CSV in `experiments/results/results_<model_name>.csv`.

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

For each generated pipeline, the execution agent writes:
- `out/pipeline_<id>/code.py`: generated training function.
- `out/pipeline_<id>/explanation.md`: concise natural-language explanation.

After execution, the evaluation stage compares models across all pipelines and reports the best pipeline/run based on the selected metric.


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

## License

Apache 2.0. See `LICENSE`.
