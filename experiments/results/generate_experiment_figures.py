from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

RESULTS_ROOT = Path(__file__).resolve().parent

DEFAULT_RESULT_DIRS = [
    "gemini-2.5-flash",
    "gemini-3.1-flash-lite-preview",
]

TIME_COLUMNS = [
    "Actual Time",
    "Equivalent Time",
    "LLM Inference Time",
    "ML Training Time",
]

NUMERIC_COLUMNS = [
    "OpenML ID",
    "Best Test-set Score",
    "Baseline",
    "Features",
    "Instances",
    "Numeric Features",
    "Discrete Features",
    "Workers",
    "Pipeline Budget",
    "Actual Pipelines",
    "Input Tokens",
    "Output Tokens",
    "Total Tokens",
    "Putative Cost ($)",
]


def safe_name(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("_").lower()


def load_results(csv_path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in TIME_COLUMNS:
        if col in df.columns:
            df[f"{col} (h)"] = pd.to_timedelta(df[col], errors="coerce").dt.total_seconds() / 3600
    if {"Equivalent Time (h)", "Actual Time (h)"}.issubset(df.columns):
        df["Parallel Speedup"] = df["Equivalent Time (h)"] / df["Actual Time (h)"]
    if {"Parallel Speedup", "Workers"}.issubset(df.columns):
        df["Worker Utilization"] = df["Parallel Speedup"] / df["Workers"]
    if {"Actual Pipelines", "Pipeline Budget"}.issubset(df.columns):
        df["Budget Utilization"] = df["Actual Pipelines"] / df["Pipeline Budget"]
    if {"Instances", "Features"}.issubset(df.columns):
        df["InstanceFeature Product"] = df["Instances"] * df["Features"]
    if {"Putative Cost ($)", "Actual Pipelines"}.issubset(df.columns):
        df["Cost per Pipeline ($)"] = df["Putative Cost ($)"] / df["Actual Pipelines"]
    return df


def annotate(ax, x, y, labels, dx=4, dy=4, fontsize=8):
    for xi, yi, label in zip(x, y, labels):
        if pd.notna(xi) and pd.notna(yi):
            ax.annotate(str(label), (xi, yi), xytext=(dx, dy), textcoords="offset points", fontsize=fontsize)


def save(fig, outdir: Path, stem: str, formats: list[str]) -> list[Path]:
    outdir.mkdir(parents=True, exist_ok=True)
    paths = []
    for fmt in formats:
        path = outdir / f"{stem}.{fmt}"
        fig.savefig(path, dpi=300, bbox_inches="tight")
        paths.append(path)
    plt.close(fig)
    return paths


def use_csv_row_order(ax) -> None:
    ax.invert_yaxis()


def performance_series(part: pd.DataFrame) -> list[tuple[str, pd.Series]]:
    series = [("Best pipeline", part["Best Test-set Score"])]
    if "Baseline" in part.columns and part["Baseline"].notna().any():
        series.append(("Baseline", part["Baseline"]))
    return series


def plot_performance_barh(
    part: pd.DataFrame,
    outdir: Path,
    formats: list[str],
    stem: str,
    title: str,
    xlabel: str,
    bar_format: str,
    log_scale: bool = False,
    xlim: tuple[float, float] | None = None,
) -> list[Path]:
    series = performance_series(part)
    y_positions = list(range(len(part)))
    fig, ax = plt.subplots(figsize=(8.5, max(3.8, 0.55 * len(part) + 1.2)))
    bar_height = 0.8 / len(series)
    for index, (label, values) in enumerate(series):
        offset = (index - (len(series) - 1) / 2) * bar_height
        y = [position + offset for position in y_positions]
        bars = ax.barh(y, values, height=bar_height, label=label)
        ax.bar_label(bars, fmt=bar_format, padding=3, fontsize=8)
    ax.set_yticks(y_positions)
    ax.set_yticklabels(part["Dataset"])
    ax.set_xlabel(xlabel)
    ax.set_title(title)
    if log_scale:
        ax.set_xscale("log")
    if xlim is not None:
        ax.set_xlim(*xlim)
    ax.grid(axis="x", linewidth=0.4, alpha=0.35)
    use_csv_row_order(ax)
    if len(series) > 1:
        ax.legend()
    return save(fig, outdir, stem, formats)


def plot_classification_scores(df: pd.DataFrame, outdir: Path, formats: list[str]) -> list[Path]:
    part = df[df.get("Problem", pd.Series(index=df.index)).eq("classification")].copy()
    if part.empty or not {"Dataset", "Best Test-set Score"}.issubset(part.columns):
        return []
    values = pd.concat([values for _, values in performance_series(part)]).dropna()
    xlim = (max(0, values.min() - 0.05), 1.01) if not values.empty else None
    return plot_performance_barh(
        part,
        outdir,
        formats,
        "02_classification_scores",
        "Best test-set performance on classification datasets",
        "Balanced accuracy",
        "%.3f",
        xlim=xlim,
    )


def plot_regression_scores(df: pd.DataFrame, outdir: Path, formats: list[str]) -> list[Path]:
    part = df[df.get("Problem", pd.Series(index=df.index)).eq("regression")].copy()
    if part.empty or not {"Dataset", "Best Test-set Score"}.issubset(part.columns):
        return []
    values = pd.concat([values for _, values in performance_series(part)]).dropna()
    log_scale = not values.empty and values.max() / max(values.min(), 1e-12) > 20
    return plot_performance_barh(
        part,
        outdir,
        formats,
        "03_regression_rmse",
        "Best test-set performance on regression datasets",
        "RMSE, log scale" if log_scale else "RMSE",
        "%.3g",
        log_scale=log_scale,
    )


def plot_time_breakdown(df: pd.DataFrame, outdir: Path, formats: list[str]) -> list[Path]:
    needed = {"Dataset", "LLM Inference Time (h)", "ML Training Time (h)", "Actual Time (h)"}
    if not needed.issubset(df.columns):
        return []
    part = df.copy()
    y = part["Dataset"]
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    ax.barh(y, part["LLM Inference Time (h)"], label="LLM inference, equivalent time")
    ax.barh(y, part["ML Training Time (h)"], left=part["LLM Inference Time (h)"], label="ML training, equivalent time")
    ax.scatter(part["Actual Time (h)"], y, marker="D", label="Actual time")
    ax.set_xlabel("Hours")
    ax.set_title("Time decomposition by dataset")
    ax.legend(loc="lower right")
    ax.grid(axis="x", linewidth=0.4, alpha=0.35)
    use_csv_row_order(ax)
    return save(fig, outdir, "04_time_breakdown", formats)


def plot_parallel_speedup(df: pd.DataFrame, outdir: Path, formats: list[str]) -> list[Path]:
    needed = {"Dataset", "Parallel Speedup", "Workers"}
    if not needed.issubset(df.columns):
        return []
    part = df.copy()
    fig, ax = plt.subplots(figsize=(8, 4.8))
    bars = ax.barh(part["Dataset"], part["Parallel Speedup"])
    ax.bar_label(bars, fmt="%.1fx", padding=3, fontsize=8)
    if part["Workers"].nunique(dropna=True) == 1:
        workers = part["Workers"].dropna().iloc[0]
        ax.axvline(workers, linestyle="--", linewidth=1, label=f"Worker count = {workers:g}")
        ax.legend()
    ax.set_xlabel("Equivalent serial time / wall-clock time")
    ax.set_title("Observed parallel speedup")
    ax.grid(axis="x", linewidth=0.4, alpha=0.35)
    use_csv_row_order(ax)
    return save(fig, outdir, "05_parallel_speedup", formats)


def plot_token_cost(df: pd.DataFrame, outdir: Path, formats: list[str]) -> list[Path]:
    needed = {"Dataset", "Input Tokens", "Output Tokens", "Putative Cost ($)"}
    if not needed.issubset(df.columns):
        return []
    part = df.copy()
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    input_m = part["Input Tokens"] / 1_000_000
    output_m = part["Output Tokens"] / 1_000_000
    ax.barh(part["Dataset"], input_m, label="Input tokens")
    ax.barh(part["Dataset"], output_m, left=input_m, label="Output tokens")
    ax.set_xlabel("Tokens, millions")
    ax.set_title("LLM token consumption")
    ax.legend(loc="lower right")
    ax.grid(axis="x", linewidth=0.4, alpha=0.35)
    use_csv_row_order(ax)
    paths = save(fig, outdir, "07_token_breakdown", formats)
    fig, ax = plt.subplots(figsize=(7.5, 5))
    ax.scatter(df["Total Tokens"] / 1_000_000, df["Putative Cost ($)"])
    annotate(ax, df["Total Tokens"] / 1_000_000, df["Putative Cost ($)"], df["Dataset"])
    ax.set_xlabel("Total tokens, millions")
    ax.set_ylabel("Putative cost, USD")
    ax.set_title("Putative cost versus total token usage")
    ax.grid(True, linewidth=0.4, alpha=0.35)
    paths.extend(save(fig, outdir, "08_cost_vs_tokens", formats))
    return paths


def plot_cost_per_pipeline(df: pd.DataFrame, outdir: Path, formats: list[str]) -> list[Path]:
    needed = {"Dataset", "Cost per Pipeline ($)"}
    if not needed.issubset(df.columns):
        return []
    part = df.copy()
    fig, ax = plt.subplots(figsize=(8, 4.8))
    bars = ax.barh(part["Dataset"], part["Cost per Pipeline ($)"])
    ax.bar_label(bars, fmt="$%.3f", padding=3, fontsize=8)
    ax.set_xlabel("USD per generated feasible pipeline")
    ax.set_title("Putative LLM cost normalized by generated pipelines")
    ax.grid(axis="x", linewidth=0.4, alpha=0.35)
    use_csv_row_order(ax)
    return save(fig, outdir, "12_cost_per_pipeline", formats)


def csv_path_for_result_path(path: str | Path) -> Path:
    result_path = resolve_result_path(path)
    if result_path.is_dir():
        csv_path = result_path / "results.csv"
    else:
        csv_path = result_path
    if not csv_path.exists():
        raise FileNotFoundError(f"Expected results CSV at {csv_path}")
    return csv_path


def label_for_result_path(path: str | Path) -> str:
    result_path = resolve_result_path(path)
    if result_path.is_dir():
        return result_path.name
    if result_path.name == "results.csv":
        return result_path.parent.name
    return result_path.stem


def load_comparison(inputs: list[str | Path]) -> tuple[pd.DataFrame, list[str], list[str]]:
    frames = []
    model_labels = []
    dataset_order = []
    for input_path in inputs:
        csv_path = csv_path_for_result_path(input_path)
        model = label_for_result_path(input_path)
        df = load_results(csv_path)
        df.insert(0, "Experiment", model)
        df.insert(1, "Source CSV", str(csv_path))
        frames.append(df)
        model_labels.append(model)
        if not dataset_order and "Dataset" in df.columns:
            dataset_order = df["Dataset"].dropna().tolist()
    combined = pd.concat(frames, ignore_index=True)
    for dataset in combined.get("Dataset", pd.Series(dtype=object)).dropna():
        if dataset not in dataset_order:
            dataset_order.append(dataset)
    if "Total Tokens" in combined.columns:
        combined["Total Tokens (M)"] = combined["Total Tokens"] / 1_000_000
    if "Input Tokens" in combined.columns:
        combined["Input Tokens (M)"] = combined["Input Tokens"] / 1_000_000
    if "Output Tokens" in combined.columns:
        combined["Output Tokens (M)"] = combined["Output Tokens"] / 1_000_000
    return combined, model_labels, dataset_order


def baseline_values_by_dataset(part: pd.DataFrame, datasets: list[str]) -> list[float]:
    values = []
    for dataset in datasets:
        rows = part[part["Dataset"].eq(dataset)]
        if "Baseline" in rows.columns:
            baseline = rows["Baseline"].dropna()
            values.append(baseline.iloc[0] if not baseline.empty else float("nan"))
        else:
            values.append(float("nan"))
    return values


def baseline_per_dataset(combined: pd.DataFrame, dataset_order: list[str]) -> pd.DataFrame:
    rows = []
    if not {"Dataset", "Problem", "Baseline"}.issubset(combined.columns):
        return pd.DataFrame()
    for dataset in dataset_order:
        part = combined[combined["Dataset"].eq(dataset)]
        baseline = part["Baseline"].dropna()
        problem = part["Problem"].dropna()
        if baseline.empty or problem.empty:
            continue
        rows.append(
            {
                "Dataset": dataset,
                "Problem": problem.iloc[0],
                "Baseline Score": baseline.iloc[0],
            }
        )
    return pd.DataFrame(rows)


def aggregate_comparison(combined: pd.DataFrame, model_labels: list[str]) -> pd.DataFrame:
    rows = []
    for model in model_labels:
        part = combined[combined["Experiment"].eq(model)]
        classification = part[part.get("Problem", pd.Series(index=part.index)).eq("classification")]
        regression = part[part.get("Problem", pd.Series(index=part.index)).eq("regression")]
        rows.append(
            {
                "Experiment": model,
                "Datasets": len(part),
                "Classification Datasets": len(classification),
                "Regression Datasets": len(regression),
                "Mean Classification Score": classification.get("Best Test-set Score", pd.Series(dtype=float)).mean(),
                "Mean Classification Baseline": classification.get("Baseline", pd.Series(dtype=float)).mean(),
                "Mean Regression RMSE": regression.get("Best Test-set Score", pd.Series(dtype=float)).mean(),
                "Mean Regression Baseline": regression.get("Baseline", pd.Series(dtype=float)).mean(),
                "Total Actual Time (h)": part.get("Actual Time (h)", pd.Series(dtype=float)).sum(),
                "Total Equivalent Time (h)": part.get("Equivalent Time (h)", pd.Series(dtype=float)).sum(),
                "Total LLM Inference Time (h)": part.get("LLM Inference Time (h)", pd.Series(dtype=float)).sum(),
                "Total ML Training Time (h)": part.get("ML Training Time (h)", pd.Series(dtype=float)).sum(),
                "Mean Parallel Speedup": part.get("Parallel Speedup", pd.Series(dtype=float)).mean(),
                "Total Input Tokens": part.get("Input Tokens", pd.Series(dtype=float)).sum(),
                "Total Output Tokens": part.get("Output Tokens", pd.Series(dtype=float)).sum(),
                "Total Tokens": part.get("Total Tokens", pd.Series(dtype=float)).sum(),
                "Total Putative Cost ($)": part.get("Putative Cost ($)", pd.Series(dtype=float)).sum(),
                "Mean Cost per Pipeline ($)": part.get("Cost per Pipeline ($)", pd.Series(dtype=float)).mean(),
                "Total Actual Pipelines": part.get("Actual Pipelines", pd.Series(dtype=float)).sum(),
            }
        )
    return pd.DataFrame(rows)


def values_by_dataset(part: pd.DataFrame, datasets: list[str], model: str, metric: str) -> list[float]:
    values = []
    model_part = part[part["Experiment"].eq(model)].set_index("Dataset")
    for dataset in datasets:
        if dataset in model_part.index:
            values.append(model_part.loc[dataset, metric])
        else:
            values.append(float("nan"))
    return values


def plot_grouped_barh(
    combined: pd.DataFrame,
    model_labels: list[str],
    dataset_order: list[str],
    outdir: Path,
    formats: list[str],
    stem: str,
    metric: str,
    title: str,
    xlabel: str,
    problem: str | None = None,
    log_scale: bool = False,
    include_baseline: bool = False,
) -> list[Path]:
    if not {"Dataset", "Experiment", metric}.issubset(combined.columns):
        return []
    part = combined.copy()
    if problem is not None:
        part = part[part.get("Problem", pd.Series(index=part.index)).eq(problem)]
    datasets = [dataset for dataset in dataset_order if dataset in set(part["Dataset"])]
    if not datasets:
        return []
    labels = model_labels.copy()
    if include_baseline and "Baseline" in part.columns and part["Baseline"].notna().any():
        labels.append("Baseline")
    y_positions = list(range(len(datasets)))
    bar_height = 0.8 / max(len(labels), 1)
    fig, ax = plt.subplots(figsize=(9, max(4, 0.55 * len(datasets) + 1.2)))
    for index, label in enumerate(labels):
        offset = (index - (len(labels) - 1) / 2) * bar_height
        y = [position + offset for position in y_positions]
        if label == "Baseline":
            values = baseline_values_by_dataset(part, datasets)
        else:
            values = values_by_dataset(part, datasets, label, metric)
        ax.barh(y, values, height=bar_height, label=label)
    ax.set_yticks(y_positions)
    ax.set_yticklabels(datasets)
    ax.set_xlabel(xlabel)
    ax.set_title(title)
    if log_scale:
        ax.set_xscale("log")
    ax.grid(axis="x", linewidth=0.4, alpha=0.35)
    ax.legend()
    use_csv_row_order(ax)
    return save(fig, outdir, stem, formats)


def plot_aggregate_time_breakdown(summary: pd.DataFrame, outdir: Path, formats: list[str]) -> list[Path]:
    needed = {"Experiment", "Total LLM Inference Time (h)", "Total ML Training Time (h)", "Total Actual Time (h)"}
    if not needed.issubset(summary.columns):
        return []
    x = list(range(len(summary)))
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    llm = summary["Total LLM Inference Time (h)"]
    training = summary["Total ML Training Time (h)"]
    ax.bar(x, llm, label="LLM inference, equivalent time")
    ax.bar(x, training, bottom=llm, label="ML training, equivalent time")
    ax.scatter(x, summary["Total Actual Time (h)"], marker="D", color="black", label="Actual wall-clock total", zorder=3)
    ax.set_xticks(x)
    ax.set_xticklabels(summary["Experiment"], rotation=15, ha="right")
    ax.set_ylabel("Hours")
    ax.set_title("Aggregate time usage by experiment")
    ax.grid(axis="y", linewidth=0.4, alpha=0.35)
    ax.legend()
    return save(fig, outdir, "01_aggregate_time_breakdown", formats)


def plot_aggregate_resource_usage(summary: pd.DataFrame, outdir: Path, formats: list[str]) -> list[Path]:
    needed = {"Experiment", "Total Input Tokens", "Total Output Tokens", "Total Putative Cost ($)"}
    if not needed.issubset(summary.columns):
        return []
    x = list(range(len(summary)))
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.6))
    input_m = summary["Total Input Tokens"] / 1_000_000
    output_m = summary["Total Output Tokens"] / 1_000_000
    axes[0].bar(x, input_m, label="Input tokens")
    axes[0].bar(x, output_m, bottom=input_m, label="Output tokens")
    axes[0].set_ylabel("Tokens, millions")
    axes[0].set_title("Aggregate token usage")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(summary["Experiment"], rotation=15, ha="right")
    axes[0].grid(axis="y", linewidth=0.4, alpha=0.35)
    axes[0].legend()
    bars = axes[1].bar(x, summary["Total Putative Cost ($)"])
    axes[1].bar_label(bars, fmt="$%.2f", padding=3, fontsize=8)
    axes[1].set_ylabel("USD")
    axes[1].set_title("Aggregate putative cost")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(summary["Experiment"], rotation=15, ha="right")
    axes[1].grid(axis="y", linewidth=0.4, alpha=0.35)
    return save(fig, outdir, "02_aggregate_resource_usage", formats)


