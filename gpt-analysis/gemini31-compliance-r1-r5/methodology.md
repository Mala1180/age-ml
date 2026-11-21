# Post hoc compliance audit

The archive is inspected without executing generated code, importing generated modules, or loading serialized models. Every registered candidate code hash and ordered requested recipe is checked against its candidate_key using the recorded fit seed. Effective specifications are checked against the frozen campaign hashes (generated specification hashes use the campaign JSON-string serialization).

## Populations

An instance is one recorded fit/attempt with its actual hyperparameters. A version is deduplicated within (condition, dataset, repetition, run identity, planned pipeline ID, code hash). Version flags are unions over observed instances, not claims that every parameter instance violates. Eligible fits and selected winners are reported separately. A winner must match run ID, candidate key, code hash and summary score. Additional artifact/trace versions are audited for structure only and excluded from primary instance rates. Their recipe origins are explicit: a candidate-key-verified recipe, an unambiguous retained state, or a machine-written numbered pipeline header paired with the frozen component grid. Recipes outside the ledger cannot be candidate-key verified. Unattributable sources remain in coverage inventories.

## Contract and interpretation

The strict policy checks missing/substituted/undeclared reachable components, declared ordering, requested parameter binding, and task-incompatible planned estimators. A wrong_task_recipe is a planning/specification issue, not a code deviation from that same recipe. Every condition uses its own effective specification. No-CSP is checked against its recovered proposed recipe, not against a hypothetical CSP choice. Selected parameters with colliding flat names are checked against each component's frozen grid. Categorical imputer strategy differences are review notes. Encoders and undeclared categorical adapters count under the strict policy; an adapters-allowed sensitivity is reported separately. These alternatives must not be mixed in a single comparison.

A conservative AST interpreter resolves only supported expressions and reachable returned components. Syntax errors, unsupported factories and unknown parameters are not labeled conforming. A confirmed detectable violation takes precedence over otherwise unknown parameter checks. No-detected-violation means only that the applicable implemented checks resolved and found no violation; it is not proof of full behavioral or constraint compliance. Logical requirements outside these checks, leakage, numerical equivalence, training behavior and runtime mutations are not certified. Column-scope/data-dependent checks are limited; review flags are retained. Defaults used for compared parameters are explicit in the code.

## Graphs and statistics

All-winner performance and filtered-winner performance are both generated. Filtered plots exclude confirmed violations and undetermined winners, retain expected denominators, and never select a replacement winner. This conditional subset may introduce selection bias. Resources include all recorded outcomes. Failure counts are distinct from semantic violations; missing/invalid code does not establish a structural violation. Static code versions and instances are clustered within runs and are not independent statistical samples. Confidence margins across technical repetitions are descriptive, not guarantees of reproducibility or confidence on generalization. Judge precision/recall and causal filtering effectiveness cannot be estimated from the retained nonrepresentative trace sample.

## Reproduction

`python scripts/compliance_audit.py --input evidence.zip --outdir reports/compliance`

The same command regenerates the CSVs, audit figures and campaign figures/tables. Dependencies: numpy, pandas, scipy, matplotlib, PyYAML. See coverage.json for input identity and limitations; all CSV fields are English.
