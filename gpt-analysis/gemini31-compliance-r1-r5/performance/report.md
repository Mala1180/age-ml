# gemini31-flash-lite-hamlet-cv-w8-storage — repetitions [1, 2, 3, 4, 5]

Recorded outcomes: 270/270; valid candidates: 259; failures: 11; missing: 0.

Score role: **selection_cv_not_independent_test**. The CSV Baseline field is a protocol/reference label, never a HAMLET numeric score.

This is descriptive analysis. No p-values are computed. 95% Student-t intervals are calculated across successful repetitions (n >= 2), never across CV folds. They assume independent representative repetitions and describe technical variability here, not uncertainty on generalization or different data splits. Compact annotations use mean ± the original symmetric t margin. CSVs retain both original endpoints and endpoints intersected with the known metric range ([0,1] for BA and [0,infinity) for RMSE). The ± notation is a 95% margin, not a standard deviation; it may extend beyond the metric bounds. Zero-width intervals indicate identical observed values, not guaranteed reproducibility. The campaign uses the recorded seeds; repetitions with the same seed are technical repetitions, not different seeds.

Performance means/std use successful observations only. Missing outcomes are distinct from failures. Paired deltas require both conditions to succeed; exclusions remain in paired_deltas.csv. Regression RMSE is never averaged across datasets with different target scales.

Recorded worker settings: [8.0].

Failure status alone does not establish whether the cause was generated code, timeout or infrastructure. Detailed evidence must be inspected before attributing causes.

## Compliance policy

When --audit is provided, figures/ contains all selected winners; figures/without_detected_violations/ contains only winners with resolved applicable checks and no detected violations. Undetermined winners are excluded too. No replacement winner is selected. This conditional subset can introduce selection bias; excluded rows and denominators are exported. Resources always retain all recorded outcomes. Strict recipe/task/parameter checks include undeclared categorical adapters; the audit separately reports an adapters-allowed sensitivity. Without an audit all successful winners have undetermined audit status.

## Paper tables

paper_table_1_datasets uses current recorded metadata. paper_dataset_differences.csv lists discrepancies from the supplied paper; historical values are never substituted for observed values. paper_results_<condition> mirrors Tables 2/3 and adds intervals and valid/expected counts. For the full AGE-ML baseline condition, paper_table_2_results or paper_table_3_results is also generated according to the model. Score means use successful runs; resource means include all recorded outcomes, including unsuccessful ones. Numeric statistics retain resource-specific denominators. Actual P. counts returned completed execution-agent states, not every attempted pipeline or successful fit.

Historical Reference is transcribed from Tables 2/3: HAMLET for classification and Kaggle notebooks for regression. It is separate from the AGE-ML baseline condition. Protocol and dataset comparability must be checked before making claims. Table 4 is a static transcription of the paper's qualitative comparison, not a recomputed experiment or an independently verified current assessment. Reference provenance is saved in tables/paper_reference_used.json.

## Exploration counts

Pipelines Found counts enumerated structures; Pipeline Budget is the configured upper bound. Actual Pipelines counts completed execution-agent states with a tracking ID, not all started structures or fitted instances. Timed-out/failed agents can still have candidate records. In no-csp the planner proposes one structure. Candidate records require validation_candidates.csv with matching provenance. Their counts include only recorded evidence; killed workers can leave unrecorded work. Missing evidence is N/A, not zero. A candidate is a code/hyperparameter/execution-attempt combination; ten CV folds are not ten candidate instances. Local pipeline IDs are not comparable across conditions. See exploration_counts.csv and pipeline_instances.csv.

## Outcomes and recorded resources

| condition | expected | recorded | completed | failed | missing | success_rate_recorded | recording_coverage | actual_time_hours | estimated_cost_usd | total_tokens |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 45 | 45 | 45 | 0 | 0 | 1 | 1 | 25.7042 | 11.5346 | 7.82017e+07 |
| specification-poor | 45 | 45 | 44 | 1 | 0 | 0.977778 | 1 | 25.5281 | 12.2305 | 9.02354e+07 |
| specification-specific | 45 | 45 | 45 | 0 | 0 | 1 | 1 | 14.54 | 8.60174 | 3.67019e+07 |
| validation-no-semantic-retry | 45 | 45 | 45 | 0 | 0 | 1 | 1 | 24.6789 | 6.9803 | 7.19828e+07 |
| validation-no-execution-retry | 45 | 45 | 35 | 10 | 0 | 0.777778 | 1 | 11.1514 | 2.74793 | 1.48972e+07 |
| no-csp | 45 | 45 | 45 | 0 | 0 | 1 | 1 | 12.0375 | 0.954301 | 9.76713e+06 |

## Unsuccessful executions

| condition | repetition | dataset | status |
| --- | --- | --- | --- |
| specification-poor | 5 | mnist_784 | no_valid_candidate |
| validation-no-execution-retry | 1 | madelon | no_valid_candidate |
| validation-no-execution-retry | 1 | mnist_784 | no_valid_candidate |
| validation-no-execution-retry | 2 | madelon | no_valid_candidate |
| validation-no-execution-retry | 2 | mnist_784 | no_valid_candidate |
| validation-no-execution-retry | 3 | madelon | no_valid_candidate |
| validation-no-execution-retry | 3 | mnist_784 | no_valid_candidate |
| validation-no-execution-retry | 4 | madelon | no_valid_candidate |
| validation-no-execution-retry | 4 | mnist_784 | no_valid_candidate |
| validation-no-execution-retry | 5 | madelon | no_valid_candidate |
| validation-no-execution-retry | 5 | mnist_784 | no_valid_candidate |

## Scores by dataset

| problem | dataset | baseline | specification-poor | specification-specific | validation-no-semantic-retry | validation-no-execution-retry | no-csp |
| --- | --- | --- | --- | --- | --- | --- | --- |
| classification | adult | 0.821761 | 0.814481 | 0.823079 | 0.822424 | 0.745435 | 0.825495 |
| classification | har | 0.95667 | 0.932699 | 0.951624 | 0.95667 | 0.933894 | 0.934259 |
| classification | madelon | 0.875 | 0.866538 | 0.810385 | 0.875 | — | 0.62 |
| classification | mnist_784 | 0.97244 | 0.70036 | 0.970074 | 0.96988 | — | 0.950564 |
| classification | texture | 0.997455 | 0.988182 | 0.997455 | 0.997455 | 0.997455 | 0.945273 |
| classification | wilt | 0.973103 | 0.950643 | 0.974589 | 0.973103 | 0.970202 | 0.802097 |
| regression | ames_housing | 33819.7 | 29706.1 | 31200.2 | 33819.7 | 36356 | 31998.7 |
| regression | auto_mpg | 2.61475 | 2.63505 | 2.71141 | 2.61475 | 3.36375 | 2.77534 |
| regression | california_housing | 70224 | 69834.5 | 68235.7 | 70224 | 80684.6 | 68282.3 |

Figures and CSV/LaTeX tables are in figures/ and tables/. Figures omit no failure from the outcome counts; a failed score cell is not zero.