def plot_aggregate_performance(
    summary: pd.DataFrame,
    baseline: pd.DataFrame,
    outdir: Path,
    formats: list[str],
) -> list[Path]:
    needed = {"Experiment", "Mean Classification Score", "Mean Regression RMSE"}
    if not needed.issubset(summary.columns):
        return []
    classification_baseline = baseline[baseline.get("Problem", pd.Series(index=baseline.index)).eq("classification")]
    regression_baseline = baseline[baseline.get("Problem", pd.Series(index=baseline.index)).eq("regression")]
    labels = summary["Experiment"].tolist()
    classification_values = summary["Mean Classification Score"].tolist()
    regression_values = summary["Mean Regression RMSE"].tolist()
    if not classification_baseline.empty or not regression_baseline.empty:
        labels.append("Baseline")
        classification_values.append(classification_baseline.get("Baseline Score", pd.Series(dtype=float)).mean())
        regression_values.append(regression_baseline.get("Baseline Score", pd.Series(dtype=float)).mean())
    x = list(range(len(labels)))
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.6))
    bars = axes[0].bar(x, classification_values)
    axes[0].bar_label(bars, fmt="%.3f", padding=3, fontsize=8)
    classification_series = pd.Series(classification_values).dropna()
    if not classification_series.empty:
        axes[0].set_ylim(max(0, classification_series.min() - 0.05), 1.01)
    axes[0].set_ylabel("Balanced accuracy")
    axes[0].set_title("Mean classification score")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(labels, rotation=15, ha="right")
    axes[0].grid(axis="y", linewidth=0.4, alpha=0.35)
    bars = axes[1].bar(x, regression_values)
    axes[1].bar_label(bars, fmt="%.3g", padding=3, fontsize=8)
    regression_series = pd.Series(regression_values).dropna()
    if not regression_series.empty and regression_series.max() / max(regression_series.min(), 1e-12) > 20:
        axes[1].set_yscale("log")
        axes[1].set_ylabel("RMSE, log scale")
    else:
        axes[1].set_ylabel("RMSE")
    axes[1].set_title("Mean regression RMSE")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(labels, rotation=15, ha="right")
    axes[1].grid(axis="y", linewidth=0.4, alpha=0.35)
    return save(fig, outdir, "03_aggregate_performance", formats)


