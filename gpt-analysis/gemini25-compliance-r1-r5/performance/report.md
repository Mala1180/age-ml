# gemini25-flash-hamlet-cv-w8-storage — repetitions [1, 2, 3, 4, 5]

Recorded outcomes: 270/270; valid candidates: 257; failures: 13; missing: 0.

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
| baseline | 45 | 45 | 45 | 0 | 0 | 1 | 1 | 27.4853 | 6.22681 | 2.60177e+07 |
| specification-poor | 45 | 45 | 44 | 1 | 0 | 0.977778 | 1 | 25.3514 | 6.27658 | 2.85048e+07 |
| specification-specific | 45 | 45 | 45 | 0 | 0 | 1 | 1 | 17.4181 | 5.4643 | 1.90761e+07 |
| validation-no-semantic-retry | 45 | 45 | 45 | 0 | 0 | 1 | 1 | 24.6219 | 2.82116 | 1.57213e+07 |
| validation-no-execution-retry | 45 | 45 | 39 | 6 | 0 | 0.866667 | 1 | 16.9583 | 3.07706 | 1.24859e+07 |
| no-csp | 45 | 45 | 39 | 6 | 0 | 0.866667 | 1 | 7.44139 | 0.535983 | 4.51201e+06 |

## Unsuccessful executions

| condition | repetition | dataset | status |
| --- | --- | --- | --- |
| specification-poor | 5 | mnist_784 | no_valid_candidate |
| validation-no-execution-retry | 1 | california_housing | no_valid_candidate |
| validation-no-execution-retry | 2 | california_housing | no_valid_candidate |
| validation-no-execution-retry | 4 | mnist_784 | no_valid_candidate |
| validation-no-execution-retry | 4 | california_housing | no_valid_candidate |
| validation-no-execution-retry | 5 | mnist_784 | no_valid_candidate |
| validation-no-execution-retry | 5 | california_housing | no_valid_candidate |
| no-csp | 1 | adult | no_valid_candidate |
| no-csp | 1 | ames_housing | no_valid_candidate |
| no-csp | 4 | mnist_784 | no_valid_candidate |
| no-csp | 4 | california_housing | no_valid_candidate |
| no-csp | 4 | ames_housing | no_valid_candidate |
| no-csp | 5 | california_housing | no_valid_candidate |

## Scores by dataset

| problem | dataset | baseline | specification-poor | specification-specific | validation-no-semantic-retry | validation-no-execution-retry | no-csp |
| --- | --- | --- | --- | --- | --- | --- | --- |
| classification | adult | 0.819542 | 0.825303 | 0.818783 | 0.821569 | 0.820776 | 0.814272 |
| classification | har | 0.95667 | 0.911705 | 0.951624 | 0.95667 | 0.933894 | 0.934259 |
| classification | madelon | 0.875 | 0.866538 | 0.810385 | 0.875 | 0.835077 | 0.853077 |
| classification | mnist_784 | 0.973112 | 0.831956 | 0.970074 | 0.97244 | 0.969448 | 0.956538 |
| classification | texture | 0.996945 | 0.988182 | 0.997455 | 0.9972 | 0.992727 | 0.964364 |
| classification | wilt | 0.973103 | 0.950643 | 0.974589 | 0.973103 | 0.973103 | 0.864821 |
| regression | ames_housing | 33040.9 | 31263.6 | 30013.1 | 29954.3 | 37037.7 | 196844 |
| regression | auto_mpg | 2.61475 | 2.63505 | 2.71141 | 2.61475 | 3.06617 | 2.79971 |
| regression | california_housing | 70644.1 | 69554.8 | 69405.2 | 70224 | 76773.8 | 74562.8 |

Figures and CSV/LaTeX tables are in figures/ and tables/. Figures omit no failure from the outcome counts; a failed score cell is not zero.
