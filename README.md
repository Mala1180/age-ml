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
- `experiments/ablation/`: ablation studies on the inputs of the framework (currently: the specification).
- `experiments/results/`: results of the campaign, one subtree per LLM backend.
- `tests/`: parser and specification validation tests.
- `out/`: downloaded artifacts for the best run and best pipeline.

## Requirements

- Python `>3.11,<4.0`
- Poetry for dependency management
- API key for the configured LLM provider

The project instantiates `ChatGoogleGenerativeAI` in [`ageml/common/model.py`](ageml/common/model.py),
so you should provide a valid Google API key via environment (for example in `.env`, initialized from `.env.example`).
The Gemini model name defaults to `gemini-3.1-flash-lite-preview` and can be overridden per run with `--model_name`
(see [Quick Start](#quick-start) and [Run Full Experiments](#run-full-experiments)) — no code change required.

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
  --model_name gemini-2.5-flash \
  --validation_metric balanced_accuracy \
  --maximize True
```

### Parameters

| Parameter           | Required | Default                         | Description                                                                                                                                  |
|---------------------|----------|---------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------|
| `spec_path`         | Yes      | -                               | Filesystem path to the YAML specification file                                                                                               |
| `dataset_path`      | Yes      | -                               | Filesystem path to the input dataset (CSV)                                                                                                   |
| `model_name`        | No       | `gemini-3.1-flash-lite-preview` | LLM backend used for planning/execution/evaluation (default: `DEFAULT_MODEL_NAME` in [`ageml/common/__init__.py`](ageml/common/__init__.py)) |
| `validation_metric` | No       | `balanced_accuracy`             | Metric for model selection. Supported: `accuracy`, `balanced_accuracy`, `f1`, `precision`, `recall`, `roc_auc`, `mse`, `rmse`, `mae`, `r2`   |
| `maximize`          | No       | `True`                          | Whether to maximize (`True`) or minimize (`False`) the metric                                                                                |

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
poetry run python -m experiments --model_name gemini-2.5-flash --spec_path resources/general-specification.yml
```

`--model_name` is optional here too (same default as above) and determines the `<model_name>` results folder below.
`--spec_path` is also optional (default: `resources/general-specification.yml`) and is used for every dataset in the suite.
A directory can be passed as well, and is read as one `<dataset>.yml` specification per dataset (see the ablation study below).

This command:
1. Downloads datasets from OpenML into `resources/datasets/classification` and `resources/datasets/regression`.
2. Runs the AutoML workflow on every dataset using `resources/general-specification.yml`.
3. Saves a summary CSV in `experiments/results/<model_name>/results.csv`.

## Ablation on the Specification

The main experiments feed AGE-ML a single, general specification for every dataset.
The ablation varies *only* that input, over three levels of a priori knowledge, keeping
budgets, candidate operators, hyper-parameter grids and step ordering fixed:

| Variant    | What it carries                                                                                                               |
|------------|-------------------------------------------------------------------------------------------------------------------------------|
| `poor`     | the general search space without the AutoML domain knowledge: per-algorithm constraints and shared best practices are removed |
| `general`  | the specification used in the main experiments (baseline)                                                                     |
| `specific` | one specification per dataset, narrowed down to the steps and operators that suit the dataset's meta-features                 |

Generate the specification files (they are derived from `resources/general-specification.yml`,
so they are **not** tracked by git and must be regenerated after cloning, and whenever that
file or the generator changes):

```bash
poetry run poe ablation-specs
```

This writes, under `experiments/ablation/specifications/generated/`:
`poor.yml`, `general.yml`, `specific/<dataset>.yml` (one per dataset),
plus `meta-features.csv` and `manifest.csv` (the ablation matrix: steps, operators,
constraints and size of the planning search space of each generated file).

The `specific` files are derived from the meta-features of the dataset CSVs, so the
command downloads any missing dataset first (from the OpenML cache in `resources/org/`),
exactly as the suite does.

Then run the whole suite once per variant, repeated to measure the statistical
variance of the results (5 repetitions of 3 variants, i.e. 15 suites):

```bash
poetry run poe ablation-run
```

`--model_name` defaults to `gemini-3.1-flash-lite-preview`, the LLM of the campaign.
`--repetitions` sets how many repetitions to run (`--repetitions=3`) or exactly which
ones (`--repetitions=4,5`). `--variants` restricts the run (e.g. `--variants=poor,general`),
and there is one shortcut per variant, to spread the campaign over several days or machines:

```bash
poetry run poe ablation-poor       # the 5 repetitions of poor.yml
poetry run poe ablation-general    # the 5 repetitions of general.yml
poetry run poe ablation-specific   # the 5 repetitions of specific/<dataset>.yml
```

Each repetition of each variant gets its own directory, with the same schema as the
main experiments (`experiments/results/<model_name>/results.csv`):

```
experiments/results/<model_name>/
└── <variant>/                    # poor, general, specific
    ├── run-1/
    │   ├── results.csv           # one summary row per dataset of the suite
    │   └── artifacts/<dataset>/  # best_run and best_pipeline of that dataset
    ├── run-2/
    └── ...
```

Repetitions are the *outer* loop, so after the first pass every variant already has a
complete -- if not yet significant -- `run-1`. The 15 `results.csv` are deliberately kept
apart, to be aggregated afterwards into one table per variant.

An interrupted suite is resumed by re-running the very same command: the datasets already
summarized in `run-<n>/results.csv` are skipped, never appended twice. To redo a repetition
from scratch, delete its `run-<n>` directory.

The `specific` variant is *generated*, never hand-written: every pruning decision
is a pure function of the dataset meta-features (`specialize` in
`experiments/ablation/specifications/generator.py`), and the rationale of each decision
taken is written in the header of the generated file.

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
- `experiments/ablation/specifications/generated/` (generated, see above)

> Note: all the steps that a specification declares should also appear in its `ordering`
> section. A partial ordering lets the planner permute the unordered steps, which makes
> the number of admissible pipelines grow combinatorially; the generator enforces a total
> ordering, and `search_space.py` reports the resulting number of admissible pipelines.

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

Ablation study (see [Ablation on the Specification](#ablation-on-the-specification)):

```bash
poetry run poe ablation-specs     # generate the specification variants
poetry run poe ablation-run       # run the suite 5 times per variant (15 suites)
poetry run poe ablation-poor      # only the repetitions of the knowledge-poor variant
poetry run poe ablation-general   # only the repetitions of the general variant
poetry run poe ablation-specific  # only the repetitions of the dataset-specific variant
```

`poetry run poe` lists every task with its description.

## Paper

The corresponding paper of this framework is currently under review at the Future Generation Computer Systems (FGCS) journal.

## License

Apache 2.0. See `LICENSE`.
