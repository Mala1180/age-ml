"""Offline reporting from committed AGE-ML and MLZero summary data only.

Run from the AGE-ML checkout: python scripts/competitor_analysis.py
No experiment runtime, model code, API key or container is required.
"""

import argparse
import html
import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def compact(value):
    return f"{value:.6g}" if math.isfinite(value) else "—"


def metric_table(summary):
    rows = []
    for row in summary.itertuples():
        interval = (
            f"{compact(row.mean)} ± {compact(row.ci95_half_width)}"
            if math.isfinite(row.ci95_half_width)
            else f"{compact(row.mean)} (CI unavailable)"
            if row.n_valid
            else "—"
        )
        rows.append(
            {
                "Backend": row.backend,
                "Dataset": row.dataset,
                "Method": row.method,
                "Metric": row.metric,
                "Valid / planned": f"{row.n_valid}/{row.n_planned}",
                "Final failures": row.n_failed,
                "Not published": row.n_not_published,
                "Mean ± 95% CI": interval,
                "Median [Q1, Q3]": f"{compact(row.median)} [{compact(row.q1)}, {compact(row.q3)}]"
                if row.n_valid
                else "—",
                "Min–max": f"{compact(row.min)}–{compact(row.max)}"
                if row.n_valid
                else "—",
            }
        )
    import pandas as pd

    return pd.DataFrame(rows)


def comparison_table(display):
    import pandas as pd

    from scripts.competitor_data import METHODS, dataset_order, label

    rows = []
    for dataset in dataset_order(display.Dataset.unique()):
        part = display[display.Dataset.eq(dataset)]
        age = part[part.Method.eq(METHODS[0])].iloc[0]
        ml = part[part.Method.eq(METHODS[1])].iloc[0]
        rows.append(
            {
                "Dataset": label(dataset),
                "Metric": age.Metric,
                "AGE-ML Original: mean ± CI": age["Mean ± 95% CI"],
                "AGE-ML valid": age["Valid / planned"],
                "MLZero: mean ± CI": ml["Mean ± 95% CI"],
                "MLZero valid": ml["Valid / planned"],
            }
        )
    return pd.DataFrame(rows)


def markdown_table(table):
    columns = list(table.columns)
    rows = [columns, ["---"] * len(columns)]
    rows.extend(table.astype(str).values.tolist())
    return "\n".join(
        "| "
        + " | ".join(str(v).replace("|", "\\|").replace("\n", " ") for v in row)
        + " |"
        for row in rows
    )


def latex_table(table):
    replacements = {
        "\\": r"\textbackslash{}",
        "_": r"\_",
        "&": r"\&",
        "%": r"\%",
        "#": r"\#",
        "$": r"\$",
        "{": r"\{",
        "}": r"\}",
        "±": r"$\pm$",
        "—": "--",
        "–": "--",
    }

    def escape(value):
        return "".join(replacements.get(char, char) for char in str(value))

    rows = [list(table.columns), *table.astype(str).values.tolist()]
    lines = [r"\begin{tabular}{" + "l" * len(table.columns) + "}", r"\toprule"]
    for i, row in enumerate(rows):
        lines.append(" & ".join(escape(value) for value in row) + r" \\")
        if i == 0:
            lines.append(r"\midrule")
    return "\n".join([*lines, r"\bottomrule", r"\end{tabular}", ""])


