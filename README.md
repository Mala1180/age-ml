# Agentic AutoML

Agentic AutoML is a Python project that uses LLM agents plus a constraint solver to design, implement, and execute machine learning pipelines from a YAML specification.

The workflow has two stages:
- **Planning**: parse a specification and enumerate valid pipeline structures.
- **Execution**: generate Python training code for each planned pipeline, validate it, run hyperparameter combinations, and track runs with MLflow.

## Repository Structure

- `automlllm/planning/`: planning agent and constraint solver logic.
- `automlllm/execution/`: code generation, validation, execution, and MLflow integration.
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

Run the full workflow:

```bash
python -m automlllm \
  --spec_path resources/general-specification.yml \
  --dataset_path resources/datasets/adult.csv
```

What this does:
1. Generates all feasible pipelines according to the provided specification.
2. Sets/uses MLflow experiment `adult-experiment`.
3. Generates and executes code of generated pipelines in parallel processes.
4. Uses MLflow to track runs, logging parameters, metrics, and artifacts.
5. Writes generated files in `out/pipeline_<id>/`.

## Specification Format

A specification file defines:
- `budgets.pipelines`: maximum number of planned pipelines to sample/execute (default: 20).
- `budgets.time`: runtime budget for exploration/execution scheduling. You can set `hours`, `minutes`, and/or `seconds` (default: `minutes: 60`).
- `budgets.workers`: number of execution workers used for concurrent pipeline runs (default: 5).
- `pipeline.defaults`: default attributes for steps (`mandatory`, `candidates`).
- `pipeline.steps`: admissible steps and candidates with parameter grids.
- `orderings`: ordering constraints (supports `sequence` shorthand).
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

## Notes and Current Limitations

- Semantic constraints (`natural_language`, `dataset`) are evaluated by the planning agent and translated into concrete constraints when satisfied.
- Pipeline code generation/execution retries up to 5 times for validation/execution failures.
- Experiment names are currently hard-coded in entrypoints (`adult-experiment` / `mattia-experiment`).

## License

Apache 2.0. See `LICENSE`.
