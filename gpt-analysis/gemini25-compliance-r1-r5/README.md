# Gemini campaign: post hoc compliance analysis

| condition | label | expected_outcomes | selected_winners | strict_winner_violations | adapters_allowed_winner_violations | unsuccessful_outcomes |
| --- | --- | --- | --- | --- | --- | --- |
| baseline | Original | 45 | 45 | 14 | 8 | 0 |
| specification-poor | Broad | 45 | 44 | 10 | 0 | 1 |
| specification-specific | Tight | 45 | 45 | 13 | 1 | 0 |
| validation-no-semantic-retry | No semantic retry | 45 | 45 | 17 | 7 | 0 |
| validation-no-execution-retry | No execution retry | 45 | 39 | 10 | 6 | 6 |
| no-csp | No CSP | 45 | 39 | 9 | 6 | 6 |

Strict counts refer to selected implementations, not the number of individual findings. One winner can have multiple findings. The adapters-allowed column permits categorical representation adapters only; missing/substituted models, task mismatches, global extra components and parameter mismatches remain violations.

Original: 14/45 strict winner violations; 8/45 with categorical adapters allowed. Structural violation rate among resolved registered code versions: 19.85% (488/2459).

No semantic retry: 17/45 strict winner violations; 7/45 with categorical adapters allowed. Structural violation rate among resolved registered code versions: 27.76% (725/2612).

These are descriptive differences in the registered population, not evidence of statistical significance or a causal judge effect. Versions and fits are clustered; technical repetitions share recorded seeds. A smaller violation rate among successful candidates does not estimate precision/recall of the judge.

The strict and adapters-allowed policies answer different questions; this choice materially affects interpretation and should be stated in the paper. A wrong_task_recipe finding refers to planning a classifier for a regression task (or the reverse), not to code deviating from that same recipe.

Filtered figures drop original winners with confirmed violations or undetermined checks; they do not choose an alternative candidate. Some dataset/configuration cells may have no included result. This does not mean their score is zero. Costs include all outcomes.

## Files

tables/run_audit.csv: all dataset outcomes and winner verdicts. tables/individual_findings.csv: individual violations with source locations. tables/instance_audit.csv: registered parameter instances. tables/implementation_audit.csv: versions deduplicated within pipeline/run. Additional versions and unlinked sources are separate. coverage.json and methodology.md define coverage and limitations.

performance/figures/: all winners and outcome/resource figures. performance/figures/without_detected_violations/: filtered performance figures. performance/tables/: CSV, Markdown and LaTeX tables, including paper layouts and filtered variants. audit_figures/: population violation rates and per-run distributions.

## Reproduce

Run `python scripts/compliance_audit.py --input evidence.zip --outdir reports/compliance` after applying the companion code ZIP. To regenerate plots from repository results, run `python scripts/campaign_analysis.py report --campaign PATH --repetitions all --audit reports/compliance/tables/run_audit.csv --outdir reports/performance`. The evidence ZIP remains the source for reproduction; large extracted evidence files are omitted from the downloadable report package.
