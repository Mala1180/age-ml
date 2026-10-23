"""One configuration, sequential baseline/ablation jobs and frozen holdout rows."""

import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Literal

import fire
import yaml
from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

from ageml.common.llm_config import resolve_llm_config
from ageml.protocol import (
    VERSION,
    digest,
    environment_identity,
    file_hash,
    prepare,
    write_json,
)
from ageml.specification import Specification
from experiments.ablation.specifications import get_variant
from experiments.ablation.specifications.generator import generate
from experiments.ablation.specifications.meta_features import (
    compute_meta_features_from_frame,
)
from experiments.ablation.validation import get_validation_config
from experiments.download_datasets import (
    DEFAULT_OPENML_DATASETS,
    download_all_openml_datasets,
)
from experiments.suite import run_suite
from resources import DIR as RESOURCES_DIR

ROOT = Path(__file__).resolve().parents[1]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Backend(StrictModel):
    provider: Literal["gemini", "ollama"] = "ollama"
    name: str
    base_url: str | None = None
    api_key_env: str | None = None
    seed: StrictInt | None = None
    temperature: float | None = None


class Ablations(StrictModel):
    specification: list[Literal["poor", "general", "specific"]] = Field(
        default_factory=list
    )
    validation: list[Literal["no-semantic-retry", "no-execution-retry"]] = Field(
        default_factory=list
    )
    no_csp: bool = False


class Campaign(StrictModel):
    name: str
    model: Backend
    specification: str = "resources/general-specification.yml"
    output_dir: str
    repetitions: StrictInt | list[StrictInt] = 1
    split_seed: StrictInt = 42
    run_seed: StrictInt = 42
    evaluation_protocol: Literal["holdout", "hamlet_cv"] = "holdout"
    time_budget_seconds: StrictInt | None = None
    baseline: bool = True
    ablations: Ablations = Field(default_factory=Ablations)
    datasets: dict[str, dict[str, StrictInt]] = Field(
        default_factory=lambda: DEFAULT_OPENML_DATASETS
    )

    @model_validator(mode="after")
    def validate_selection(self):
        for seed in (self.split_seed, self.run_seed, self.model.seed):
            if seed is not None and not 0 <= seed <= 2**32 - 1:
                raise ValueError("Seeds must be unsigned 32-bit integers")
        if self.model.temperature is not None and not 0 <= self.model.temperature <= 2:
            raise ValueError("Temperature must be between 0 and 2")
        if self.time_budget_seconds is not None and self.time_budget_seconds <= 0:
            raise ValueError("time_budget_seconds must be positive")
        reps = self.repetition_ids()
        if not reps or any(r < 1 for r in reps) or len(reps) != len(set(reps)):
            raise ValueError("Repetitions must be positive and unique")
        names = []
        for task, datasets in self.datasets.items():
            if task not in ("classification", "regression") or not datasets:
                raise ValueError(
                    "Datasets require classification/regression tasks and nonempty mappings"
                )
            for name, dataset_id in datasets.items():
                if (
                    not name
                    or any(
                        c
                        not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-"
                        for c in name
                    )
                    or name in (".", "..")
                    or dataset_id < 1
                ):
                    raise ValueError(
                        "Dataset names must be safe filenames and OpenML IDs positive"
                    )
                names.append(name)
        if not names or len(names) != len(set(names)):
            raise ValueError("Dataset names must be nonempty and globally unique")
        for values in (self.ablations.specification, self.ablations.validation):
            if len(values) != len(set(values)):
                raise ValueError("Duplicate ablation requested")
        if self.baseline and "general" in self.ablations.specification:
            raise ValueError(
                "baseline already supplies general; remove specification/general or disable baseline"
            )
        if (
            not self.baseline
            and not self.ablations.specification
            and not self.ablations.validation
            and not self.ablations.no_csp
        ):
            raise ValueError("Select at least one experiment condition")
        return self

    def repetition_ids(self):
        return (
            list(range(1, self.repetitions + 1))
            if isinstance(self.repetitions, int)
            else self.repetitions
        )


def repo_path(path):
    value = Path(path).expanduser()
    return value.resolve() if value.is_absolute() else (ROOT / value).resolve()


