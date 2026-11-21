"""Accessible publication figures for the committed competitor summaries."""

from contextlib import contextmanager
from textwrap import fill

import numpy as np

from scripts.competitor_data import METHODS, MISSING, dataset_order, label

COLORS = {METHODS[0]: "#345995", METHODS[1]: "#A64B00"}
MARKERS = {METHODS[0]: "o", METHODS[1]: "s"}
STYLE = {
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.titlesize": 13,
    "axes.labelsize": 10,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "svg.fonttype": "none",
    "savefig.facecolor": "white",
    "text.color": "#222222",
    "axes.labelcolor": "#222222",
    "xtick.color": "#222222",
    "ytick.color": "#222222",
}


@contextmanager
def plot_style():
    import matplotlib

    # RcParams validates settings and satisfies Matplotlib's typed rc_context API.
    with matplotlib.rc_context(matplotlib.RcParams(STYLE)):
        yield


def contrast_on_white(color):
    rgb = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in rgb]
    luminance = sum(w * v for w, v in zip((0.2126, 0.7152, 0.0722), linear))
    return 1.05 / (luminance + 0.05)


def accessibility_notes():
    return dict(
        method_colors=COLORS,
        markers=MARKERS,
        color_contrast_against_white={
            k: contrast_on_white(v) for k, v in COLORS.items()
        },
        non_color_channels=[
            "direct method labels",
            "circle versus square markers",
            "failure and missing hatches",
            "numeric counts",
        ],
        alternative_representations=[
            "HTML tables",
            "CSV tables",
            "figure alt text",
            "vector PDF and editable SVG",
        ],
        limitations="Static PDF/SVG files are not certified tagged accessible documents; use the companion HTML and CSV tables.",
    )


def save(fig, directory, name, formats, caption):
    import matplotlib.pyplot as plt

    directory.mkdir(parents=True, exist_ok=True)
    fig.text(
        0.01,
        0.015,
        fill(caption, width=max(80, int(fig.get_figwidth() * 16))),
        fontsize=8,
        color="#444444",
        va="bottom",
    )
    fig.tight_layout(rect=(0, 0.09, 1, 0.94))
    for extension in formats:
        fig.savefig(directory / f"{name}.{extension}", dpi=200, bbox_inches="tight")
    plt.close(fig)


def outcomes(frame, info, directory, formats):
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    names = dataset_order(info["datasets"])
    planned = len(info["repetitions"])
    fig, ax = plt.subplots(figsize=(11.5, max(6.2, len(names) * 0.72 + 2)))
    for i, name in enumerate(names):
        for j, method in enumerate(METHODS):
            group = frame[frame.dataset.eq(name) & frame.method.eq(method)]
            y = i * 2.55 + j
            valid = int(group.status.eq("completed").sum())
            missing = int(group.status.eq(MISSING).sum())
            failed = len(group) - valid - missing
            for left, width, color, hatch, text in (
                (0, valid, COLORS[method], "", "V"),
                (valid, failed, "white", "////", "F"),
                (valid + failed, missing, "white", "..", "—"),
            ):
                if not width:
                    continue
                ax.barh(
                    y,
                    width,
                    left=left,
                    height=0.76,
                    color=color,
                    hatch=hatch,
                    edgecolor="#333333",
                    linewidth=0.8,
                )
                ax.text(
                    left + width / 2,
                    y,
                    f"{text}: {width}",
                    ha="center",
                    va="center",
                    color="white" if text == "V" else "#222222",
                    fontsize=9,
                    bbox=None
                    if text == "V"
                    else dict(facecolor="white", edgecolor="none", pad=1),
                )
            ax.text(
                planned + 0.13, y, f"{valid}/{planned} valid", va="center", fontsize=9
            )
    positions = [i * 2.55 + j for i in range(len(names)) for j in range(2)]
    ax.set_yticks(
        positions, [f"{label(name)} · {method}" for name in names for method in METHODS]
    )
    ax.invert_yaxis()
    ax.set_xlim(0, planned + 1.1)
    ax.set_xticks(range(planned + 1))
    ax.set_xlabel("Number of planned repetitions")
    ax.grid(axis="x", color="#e5e7eb", linewidth=0.6)
    ax.set_axisbelow(True)
    fig.suptitle(f"Published outcomes · {info['label']}", fontsize=14)
    ax.legend(
        handles=[
            Patch(facecolor=COLORS[METHODS[0]], label="V: valid result (method color)"),
            Patch(
                facecolor="white",
                edgecolor="#333333",
                hatch="////",
                label="F: final outcome without valid result",
            ),
            Patch(
                facecolor="white",
                edgecolor="#333333",
                hatch="..",
                label="—: no published final outcome",
            ),
        ],
        loc="lower center",
        bbox_to_anchor=(0.47, 1.005),
        ncol=3,
        frameon=False,
        fontsize=8,
    )
    caption = "All planned repetitions stay in the denominator. Missing publications may be pending, interrupted, or not yet committed; they are not failures. A valid result does not certify specification compliance."
    save(fig, directory, "01_outcomes", formats, caption)
    return dict(
        name="01_outcomes",
        title="Published outcomes",
        caption=caption,
        alt="Counts of valid, unsuccessful final, and unpublished outcomes for each dataset and method. Exact counts appear inside the bars and in outcomes.csv.",
    )