def write_report(out, frame, summary, pairs, pair_summary, infos, sources, formats):
    from scripts.competitor_figures import accessibility_notes, make_figures

    out.mkdir(parents=True, exist_ok=True)
    tables = out / "tables"
    tables.mkdir(exist_ok=True)
    for name, table in (
        ("per_repetition", frame),
        ("metric_summary", summary),
        ("paired_repetitions", pairs),
        ("paired_summary", pair_summary),
    ):
        table.to_csv(tables / f"{name}.csv", index=False)
    overview = (
        summary.groupby(["backend", "method"], sort=False)[
            ["n_planned", "n_recorded", "n_valid", "n_failed", "n_not_published"]
        ]
        .sum()
        .reset_index()
    )
    overview.to_csv(tables / "outcomes.csv", index=False)
    failures = frame[~frame.status.isin(["completed", "not_published"])].copy()
    failures["terminal_phase"] = failures.terminal_phase.replace(
        "", "Not available in committed summary"
    )
    failures.groupby(
        ["backend", "method", "dataset", "status", "terminal_phase"], dropna=False
    ).size().rename("n_runs").reset_index().to_csv(
        tables / "failure_reasons.csv", index=False
    )
    presentation = metric_table(summary)
    presentation.to_csv(tables / "metric_summary_display.csv", index=False)
    notes = [
        "Scores are selected mean ten-fold CV scores, not independent test scores.",
        "Every point is one successful repetition, not a CV fold; methods are compared within the same LLM backend.",
        "Failed and unpublished outcomes are retained in denominators and never replaced by zero scores.",
        "Distribution means are conditional on success. Paired summaries use only common successful repetition indices; their means can differ from the all-success means.",
        "95% Student-t intervals describe variability across observed successful repetitions under an independence assumption that these shared-seed, shared-fold runs do not establish. They are not generalization guarantees. No p-values or claims of significance are produced.",
        "Confidence intervals are not clipped to the metric domain. A broad interval is reported transparently rather than hidden by clipping.",
        "Input hashes, prescribed-fold identities, model, seed, temperature, score role and one-hour search budgets are checked. Equal resource-time usage is not established: CPU limits and AGE-ML worker counts are different quantities.",
        "Successful saved results are included without post-hoc specification-compliance filtering. Artifact validity does not certify structural or hyperparameter compliance.",
        "Only committed summary CSVs, campaign manifests and configuration files are read. Generated model code, data matrices, predictions, and LLM APIs are not executed or accessed.",
    ]
    metadata = dict(
        created_at=datetime.now(UTC).isoformat(),
        sources=sources,
        campaigns=infos,
        interpretation=notes,
        accessibility=accessibility_notes(),
    )
    (out / "sources.json").write_text(
        json.dumps(metadata, indent=2, allow_nan=False) + "\n"
    )
    md = [
        "# AGE-ML / MLZero comparison",
        "",
        markdown_table(overview),
        "",
        "## Interpretation",
        "",
    ]
    md += [f"- {note}" for note in notes]
    body = [
        "<h1>AGE-ML / MLZero comparison</h1>",
        "<p>Selected ten-fold CV scores. Exact values and all outcomes are available in the accompanying CSV tables.</p>",
        '<p><a href="sources.json">Input commits, hashes and interpretation</a> · <a href="tables/per_repetition.csv">All repetitions (CSV)</a> · <a href="tables/paired_summary.csv">Matched results (CSV)</a></p>',
        '<div class="table-wrap">' + overview.to_html(index=False, border=0) + "</div>",
        "<h2>How to interpret this report</h2><ul>"
        + "".join(f"<li>{html.escape(note)}</li>" for note in notes)
        + "</ul>",
    ]
    alt_text = []
    for backend, info in infos.items():
        subset = frame[frame.backend.eq(backend)]
        matched = pairs[pairs.backend.eq(backend)]
        backend_dir = out / "figures" / backend
        figures = make_figures(subset, matched, info, backend_dir, formats)
        display = presentation[presentation.Backend.eq(backend)].drop(columns="Backend")
        comparison = comparison_table(display)
        comparison.to_csv(tables / f"{backend}_comparison.csv", index=False)
        (tables / f"{backend}_comparison.md").write_text(
            markdown_table(comparison) + "\n"
        )
        (tables / f"{backend}_comparison.tex").write_text(latex_table(comparison))
        (tables / f"{backend}_metrics.md").write_text(markdown_table(display) + "\n")
        (tables / f"{backend}_metrics.tex").write_text(latex_table(display))
        md += ["", f"## {info['label']}", "", markdown_table(comparison), ""]
        body += [
            f"<h2>{html.escape(info['label'])}</h2>",
            '<div class="table-wrap">'
            + comparison.to_html(index=False, border=0, escape=True)
            + "</div>",
        ]
        if not info["mlzero_summary_published"]:
            warning = "No MLZero summary is published for this backend at the recorded commit. Its planned outcomes are marked not published; this does not establish whether a campaign is currently running."
            md += [warning, ""]
            body += [f'<p class="notice">{warning}</p>']
        for figure in figures:
            stem = f"figures/{backend}/{figure['name']}"
            preview_format = (
                "png" if "png" in formats else "svg" if "svg" in formats else None
            )
            alt_text += [
                f"## {backend}/{figure['name']}",
                "",
                figure["alt"],
                "",
                figure["caption"],
                "",
            ]
            md += [f"### {figure['title']}", "", figure["caption"], ""]
            if preview_format:
                md += [f"![{figure['alt']}]({stem}.{preview_format})", ""]
                body += [
                    f'<figure><img src="{stem}.{preview_format}" alt="{html.escape(figure["alt"], quote=True)}"><figcaption>{html.escape(figure["caption"])}</figcaption></figure>'
                ]
            else:
                body += [
                    f'<p><a href="{stem}.pdf">{html.escape(figure["title"])} (PDF)</a></p>'
                ]
        body += [
            '<details><summary>Full distribution statistics and outcome counts</summary><div class="table-wrap">'
            + display.to_html(index=False, border=0, escape=True)
            + "</div></details>"
        ]
    (out / "report.md").write_text("\n".join(md) + "\n")
    (out / "alt_text.md").write_text("\n".join(alt_text))
    css = "body{font-family:system-ui,sans-serif;color:#222;background:white;max-width:1200px;margin:2rem auto;padding:0 1rem;line-height:1.55}a{color:#234b83}img{width:100%;height:auto}figure{margin:2rem 0}figcaption{font-size:.95rem}table{border-collapse:collapse;width:100%;font-size:.9rem}td,th{padding:.5rem;border-bottom:1px solid #888;text-align:left}th{background:#eee}.table-wrap{overflow:auto}.notice{border:2px solid #555;padding:1rem}"
    document = (
        '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>AGE-ML / MLZero comparison</title><style>'
        + css
        + "</style><main>"
        + "\n".join(body)
        + "</main></html>"
    )
    (out / "index.html").write_text(document.replace("<th>", '<th scope="col">'))
    return overview