def build_plan(config):
    output = repo_path(config.output_dir)
    if output == ROOT or any(
        output.is_relative_to(ROOT / folder)
        for folder in ("tmp", "out", "ageml", "resources")
    ):
        raise ValueError(
            "output_dir must be separate from source/data and the agents' disposable tmp/out directories"
        )
    jobs = []
    if config.baseline:
        jobs.append({"id": "baseline", "kind": "baseline"})
    jobs.extend(
        {"id": f"specification-{variant}", "kind": "specification", "variant": variant}
        for variant in config.ablations.specification
    )
    jobs.extend(
        {"id": f"validation-{variant}", "kind": "validation", "variant": variant}
        for variant in config.ablations.validation
    )
    if config.ablations.no_csp:
        jobs.append({"id": "no-csp", "kind": "no-csp"})
    spec = Specification.parse(repo_path(config.specification).read_text())
    runs = (
        len(jobs)
        * len(config.repetition_ids())
        * sum(map(len, config.datasets.values()))
    )
    return {
        "name": config.name,
        "protocol_version": VERSION,
        "evaluation_protocol": config.evaluation_protocol,
        "run_seed": config.run_seed,
        "cv_folds_per_candidate": 10
        if config.evaluation_protocol == "hamlet_cv"
        else 0,
        "jobs": jobs,
        "repetitions": config.repetition_ids(),
        "dataset_runs": runs,
        "nominal_exploration_hours": runs
        * (config.time_budget_seconds or spec.budgets.time.total_seconds)
        / 3600,
        "output_dir": str(repo_path(config.output_dir)),
    }


@contextmanager
def checkout_lock():
    """Existing agents use shared tmp/out paths; forbid concurrent campaigns here."""
    with (ROOT / ".age-ml-campaign.lock").open("a+b") as stream:
        if os.name == "nt":
            import msvcrt

            stream.write(b"0")
            stream.flush()
            stream.seek(0)
            acquire = lambda: msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            release = lambda: msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            acquire = lambda: fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            release = lambda: fcntl.flock(stream, fcntl.LOCK_UN)
        try:
            acquire()
        except OSError as exc:
            raise RuntimeError(
                "Another campaign is using this checkout; wait or use a separate checkout/container"
            ) from exc
        try:
            yield
        finally:
            stream.seek(0)
            release()


def _save_or_verify(path, value):
    if path.exists():
        if json.loads(path.read_text()) != value:
            raise ValueError(
                f"Frozen campaign artifact differs: {path}; choose a new output_dir"
            )
    else:
        write_json(path, value, exclusive=True)


def _prepare(config, plan, llm):
    output = repo_path(config.output_dir)
    base = repo_path(config.specification).read_text()
    source_evidence, split_paths, rendered = {}, {}, {}
    for task, datasets in config.datasets.items():
        for name in datasets:
            source = RESOURCES_DIR / "datasets" / task / f"{name}.csv"
            metadata = json.loads(source.with_suffix(".metadata.json").read_text())
            if metadata["task"] != task:
                raise ValueError("Dataset metadata task conflict")
            split_path = output / "splits" / f"{name}.json"
            df, split = prepare(
                source,
                metadata["target_column"],
                task,
                config.split_seed,
                split_path if split_path.exists() else None,
                evaluation_protocol=config.evaluation_protocol,
            )
            source_evidence[name] = {
                "source_sha256": split["source_sha256"],
                "split_identity": split["split_identity"],
                "metadata": metadata,
            }
            split_paths[name] = str(split_path)
            training = df.iloc[split["partitions"]["train"]].reset_index(drop=True)
            meta = compute_meta_features_from_frame(
                training, task, name, metadata["target_column"]
            )
            for variant in config.ablations.specification:
                if variant == "specific":
                    rendered[f"specific/{name}.yml"] = generate(
                        base, get_variant(variant), meta
                    ).to_yaml()
            # Keep manifests in memory until campaign identity has been checked.
            source_evidence[name]["manifest"] = split
    for variant in config.ablations.specification:
        if variant != "specific":
            rendered[f"{variant}.yml"] = generate(base, get_variant(variant)).to_yaml()
    code_files = [
        p
        for directory in (ROOT / "ageml", ROOT / "experiments")
        for p in directory.rglob("*.py")
        if "results" not in p.relative_to(ROOT).parts and not p.is_relative_to(output)
    ]
    identity = {
        "config": config.model_dump(mode="json"),
        "model": llm.public_dict(),
        "plan": plan,
        "source_evidence": source_evidence,
        "base_specification_sha256": file_hash(repo_path(config.specification)),
        "generated_specifications": {
            name: digest(text) for name, text in rendered.items()
        },
        "code_sha256": digest(
            {str(p.relative_to(ROOT)): file_hash(p) for p in sorted(code_files)}
        ),
        "environment": json.loads(json.dumps(environment_identity())),
        "thread_environment": {
            key: os.environ.get(key)
            for key in (
                "OMP_NUM_THREADS",
                "OPENBLAS_NUM_THREADS",
                "MKL_NUM_THREADS",
                "NUMEXPR_NUM_THREADS",
            )
        },
    }
    identity["campaign_identity"] = digest(identity)
    _save_or_verify(output / "campaign.json", identity)
    for name, evidence in source_evidence.items():
        _save_or_verify(Path(split_paths[name]), evidence["manifest"])
    for name, text in rendered.items():
        path = output / "specifications" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.read_text() != text:
            raise ValueError(f"Specification changed: {path}")
        path.write_text(text)
    return split_paths