def _axis_limits(ax, values, metric):
    if not values:
        return
    low, high = min(values), max(values)
    pad = max(
        (high - low) * 0.16,
        0.0001 if metric == "balanced_accuracy" else max(abs(high), 1) * 0.005,
    )
    low, high = max(0, low - pad), high + pad
    if metric == "balanced_accuracy":
        high = min(1, high)
    ax.set_ylim(low, high)
    ax.ticklabel_format(axis="y", style="plain", useOffset=False)


def distributions(frame, info, metric, directory, formats):
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.ticker import FuncFormatter

    names = dataset_order(
        name for name, meta in info["datasets"].items() if meta["metric"] == metric
    )
    if not names:
        return None
    columns = min(3, len(names))
    height = 3.7 * int(np.ceil(len(names) / columns)) + 0.9
    fig, axes = plt.subplots(
        int(np.ceil(len(names) / columns)),
        columns,
        figsize=(4.1 * columns, height),
        squeeze=False,
    )
    for ax, name in zip(axes.flat, names):
        part = frame[frame.dataset.eq(name)]
        all_values, ticks = [], []
        for x, method in enumerate(METHODS):
            group = part[part.method.eq(method)].sort_values("repetition")
            valid = group[group.status.eq("completed")]
            values = valid.score.to_numpy(dtype=float)
            all_values.extend(values.tolist())
            ticks.append(f"{method}\n{len(values)}/{len(group)} valid")
            if len(values) >= 2:
                ax.boxplot(
                    [values],
                    positions=[x],
                    widths=0.36,
                    showfliers=False,
                    whis=(0, 100),
                    patch_artist=True,
                    manage_ticks=False,
                    boxprops=dict(facecolor="white", edgecolor="#444444", linewidth=1),
                    medianprops=dict(color="#111111", linewidth=1.7),
                    whiskerprops=dict(color="#666666"),
                    capprops=dict(color="#666666"),
                )
            positions = [
                x
                + (info["repetitions"].index(rep) - (len(info["repetitions"]) - 1) / 2)
                * 0.065
                for rep in valid.repetition
            ]
            ax.scatter(
                positions,
                values,
                color=COLORS[method],
                marker=MARKERS[method],
                s=45,
                edgecolor="white",
                linewidth=0.65,
                zorder=4,
            )
            if len(values):
                ax.scatter(
                    x,
                    values.mean(),
                    marker="D",
                    s=46,
                    color="#111111",
                    edgecolor="white",
                    linewidth=0.7,
                    zorder=5,
                )
            else:
                ax.text(
                    x,
                    0.5,
                    "No valid\npublished result",
                    ha="center",
                    va="center",
                    transform=ax.get_xaxis_transform(),
                    fontsize=9,
                    color="#444444",
                )
        _axis_limits(ax, all_values, metric)
        if metric == "rmse" and all_values and max(all_values) >= 10000:
            ax.yaxis.set_major_formatter(
                FuncFormatter(lambda value, _: f"{value / 1000:g}k")
            )
        ax.set_xlim(-0.5, 1.5)
        ax.set_xticks([0, 1], ticks, fontsize=9)
        ax.set_title(label(name))
        ax.set_ylabel(
            "Balanced accuracy ↑" if metric == "balanced_accuracy" else "RMSE ↓"
        )
        ax.grid(axis="y", color="#e5e7eb", linewidth=0.6)
        ax.set_axisbelow(True)
    for ax in list(axes.flat)[len(names) :]:
        ax.set_visible(False)
    metric_label = "Classification" if metric == "balanced_accuracy" else "Regression"
    fig.suptitle(
        f"{metric_label}: observed score distributions · {info['label']}", fontsize=14
    )
    fig.legend(
        handles=[
            Line2D(
                [],
                [],
                color=COLORS[method],
                marker=MARKERS[method],
                linestyle="none",
                label=method,
            )
            for method in METHODS
        ]
        + [
            Line2D(
                [],
                [],
                marker="D",
                color="#111111",
                linestyle="none",
                label="Arithmetic mean",
            )
        ],
        loc="upper center",
        bbox_to_anchor=(0.5, 0.945),
        ncol=3,
        frameon=False,
        fontsize=9,
    )
    name = (
        "02_classification_distributions"
        if metric == "balanced_accuracy"
        else "03_regression_distributions"
    )
    caption = "Each colored point is one successful repetition; black diamonds are means. Boxes show median and interquartile range; whiskers show observed minimum–maximum. Absolute selection-CV scores; each dataset has its own labelled scale. Failed or unpublished runs are not zero scores. k = 1,000."
    save(fig, directory, name, formats, caption)
    return dict(
        name=name,
        title=f"{metric_label} distributions",
        caption=caption,
        alt=f"Per-dataset {metric_label.lower()} score distributions, with every successful repetition shown and valid/planned counts. Blue circles identify AGE-ML Original; dark orange squares identify MLZero. The tables provide all numerical values.",
    )