def make_performance_deltas(combined: pd.DataFrame, model_labels: list[str], dataset_order: list[str]) -> pd.DataFrame:
    if len(model_labels) < 2 or not {"Dataset", "Experiment", "Problem", "Best Test-set Score"}.issubset(combined.columns):
        return pd.DataFrame()
    baseline, candidate = model_labels[:2]
    baseline_rows = combined[combined["Experiment"].eq(baseline)].set_index("Dataset")
    candidate_rows = combined[combined["Experiment"].eq(candidate)].set_index("Dataset")
    rows = []
    for dataset in dataset_order:
        if dataset not in baseline_rows.index or dataset not in candidate_rows.index:
            continue
        baseline_score = baseline_rows.loc[dataset, "Best Test-set Score"]
        candidate_score = candidate_rows.loc[dataset, "Best Test-set Score"]
        problem = baseline_rows.loc[dataset, "Problem"]
        if problem == "classification":
            improvement = (candidate_score - baseline_score) * 100
            metric = "balanced accuracy delta, percentage points"
        elif problem == "regression":
            improvement = (baseline_score - candidate_score) / baseline_score * 100
            metric = "RMSE reduction, percent"
        else:
            continue
        rows.append(
            {
                "Dataset": dataset,
                "Problem": problem,
                "Baseline Experiment": baseline,
                "Candidate Experiment": candidate,
                "Baseline Score": baseline_score,
                "Candidate Score": candidate_score,
                "Improvement": improvement,
                "Improvement Metric": metric,
                "Better Experiment": candidate if improvement > 0 else baseline if improvement < 0 else "tie",
            }
        )
    return pd.DataFrame(rows)