@contextmanager
def working_directory(path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def run(config: str, dry_run: bool = False):
    """Run --config campaigns/ollama12.yml; --dry_run previews with no downloads/LLM calls."""
    settings = Campaign.model_validate(yaml.safe_load(Path(config).read_text()))
    plan = build_plan(settings)
    if dry_run:
        return plan
    if settings.model.name.startswith("CHANGE_ME"):
        raise ValueError(
            "Set model.name to an installed model tag in the campaign YAML"
        )
    llm = resolve_llm_config(
        settings.model.name,
        settings.model.provider,
        settings.model.base_url,
        settings.model.api_key_env,
        settings.model.seed,
        settings.model.temperature,
    )
    # Agent code uses relative paths; serialize campaigns and anchor the checkout.
    with checkout_lock(), working_directory(ROOT):
        download_all_openml_datasets(settings.datasets)
        splits = _prepare(settings, plan, llm)
        output = repo_path(settings.output_dir)
        for repetition in settings.repetition_ids():
            for job in plan["jobs"]:
                spec = repo_path(settings.specification)
                options = {}
                if job["kind"] == "specification":
                    variant = job["variant"]
                    spec = (
                        output
                        / "specifications"
                        / ("specific" if variant == "specific" else f"{variant}.yml")
                    )
                elif job["kind"] == "validation":
                    variant = get_validation_config(job["variant"])
                    options = {
                        "retry_on_semantic_failure": variant.retry_on_semantic_failure,
                        "retry_on_execution_failure": variant.retry_on_execution_failure,
                    }
                elif job["kind"] == "no-csp":
                    options = {"use_csp": False}
                destination = output / job["id"] / f"run-{repetition}"
                print(
                    f"Campaign {settings.name}: {job['id']}, repetition {repetition}",
                    flush=True,
                )
                result = run_suite(
                    model_name=llm.model_name,
                    evaluation_protocol=settings.evaluation_protocol,
                    run_seed=settings.run_seed,
                    model_seed=settings.model.seed,
                    model_temperature=settings.model.temperature,
                    time_budget_seconds=settings.time_budget_seconds,
                    model_provider=llm.provider,
                    model_base_url=llm.base_url,
                    model_api_key_env=llm.api_key_env,
                    spec_path=spec,
                    output_dir=destination,
                    datasets=settings.datasets,
                    split_manifests=splits,
                    split_seed=settings.split_seed,
                    download_datasets=False,
                    **options,
                )
                _save_or_verify(
                    destination / "campaign-job.json",
                    {
                        "campaign_identity": json.loads(
                            (output / "campaign.json").read_text()
                        )["campaign_identity"],
                        "job": job,
                        "repetition": repetition,
                        "summary": str(result),
                    },
                )
    return {"campaign": str(output / "campaign.json"), "output_dir": str(output)}


if __name__ == "__main__":
    fire.Fire(run)