def main(argv=None):
    # Also support `python scripts/competitor_analysis.py` without installing AGE-ML.
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.competitor_data import (
        GitSource,
        digest,
        paired_results,
        parse_repetitions,
        read_backend,
        summarize,
        summarize_pairs,
    )

    import pandas as pd

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=ROOT / "resources/competitor-analysis.json"
    )
    parser.add_argument("--age-repository")
    parser.add_argument("--mlzero-repository")
    parser.add_argument("--age-ref")
    parser.add_argument("--mlzero-ref")
    parser.add_argument("--backends", default="gemini25,gemini31")
    parser.add_argument("--repetitions", default="1,2,3,4,5")
    parser.add_argument(
        "--outdir", type=Path, default=ROOT / "reports/competitor-comparison"
    )
    parser.add_argument(
        "--cache-dir", type=Path, default=ROOT / "reports/.competitor-cache"
    )
    parser.add_argument("--formats", default="png,pdf,svg")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Use the last fetched source commits; perform no network access",
    )
    args = parser.parse_args(argv)
    cfg = json.loads(args.config.read_text())
    selected = args.backends.split(",")
    if len(set(selected)) != len(selected) or not set(selected) <= set(cfg["backends"]):
        parser.error("Choose distinct configured backends, e.g. gemini25,gemini31")
    formats = args.formats.split(",")
    if (
        not formats
        or len(set(formats)) != len(formats)
        or not set(formats) <= {"png", "pdf", "svg"}
    ):
        parser.error("Formats must be a distinct subset of png,pdf,svg")
    repetitions = parse_repetitions(args.repetitions)
    sources = {}
    for name in ("age", "mlzero"):
        repository = getattr(args, f"{name}_repository") or cfg[f"{name}_repository"]
        ref = getattr(args, f"{name}_ref") or cfg[f"{name}_ref"]
        print(f"Reading {name}: {repository} at {ref}", flush=True)
        cache = args.cache_dir / f"{name}-{digest(str(repository).encode())[:12]}"
        sources[name] = GitSource(repository, ref, cache, args.offline)
    frames, infos = [], {}
    for backend in selected:
        frame, info = read_backend(
            sources["age"],
            sources["mlzero"],
            backend,
            cfg["backends"][backend],
            repetitions,
        )
        frames.append(frame)
        infos[backend] = info
    frame = pd.concat(frames, ignore_index=True)
    pairs = paired_results(frame)
    provenance = {name: source.provenance() for name, source in sources.items()}
    provenance["analysis"] = dict(
        config_sha256=digest(args.config.read_bytes()),
        code_sha256={
            path.name: digest(path.read_bytes())
            for path in (
                Path(__file__),
                ROOT / "scripts/competitor_data.py",
                ROOT / "scripts/competitor_figures.py",
            )
        },
    )
    overview = write_report(
        args.outdir,
        frame,
        summarize(frame),
        pairs,
        summarize_pairs(pairs),
        infos,
        provenance,
        formats,
    )
    print(overview.to_string(index=False))
    print(f"Report: {(args.outdir / 'index.html').resolve()}")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, FileNotFoundError, KeyError) as error:
        raise SystemExit(f"Comparison aborted: {error}") from error