def plot_performance_delta(
    deltas: pd.DataFrame,
    outdir: Path,
    formats: list[str],
    problem: str,
    stem: str,
    title: str,
    xlabel: str,
) -> list[Path]:
    if deltas.empty:
        return []
    part = deltas[deltas["Problem"].eq(problem)].copy()
    if part.empty:
        return []
    colors = ["#2ca02c" if value >= 0 else "#d62728" for value in part["Improvement"]]
    fig, ax = plt.subplots(figsize=(8.5, max(3.8, 0.55 * len(part) + 1.2)))
    bars = ax.barh(part["Dataset"], part["Improvement"], color=colors)
    ax.bar_label(bars, fmt="%.2f", padding=3, fontsize=8)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlabel(xlabel)
    ax.set_title(title)
    ax.grid(axis="x", linewidth=0.4, alpha=0.35)
    use_csv_row_order(ax)
    return save(fig, outdir, stem, formats)


def make_comparison(inputs: list[str | Path], outdir: str | Path, formats: list[str]) -> list[Path]:
    outdir = Path(outdir)
    combined, model_labels, dataset_order = load_comparison(inputs)
    summary = aggregate_comparison(combined, model_labels)
    baseline_reference = baseline_per_dataset(combined, dataset_order)
    deltas = make_performance_deltas(combined, model_labels, dataset_order)
    outputs = []
    outputs.extend(plot_aggregate_time_breakdown(summary, outdir, formats))
    outputs.extend(plot_aggregate_resource_usage(summary, outdir, formats))
    outputs.extend(plot_aggregate_performance(summary, baseline_reference, outdir, formats))
    outputs.extend(
        plot_grouped_barh(
            combined,
            model_labels,
            dataset_order,
            outdir,
            formats,
            "04_classification_score_comparison",
            "Best Test-set Score",
            "Classification performance by dataset",
            "Balanced accuracy",
            problem="classification",
            include_baseline=True,
        )
    )
    outputs.extend(
        plot_grouped_barh(
            combined,
            model_labels,
            dataset_order,
            outdir,
            formats,
            "05_regression_rmse_comparison",
            "Best Test-set Score",
            "Regression performance by dataset",
            "RMSE",
            problem="regression",
            log_scale=True,
            include_baseline=True,
        )
    )
    outputs.extend(
        plot_grouped_barh(
            combined,
            model_labels,
            dataset_order,
            outdir,
            formats,
            "06_actual_time_comparison",
            "Actual Time (h)",
            "Actual wall-clock time by dataset",
            "Hours",
        )
    )
    outputs.extend(
        plot_grouped_barh(
            combined,
            model_labels,
            dataset_order,
            outdir,
            formats,
            "07_total_tokens_comparison",
            "Total Tokens (M)",
            "Total token usage by dataset",
            "Tokens, millions",
        )
    )
    outputs.extend(
        plot_grouped_barh(
            combined,
            model_labels,
            dataset_order,
            outdir,
            formats,
            "08_putative_cost_comparison",
            "Putative Cost ($)",
            "Putative cost by dataset",
            "USD",
        )
    )
    if len(model_labels) >= 2:
        baseline, candidate = model_labels[:2]
        outputs.extend(
            plot_performance_delta(
                deltas,
                outdir,
                formats,
                "classification",
                "09_classification_score_delta",
                f"Classification delta: {candidate} versus {baseline}",
                "Balanced accuracy delta, percentage points",
            )
        )
        outputs.extend(
            plot_performance_delta(
                deltas,
                outdir,
                formats,
                "regression",
                "10_regression_rmse_reduction",
                f"Regression RMSE reduction: {candidate} versus {baseline}",
                "RMSE reduction, percent",
            )
        )
    outdir.mkdir(parents=True, exist_ok=True)
    combined_path = outdir / "comparison_metrics.csv"
    summary_path = outdir / "aggregate_metrics.csv"
    deltas_path = outdir / "performance_deltas.csv"
    baseline_path = outdir / "baseline_metrics.csv"
    combined.to_csv(combined_path, index=False)
    summary.to_csv(summary_path, index=False)
    deltas.to_csv(deltas_path, index=False)
    baseline_reference.to_csv(baseline_path, index=False)
    outputs.extend([combined_path, summary_path, deltas_path, baseline_path])
    return outputs


