# AGE-ML / MLZero comparison

Run this analysis locally in the AGE-ML repository:

```bash
poetry run python scripts/competitor_analysis.py
```

The defaults read committed results from:

| Repository | Branch | Data |
| --- | --- | --- |
| `Mala1180/age-ml` | `results/gemini-run1` | Original/baseline CSVs and campaign manifests, Gemini 2.5 and 3.1 |
| `gciatto/experiments-ageml-mlzero-benchmark` | `results/mlzero-gemini` | Per-run report CSVs, configurations and optional full-audit summary CSVs |

The command does not switch either working checkout or execute model code. It
uses a dedicated bare Git cache under `reports/.competitor-cache/`. The reports
are written under `reports/competitor-comparison/`; both directories are already
ignored by Git. Results therefore stay on their results branches, and the scripts
can be committed on `main` without copying experimental outputs there.

An online invocation refreshes the two branch tips once and reads fixed commit
IDs for the entire report. `sources.json` records those commits, every consumed
file hash, the analysis-code hashes and the selected repetitions. The first
fetch can take longer; Git requests partial object transfers where supported.

## Outputs

Open `reports/competitor-comparison/index.html` in a browser. It is self-contained
apart from the relative figure files, works offline, and includes text
alternatives and semantic tables. For each backend, four figures are exported in
PNG, PDF and editable SVG:

1. **Published outcomes:** valid results, unsuccessful final outcomes and
   unpublished results, with all planned repetitions in the denominator.
2. **Classification distributions:** every successful repetition, grouped by
   dataset and method; balanced accuracy is shown on an absolute, labelled scale.
3. **Regression distributions:** the same representation for RMSE. Each dataset
   has its own scale; the values are not normalized or averaged across datasets.
4. **Matched repetition differences:** common successful repetition indices.
   Positive values favor MLZero. Classification uses percentage points;
   regression uses `100 * (AGE_RMSE - MLZero_RMSE) / AGE_RMSE`. A zero AGE RMSE
   makes that relative percentage undefined; it is never replaced with zero.

Colored points are individual repetitions, black diamonds are arithmetic means,
boxes show median and interquartile range, and whiskers span observed min–max.
With at most five repetitions, no kernel-density or violin curves are invented.
The blue circles and dark-orange squares remain distinguishable in grayscale.
Outcome bars also use direct labels, counts and distinct hatches. The palette
has at least 4.5:1 contrast against white; colors, contrast values and limitations
are recorded in `sources.json`. Static PDFs are not certified tagged accessible
documents; the HTML and CSV files provide the accessible numerical alternative.

The `tables/` directory contains:

| File | Contents |
| --- | --- |
| `per_repetition.csv` | Every planned dataset/method/repetition, including unsuccessful and unpublished outcomes |
| `outcomes.csv` | Backend/method counts: planned, recorded, valid, failed, unpublished |
| `metric_summary.csv` | Mean, SD, median, quartiles, min–max and descriptive 95% intervals |
| `metric_summary_display.csv` | Formatted full distribution statistics and counts |
| `<backend>_comparison.csv`, `.md`, `.tex` | Compact side-by-side mean ± CI and valid/planned counts |
| `<backend>_metrics.md`, `.tex` | Detailed distribution statistics, failures and missing publications |
| `paired_repetitions.csv` | Each matched index and the signed performance difference |
| `paired_summary.csv` | Pair counts, means on common successes, descriptive advantage intervals and win/tie counts |
| `failure_reasons.csv` | Final failure counts, with terminal phases when the committed audit supplies them |

LaTeX tables use `booktabs`; wide tables can be wrapped in the paper's usual
`resizebox` or placed in a two-column-spanning table.

## Refresh, offline use and subsets

Refresh with the original command after committing/pushing new MLZero summaries.
No script change is needed when Gemini 3.1 results become available.

```bash
# Reproduce the last fetched commits without network access.
poetry run python scripts/competitor_analysis.py --offline

# Only one backend or an explicit repetition subset.
poetry run python scripts/competitor_analysis.py \
  --backends gemini25 --repetitions 1,2,3 \
  --outdir reports/competitor-comparison/gemini25-r1-r3

# Read committed branches from existing local clones instead of the public remotes.
poetry run python scripts/competitor_analysis.py \
  --age-repository . \
  --mlzero-repository ../experiments-ageml-mlzero-benchmark
```

Local clones must contain the configured named branches. Uncommitted working
files and the currently checked-out branch are not used. `--age-ref` and
`--mlzero-ref` can select an explicit branch, full ref or commit ID; use separate
output directories for alternative analyses. A first offline run has no cached
inputs and fails clearly. Missing blobs in an offline cache cannot trigger a
network fetch.

The only central configuration is `resources/competitor-analysis.json`. It maps
backend labels to the existing campaign and summary paths. There are no embedded
experimental scores or credentials in the analysis scripts.

## Interpretation and safeguards

- The comparison is **AGE-ML Original versus MLZero**, within the same LLM backend.
  Ablation conditions are not pooled into the original method's distribution.
- These are **selected mean ten-fold CV scores**, not independent test results.
  Data-source hashes, fold identities, model, seed 42, temperature zero and
  one-hour search budgets must match. A mismatch stops the report.
- Successful means are conditional on returning a valid result. Common-success
  pair means can differ from all-success means; both are exported explicitly.
- A `no_artifact` outcome is a final unsuccessful search. A missing summary row
  means **not published**, not failure and not proof that a job is running.
  The denominator is always the requested planned repetitions, never only the
  outcomes that happened to be recorded.
- 95% Student-t intervals use successful **repetitions**, not the ten CV folds.
  They are descriptive under an independence assumption not established by these
  shared-seed, shared-fold runs. They are not generalization guarantees. With one
  value the interval is unavailable; with no values the mean is unavailable.
  Intervals are not clipped to hide uncertainty. No p-values or claims of
  statistical significance are generated.
- Equal resource-time usage is not established by a common one-hour limit:
  MLZero CPU allocation and AGE-ML worker counts are different quantities.
- Valid results do not certify specification compliance. This report uses all
  successful outcomes; it does not invent comparable post-hoc compliance labels.
- Optional full-audit tables are cross-checked against the current summary and
  AGE-ML scores before their diagnostic annotations are reused. Stale or
  inconsistent audit scores stop the report.

MLZero must publish `report/mlzero_runs.csv` in each canonical campaign directory
on `results/mlzero-gemini`. Its existing HAMLET-CV `report` command produces that
table. Existing full-audit CSVs are optional; raw generated models, predictions,
data matrices and API keys are not needed.