def paired(pairs, info, directory, formats):
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(
        1, 2, figsize=(12, 6.1), gridspec_kw={"width_ratios": [1.2, 1]}
    )
    for ax, metric in zip(axes, ("balanced_accuracy", "rmse")):
        names = dataset_order(
            name for name, meta in info["datasets"].items() if meta["metric"] == metric
        )
        for y, name in enumerate(names):
            group = pairs[pairs.dataset.eq(name)].sort_values("repetition")
            valid = group[group.both_valid & group.mlzero_advantage.notna()]
            values = valid.mlzero_advantage.to_numpy(dtype=float)
            offset = [
                (info["repetitions"].index(rep) - (len(info["repetitions"]) - 1) / 2)
                * 0.075
                for rep in valid.repetition
            ]
            ax.scatter(
                values,
                [y + value for value in offset],
                s=38,
                marker="s",
                color=COLORS[METHODS[1]],
                edgecolor="white",
                linewidth=0.5,
                zorder=3,
            )
            if len(values):
                ax.plot(
                    [min(values), max(values)],
                    [y, y],
                    color="#777777",
                    linewidth=1,
                    zorder=1,
                )
                ax.scatter(
                    values.mean(),
                    y,
                    marker="D",
                    s=46,
                    color="#111111",
                    edgecolor="white",
                    zorder=4,
                )
            ax.text(
                1.02,
                y,
                f"{len(valid)}/{len(group)} pairs",
                transform=ax.get_yaxis_transform(),
                va="center",
                fontsize=8,
                color="#444444",
            )
        ax.axvline(0, linestyle="--", color="#444444", linewidth=1)
        ax.set_yticks(range(len(names)), [label(name) for name in names])
        ax.set_ylim(len(names) - 0.5, -0.7)
        ax.set_xlabel(
            "MLZero advantage (percentage points)"
            if metric == "balanced_accuracy"
            else "MLZero advantage (% RMSE reduction)"
        )
        ax.set_title(
            "Classification" if metric == "balanced_accuracy" else "Regression"
        )
        ax.grid(axis="x", color="#e5e7eb", linewidth=0.6)
        ax.set_axisbelow(True)
        ax.margins(x=0.18)
    fig.suptitle(f"Matched repetition differences · {info['label']}", fontsize=14)
    caption = "Positive values favor MLZero; negative values favor AGE-ML Original. Squares are matched repetition indices with two valid scores; diamonds are means and thin lines span observed differences. Missing or unsuccessful outcomes are excluded here, not from the outcome counts. Matching indices does not establish statistical independence."
    save(fig, directory, "04_paired_differences", formats, caption)
    return dict(
        name="04_paired_differences",
        title="Matched repetition differences",
        caption=caption,
        alt="Per-dataset differences using only repetition indices where both methods returned a valid score. Zero means equal performance; positive values favor MLZero. Classification uses percentage points; regression uses percentage RMSE reductions. Pair counts are printed beside each row.",
    )


def make_figures(frame, pairs, info, directory, formats):
    import matplotlib

    matplotlib.use("Agg")
    with plot_style():
        figures = [outcomes(frame, info, directory, formats)]
        for metric in ("balanced_accuracy", "rmse"):
            figure = distributions(frame, info, metric, directory, formats)
            if figure:
                figures.append(figure)
        figures.append(paired(pairs, info, directory, formats))
    return figures