def make_all(csv_path: str | Path, outdir: str | Path, formats: list[str]) -> list[Path]:
    df = load_results(csv_path)
    outdir = Path(outdir)
    plotters = [
        plot_classification_scores,
        plot_regression_scores,
        plot_time_breakdown,
        plot_parallel_speedup,
        plot_token_cost,
        plot_cost_per_pipeline,
    ]
    outputs = []
    for plotter in plotters:
        outputs.extend(plotter(df, outdir, formats))
    summary_path = outdir / "derived_metrics.csv"
    df.to_csv(summary_path, index=False)
    outputs.append(summary_path)
    return outputs


def resolve_result_path(path: str | Path) -> Path:
    path = Path(path)
    if path.exists():
        return path
    candidate = RESULTS_ROOT / path
    if candidate.exists():
        return candidate
    return path


def make_for_result_path(path: str | Path, formats: list[str], outdir: str | Path | None = None) -> list[Path]:
    result_path = resolve_result_path(path)
    if result_path.is_dir():
        csv_path = result_path / "results.csv"
        target_dir = Path(outdir) if outdir is not None else result_path / "figures"
    else:
        csv_path = result_path
        target_dir = Path(outdir) if outdir is not None else result_path.parent / "figures"
    if not csv_path.exists():
        raise FileNotFoundError(f"Expected results CSV at {csv_path}")
    return make_all(csv_path, target_dir, formats)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "inputs",
        nargs="*",
        help=(
            "Result directories or results.csv files. Defaults to the Gemini result "
            "directories in experiments/results."
        ),
    )
    parser.add_argument(
        "--outdir",
        help="Override output directory. Only valid when processing one input.",
    )
    parser.add_argument(
        "--comparison-dir",
        default=RESULTS_ROOT / "comparison",
        help="Directory where comparison figures will be written when at least two inputs are processed.",
    )
    parser.add_argument(
        "--no-comparison",
        action="store_true",
        help="Only generate per-experiment figures, without aggregate comparison charts.",
    )
    parser.add_argument("--formats", nargs="+", default=["png", "pdf"], help="Output formats, e.g. png pdf svg")
    args = parser.parse_args()
    inputs = args.inputs or DEFAULT_RESULT_DIRS
    if args.outdir and len(inputs) != 1:
        parser.error("--outdir can only be used with a single input")
    for input_path in inputs:
        outputs = make_for_result_path(input_path, args.formats, args.outdir)
        for path in outputs:
            print(path)
    if not args.no_comparison and len(inputs) >= 2:
        outputs = make_comparison(inputs, args.comparison_dir, args.formats)
        for path in outputs:
            print(path)


if __name__ == "__main__":
    main()
