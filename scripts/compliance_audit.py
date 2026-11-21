"""Audit an exported AGE-ML campaign without executing generated code.

python scripts/compliance_audit.py --input evidence.zip --outdir reports/compliance
Requires numpy, pandas, scipy, matplotlib, PyYAML. Read methodology.md in output.
"""

from __future__ import annotations

import argparse
import ast
import collections
import csv
import hashlib
import io
import itertools
import json
import re
import tempfile
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

if __package__:
    from ._compliance_checks import audit_candidates
else:
    from _compliance_checks import audit_candidates

LABELS = {
    "baseline": "Original",
    "specification-poor": "Broad",
    "specification-specific": "Tight",
    "validation-no-semantic-retry": "No semantic retry",
    "validation-no-execution-retry": "No execution retry",
    "no-csp": "No CSP",
}


def recover(source):
    z = zipfile.ZipFile(source)
    frozen = json.loads(z.read("campaign/campaign.json"))
    candidates = json.loads(z.read("candidate_index.json"))
    specs = {}
    for name in ["frozen-base-specification.yml"] + [
        "specifications/" + k for k in frozen["generated_specifications"]
    ]:
        raw = z.read("campaign/" + name)
        expected = (
            frozen["base_specification_sha256"]
            if name.startswith("frozen")
            else frozen["generated_specifications"][name[len("specifications/") :]]
        )
        actual = hashlib.sha256(
            raw
            if name.startswith("frozen")
            else json.dumps(
                raw.decode(), sort_keys=True, separators=(",", ":"), allow_nan=False
            ).encode()
        ).hexdigest()
        assert actual == expected, (name, actual, expected)
        specs[name] = yaml.safe_load(raw)
    summaries = {}
    winners = {}
    for name in z.namelist():
        if name.startswith("campaign/") and name.endswith("/results.csv"):
            for r in csv.DictReader(io.StringIO(z.read(name).decode())):
                summaries[r["Run Identity"]] = r
        if name.startswith("campaign/") and name.endswith("/selection.json"):
            p = json.loads(z.read(name))
            winners[p["run_identity"]] = p.get("selected")
    trace_recipes = collections.defaultdict(list)
    trace_codes = {}
    for line in z.read("traces/implementation_states.jsonl").splitlines():
        span = json.loads(line)
        for obs in span["observations"]:
            fields = obs.get("fields", {})
            p = fields.get("pipeline")
            identity = fields.get("run_identity")
            if identity in summaries and isinstance(p, dict) and p.get("steps"):
                key = (identity, str(p["id"]))
                steps = p["steps"]
                if steps not in trace_recipes[key]:
                    trace_recipes[key].append(steps)
                if isinstance(p.get("code"), str):
                    trace_codes[
                        (
                            identity,
                            str(p["id"]),
                            hashlib.sha256(p["code"].encode()).hexdigest(),
                        )
                    ] = p["code"]
    cache = {}
    recipe_cache = {}
    codes = {}
    out = []
    miss = []

    def digest(steps, c, hp):
        return hashlib.sha256(
            json.dumps(
                {
                    "structure": steps,
                    "hyperparameters": hp,
                    "code_sha256": c["code_sha256"],
                    "fit_seed": frozen["config"].get("run_seed", 42),
                },
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode()
        ).hexdigest()

    def possibilities(specname, task, keys):
        key = (specname, task, tuple(sorted(keys)))
        if key not in recipe_cache:
            choices = []
            for stage, definition in specs[specname]["pipeline"]["steps"].items():
                # Recover even an erroneous planned task; the audit flags task violations separately.
                opts = [None]
                for entry in definition["candidates"]:
                    for name, config in entry.items():
                        params = config.get("params", {})
                        if set(params) <= keys:
                            opts.append(
                                {
                                    "name": stage,
                                    "candidate": name,
                                    "hyperparameters": params,
                                }
                            )
                choices.append(opts)
            recipe_cache[key] = [
                steps
                for combo in itertools.product(*choices)
                if (steps := [s for s in combo if s])
                and {k for s in steps for k in s["hyperparameters"]} == keys
            ]
        return recipe_cache[key]

    for c in candidates:
        hp = ast.literal_eval(c["hyperparameters"])
        key = (c["run_identity"], str(c["pipeline_id"]))
        summary = summaries[c["run_identity"]]
        specname = (
            "specifications/poor.yml"
            if c["condition"] == "specification-poor"
            else "specifications/specific/" + c["dataset"] + ".yml"
            if c["condition"] == "specification-specific"
            else "frozen-base-specification.yml"
        )
        steps = cache.get(key)
        if steps is None or digest(steps, c, hp) != c["candidate_key"]:
            matches = [
                s for s in trace_recipes[key] if digest(s, c, hp) == c["candidate_key"]
            ]
            if not matches:
                matches = [
                    s
                    for s in possibilities(specname, summary["Problem"], set(hp))
                    if digest(s, c, hp) == c["candidate_key"]
                ]
            if len(matches) != 1:
                steps = None
                miss.append(
                    {
                        k: c[k]
                        for k in (
                            "condition",
                            "dataset",
                            "repetition",
                            "pipeline_id",
                            "code_sha256",
                        )
                    }
                )
            else:
                steps = matches[0]
                cache[key] = steps
        if c["code_sha256"] not in codes:
            raw = z.read(c["matching_code_members"][0])
            assert hashlib.sha256(raw).hexdigest() == c["code_sha256"]
            codes[c["code_sha256"]] = raw.decode()
        out.append(
            {
                **c,
                "parameters": hp,
                "requested_steps": steps,
                "effective_specification": specname,
                "problem": summary["Problem"],
                "numeric_features": int(summary["Numeric Features"]),
                "discrete_features": int(summary["Discrete Features"]),
            }
        )
    return z, frozen, out, codes, summaries, winners, cache, trace_codes, trace_recipes


def adapter_issue(f):
    return f["type"] == "unlisted_component" and (
        f["component"] in ("OneHotEncoder", "OrdinalEncoder")
        or (
            f.get("scope") == "categorical"
            and f["component"]
            in (
                "SimpleImputer",
                "FunctionTransformer",
                "CustomOrdinalEncoderWithNaN",
                "CategoricalNaNToNumericalNaN",
            )
        )
    )


def summarize_audit(rows, findings, winners):
    byrun = collections.defaultdict(list)
    for f in findings:
        byrun[f["run_id"]].append(f)
    for r in rows:
        selected = winners.get(r["run_identity"])
        r["winner"] = bool(
            selected
            and selected["run_id"] == r["run_id"]
            and selected["candidate_key"] == r["candidate_key"]
            and selected["code_sha256"] == r["code_sha256"]
        )
        fs = byrun[r["run_id"]]
        r["structural_issues"] = json.dumps(
            [f for f in fs if f["type"] != "hyperparameter_mismatch"]
        )
        r["parameter_issues"] = json.dumps(
            [f for f in fs if f["type"] == "hyperparameter_mismatch"]
        )
        r["adapter_allowed_any_violation"] = (
            any(not adapter_issue(f) for f in fs)
            if r["audit_status"] == "resolved"
            else None
        )
        r["audit_outcome"] = (
            "confirmed_violation"
            if r["any_violation"]
            else "no_detected_violation"
            if r["audit_status"] == "resolved" and not r["unresolved_parameters"]
            else "undetermined"
        )
    frame = pd.DataFrame(rows)
    versions = []
    keys = [
        "condition",
        "dataset",
        "repetition",
        "run_identity",
        "pipeline_id",
        "code_sha256",
    ]
    for key, part in frame.groupby(keys, sort=False):
        resolved = part.audit_status.eq("resolved").all()
        fs = [f for rid in part.run_id for f in byrun[rid]]
        sf = {f["key"] for f in fs if f["type"] != "hyperparameter_mismatch"}
        pf = {f["key"] for f in fs if f["type"] == "hyperparameter_mismatch"}
        versions.append(
            dict(zip(keys, key))
            | {
                "candidate_records": len(part),
                "resolved": resolved,
                "has_winner": bool(part.winner.any()),
                "has_eligible_candidate": bool(part.eligible.any()),
                "structural_violation_count": len(sf) if resolved else None,
                "parameter_violation_count": len(pf) if resolved else None,
                "any_structural_violation": bool(sf) if resolved else None,
                "any_parameter_violation": bool(pf) if resolved else None,
                "any_violation": bool(sf | pf) if resolved else None,
                "adapter_allowed_any_violation": bool(
                    part.adapter_allowed_any_violation.eq(True).any()
                )
                if resolved
                else None,
            }
        )
    vf = pd.DataFrame(versions)
    summary = []
    for cond in LABELS:
        for pop, table in [
            ("implementation_versions", vf.loc[vf.condition.eq(cond)]),
            ("candidate_instances", frame.loc[frame.condition.eq(cond)]),
            (
                "eligible_instances",
                frame.loc[frame.condition.eq(cond) & frame.eligible],
            ),
            ("winning_instances", frame.loc[frame.condition.eq(cond) & frame.winner]),
        ]:
            valid = (
                table.loc[table.resolved]
                if "resolved" in table
                else table.loc[table.audit_status.eq("resolved")]
            )
            entry = {
                "condition": cond,
                "population": pop,
                "total": len(table),
                "auditable": len(valid),
                "not_auditable": len(table) - len(valid),
            }
            for field in [
                "any_structural_violation",
                "any_parameter_violation",
                "any_violation",
                "adapter_allowed_any_violation",
            ]:
                n = int(valid[field].eq(True).sum())
                entry[field + "_count"] = n
                entry[field + "_rate"] = n / len(valid) if len(valid) else np.nan
            summary.append(entry)
    return frame, vf, pd.DataFrame(summary)


def extra_sources(
    z, candidates, codes, recipes, trace_codes, summaries, trace_recipes, frozen
):
    """Recover non-ledger artifact/trace versions; audit separately with explicit scope."""
    known = {
        (c["run_identity"], str(c["pipeline_id"]), c["code_sha256"]) for c in candidates
    }
    extras = {}
    inventory = {}
    unknown = []
    ledger_hashes = {c["code_sha256"] for c in candidates}
    names = z.namelist()
    meta = {
        n.split("/")[1]: json.loads(z.read(n))
        for n in names
        if n.startswith("mlflow_runs/") and n.endswith("/run.json")
    }

    # Outside-ledger recipes cannot be candidate-key verified. Retained states
    # and the machine-written numbered pipeline header provide explicit evidence.
    origins = {k: "candidate_key_verified" for k in recipes}
    for key, options in trace_recipes.items():
        if key not in recipes and len(options) == 1:
            recipes[key] = options[0]
            origins[key] = "retained_trace_state"
    for name in names:
        if not name.startswith("mlflow_runs/") or not name.endswith("/pipeline.md"):
            continue
        m = meta[name.split("/")[1]]
        match = re.fullmatch(r"pipeline_(\d+)_[A-Za-z_]+", m.get("name") or "")
        if not match:
            continue
        declared = re.findall(
            r"^\d+[.)]\s+\*\*([^*]+)\*\*\s+with\s+`([^`]+)`",
            z.read(name).decode(),
            re.MULTILINE,
        )
        if not declared:
            continue
        for label in m["dataset_runs"]:
            identity = label["run_identity"]
            key = (identity, match[1])
            if identity not in summaries or key in recipes:
                continue
            cond = label["condition"]
            dataset = label["dataset"]
            specname = (
                "specifications/poor.yml"
                if cond == "specification-poor"
                else "specifications/specific/" + dataset + ".yml"
                if cond == "specification-specific"
                else "frozen-base-specification.yml"
            )
            spec = yaml.safe_load(z.read("campaign/" + specname))
            steps = []
            for stage, candidate in declared:
                definitions = (
                    spec["pipeline"]["steps"].get(stage, {}).get("candidates", [])
                )
                entries = [d[candidate] for d in definitions if candidate in d]
                if len(entries) != 1:
                    break
                steps.append(
                    {
                        "name": stage,
                        "candidate": candidate,
                        "hyperparameters": entries[0].get("params", {}),
                    }
                )
            else:
                recipes[key] = steps
                origins[key] = "machine_written_pipeline_header"

    # Some failed dataset runs have artifacts but zero registered candidates.
    # Their attribution comes from campaign summaries, never from a guessed fit.
    run_labels = {}
    for name in names:
        if name.startswith("campaign/") and name.endswith("/results.csv"):
            condition = name.split("/")[1]
            repetition = int(name.split("/")[2][4:])
            for row in csv.DictReader(io.StringIO(z.read(name).decode())):
                run_labels[row["Run Identity"]] = {
                    "condition": condition,
                    "repetition": repetition,
                }

    def add(identity, pid, h, source, parameters=None):
        key = (identity, str(pid), h)
        if key in known or key in extras or identity not in summaries:
            return
        steps = recipes.get((identity, str(pid)))
        summary = summaries[identity]
        extras[key] = {
            "condition": run_labels[identity]["condition"],
            "dataset": summary["Dataset"],
            "repetition": run_labels[identity]["repetition"],
            "run_identity": identity,
            "pipeline_id": str(pid),
            "code_sha256": h,
            "source_member": source,
            "requested_steps": steps,
            "recipe_origin": origins.get((identity, str(pid)), "unavailable"),
            "parameters": parameters,
            "problem": summary["Problem"],
            "numeric_features": int(summary["Numeric Features"]),
            "discrete_features": int(summary["Discrete Features"]),
        }

    for name in names:
        if not name.startswith("mlflow_runs/") or not name.endswith("/code.py"):
            continue
        raw = z.read(name)
        h = hashlib.sha256(raw).hexdigest()
        codes.setdefault(h, raw.decode())
        m = meta[name.split("/")[1]]
        if h not in inventory:
            try:
                ast.parse(raw.decode())
                status = "parses"
                reason = ""
            except SyntaxError as e:
                status = "invalid_source"
                reason = f"{e.msg}, line {e.lineno}"
            inventory[h] = {
                "code_sha256": h,
                "source_status": status,
                "reason": reason,
                "source_member": name,
                "artifact_copies": 0,
                "in_candidate_ledger": h in ledger_hashes,
            }
        inventory[h]["artifact_copies"] += 1
        match = re.fullmatch(
            r"(?:pipeline_)?(\d+)_[A-Za-z_]+(?:_run_\d+)?", m.get("name") or ""
        )
        for label in m["dataset_runs"]:
            if label["run_identity"] not in summaries:
                continue
            if not match:
                unknown.append(
                    {
                        "source_member": name,
                        "run_identity": label["run_identity"],
                        "code_sha256": h,
                    }
                )
                continue
            params = {}
            for k, v in m.get("parameters", {}).items():
                try:
                    params[k] = ast.literal_eval(v)
                except (ValueError, SyntaxError):
                    params[k] = v
            add(label["run_identity"], match[1], h, name, params or None)
    for (identity, pid, h), code in trace_codes.items():
        codes.setdefault(h, code)
        add(identity, pid, h, "traces/implementation_states.jsonl")
        if h not in inventory:
            try:
                ast.parse(code)
                status = "parses"
                reason = ""
            except SyntaxError as err:
                status = "invalid_source"
                reason = str(err)
            inventory[h] = {
                "code_sha256": h,
                "source_status": status,
                "reason": reason,
                "source_member": "traces/implementation_states.jsonl",
                "artifact_copies": 0,
                "in_candidate_ledger": h in ledger_hashes,
            }
    # Additional versions have structural-only audits, using actual logged
    # arguments when available and unresolved symbols otherwise.
    audited = []
    findings = []
    if __package__:
        from ._compliance_checks import (
            CLASSES,
            Factory,
            Symbol,
            graph_nodes,
            graph_paths,
        )
    else:
        from _compliance_checks import (
            CLASSES,
            Factory,
            Symbol,
            graph_nodes,
            graph_paths,
        )
    for e in extras.values():
        row = {k: v for k, v in e.items() if k not in ("parameters", "requested_steps")}
        issues = []
        try:
            if not e["requested_steps"]:
                raise ValueError("No verified planned recipe for this version")
            params = e["parameters"] or {
                k: Symbol(k)
                for step in e["requested_steps"]
                for k in step["hyperparameters"]
            }
            model = Factory(
                codes[e["code_sha256"]],
                e["numeric_features"],
                e["discrete_features"],
                params,
                e["dataset"],
            ).run()
            nodes = list(graph_nodes(model))
            expected = {CLASSES[s["candidate"]] for s in e["requested_steps"]}
            for cls in expected - {n.name for n in nodes}:
                issues.append(
                    {
                        "type": "missing_declared_component",
                        "component": cls,
                        "line": None,
                    }
                )
            for n in nodes:
                if n.name not in expected:
                    issues.append(
                        {
                            "type": "unlisted_component",
                            "component": n.name,
                            "line": n.line,
                            "scope": getattr(n, "scope", "global"),
                        }
                    )
            for step in e["requested_steps"]:
                if (
                    step["name"] in ("classification", "regression")
                    and step["name"] != e["problem"]
                ):
                    issues.append(
                        {
                            "type": "wrong_task_recipe",
                            "component": step["candidate"],
                            "line": None,
                        }
                    )
            ranks = {
                CLASSES[s["candidate"]]: i for i, s in enumerate(e["requested_steps"])
            }
            for path in graph_paths(model):
                ns = [n for n in path if n.name in ranks]
                for a, b in itertools.pairwise(ns):
                    if ranks[a.name] > ranks[b.name]:
                        issues.append(
                            {
                                "type": "declared_order_violation",
                                "component": a.name + ">" + b.name,
                                "line": a.line,
                            }
                        )
            row["audit_status"] = "resolved_structure_only"
            row["structural_violation_count"] = len(
                {(f["type"], f["component"]) for f in issues}
            )
            row["audit_outcome"] = (
                "confirmed_structural_violation"
                if issues
                else "no_structural_violation_detected"
            )
        except SyntaxError as err:
            row["audit_status"] = "invalid_source"
            row["audit_outcome"] = "undetermined"
            row["reason"] = str(err)
        except Exception as err:  # noqa: BLE001 - record unsupported source, never certify it
            row["audit_status"] = "unresolved"
            row["audit_outcome"] = "undetermined"
            row["reason"] = str(err)
        row["parameters_audited"] = False
        audited.append(row)
        findings.extend(
            {
                **{
                    k: row[k]
                    for k in [
                        "condition",
                        "dataset",
                        "repetition",
                        "pipeline_id",
                        "run_identity",
                        "code_sha256",
                        "source_member",
                    ]
                },
                **f,
            }
            for f in issues
        )
    return (
        pd.DataFrame(audited),
        pd.DataFrame(findings),
        pd.DataFrame(inventory.values()),
        pd.DataFrame(unknown),
    )


def write_report(source, outdir):
    outdir = Path(outdir).resolve()
    if outdir.exists():
        raise ValueError("Use a new output directory")
    outdir.mkdir(parents=True)
    z, frozen, cs, codes, summaries, winners, recipes, trace_codes, trace_recipes = (
        recover(source)
    )
    print(f"Hash-verified recipes and code: {len(cs)} candidate records", flush=True)
    rows, findings, unresolved = audit_candidates(cs, codes)
    frame, versions, summary = summarize_audit(rows, findings, winners)
    print(
        "Audited candidate statuses:",
        frame.audit_status.value_counts().to_dict(),
        flush=True,
    )
    tables = outdir / "tables"
    tables.mkdir()
    for name, table in [
        ("instance_audit", frame),
        ("implementation_audit", versions),
        ("comparison_summary", summary),
        ("individual_findings", pd.DataFrame(findings)),
        ("unresolved_audit", pd.DataFrame(unresolved)),
        ("winner_audit", frame.loc[frame.winner]),
    ]:
        table.to_csv(tables / f"{name}.csv", index=False)
    byidentity = {
        identity: part
        for identity, part in frame.loc[frame.winner].groupby("run_identity")
    }
    run_locations = {}
    for n in z.namelist():
        if n.startswith("campaign/") and n.endswith("/results.csv"):
            for r in csv.DictReader(io.StringIO(z.read(n).decode())):
                run_locations[r["Run Identity"]] = n
    runrows = []
    for identity, s in summaries.items():
        matches = byidentity.get(identity)
        location = run_locations[identity]
        condition = location.split("/")[1]
        rep = int(location.split("/")[2][4:])
        status = s["Status"]
        row = {
            "campaign_identity": frozen["campaign_identity"],
            "condition": condition,
            "repetition": rep,
            "dataset": s["Dataset"],
            "run_identity": identity,
            "status": status,
            "metric": s["Validation Metric"],
            "score": s.get("Search CV Score (selection; not independent test)", ""),
            "audit_outcome": "not_applicable"
            if status != "completed"
            else "undetermined",
        }
        if matches is not None:
            if len(matches) != 1:
                raise ValueError("Ambiguous winning instance")
            a = matches.iloc[0]
            row.update(
                {
                    k: a[k]
                    for k in [
                        "pipeline_id",
                        "code_sha256",
                        "run_id",
                        "audit_outcome",
                        "audit_status",
                        "structural_violation_count",
                        "parameter_violation_count",
                        "any_structural_violation",
                        "any_parameter_violation",
                        "adapter_allowed_any_violation",
                        "unresolved_parameters",
                        "structural_issues",
                        "parameter_issues",
                        "source_member",
                    ]
                }
            )
            if not np.isclose(
                float(a.validation_score), float(row["score"]), rtol=1e-12, atol=1e-12
            ):
                raise ValueError("Winning score does not match summary")
        runrows.append(row)
    runframe = pd.DataFrame(runrows)
    runframe.to_csv(tables / "run_audit.csv", index=False)
    perrun = (
        frame.groupby(["condition", "dataset", "repetition"])
        .agg(
            candidate_records=("run_id", "size"),
            auditable=("audit_status", lambda s: int(s.eq("resolved").sum())),
            structural_violations=("any_structural_violation", "sum"),
            parameter_violations=("any_parameter_violation", "sum"),
            either_violations=("any_violation", "sum"),
        )
        .reset_index()
    )
    perrun.to_csv(tables / "per_dataset_repetition.csv", index=False)
    print("Collecting additional source versions...", flush=True)
    extras, extra_findings, inventory, unlinked = extra_sources(
        z, cs, codes, recipes, trace_codes, summaries, trace_recipes, frozen
    )
    for name, table in [
        ("additional_version_audit", extras),
        ("additional_version_findings", extra_findings),
        ("all_exported_source_inventory", inventory),
        ("unlinked_source_copies", unlinked),
    ]:
        table.to_csv(tables / f"{name}.csv", index=False)
    direct = []
    for line in z.read("traces/implementation_states.jsonl").splitlines():
        span = json.loads(line)
        if span.get("name") != "execute_code":
            continue
        for obs in span["observations"]:
            f = obs.get("fields", {})
            p = f.get("pipeline")
            identity = f.get("run_identity")
            if (
                identity not in summaries
                or ".mlflow.spanInputs" not in obs.get("json_path", "")
                or not isinstance(f.get("code_validation_feedback"), bool)
                or not isinstance(p, dict)
                or not p.get("code")
            ):
                continue
            direct.append(
                {
                    "run_identity": identity,
                    "pipeline_id": p["id"],
                    "code_sha256": hashlib.sha256(p["code"].encode()).hexdigest(),
                    "verdict": "accepted"
                    if f["code_validation_feedback"]
                    else "rejected",
                    "feedback": json.dumps(f.get("semantic_validation_feedback", [])),
                    "span_id": span["span_id"],
                    "trace_id": span["trace_id"],
                }
            )
    pd.DataFrame(direct).drop_duplicates().to_csv(
        tables / "direct_judge_observations.csv", index=False
    )
    coverage = {
        "audit_script_sha256": {
            name: hashlib.sha256(
                (Path(__file__).parent / name).read_bytes()
            ).hexdigest()
            for name in (
                "compliance_audit.py",
                "_compliance_checks.py",
                "_compliance_static.py",
            )
        },
        "campaign_identity": frozen["campaign_identity"],
        "source_zip_sha256": hashlib.sha256(Path(source).read_bytes()).hexdigest(),
        "dataset_runs": len(summaries),
        "candidate_records": len(cs),
        "hash_verified_recipes": sum(c["requested_steps"] is not None for c in cs),
        "candidate_records_with_verified_code": len(cs),
        "candidate_instance_statuses": frame.audit_status.value_counts().to_dict(),
        "registered_code_versions": len(versions),
        "all_exported_source_hashes": len(inventory),
        "additional_version_audit_statuses": extras.audit_status.value_counts().to_dict()
        if len(extras)
        else {},
        "winner_outcomes": {
            c: p.audit_outcome.value_counts().to_dict()
            for c, p in runframe.groupby("condition")
        },
        "parameters_unresolved_instances": int(
            frame.unresolved_parameters.ne("").sum()
        ),
        "direct_judge_observations": len(direct),
        "scope": "All recoverable registered instances and additional attributable code versions. Additional versions have structural-only audits, not observed parameter-instance scores.",
    }
    (outdir / "coverage.json").write_text(json.dumps(coverage, indent=2))
    (outdir / "methodology.md").write_text("""# Post hoc compliance audit

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
""")
    write_summary(summary, runframe, outdir)
    audit_plots(summary, perrun, runframe, outdir / "audit_figures")
    # Temporary input texts only; never copy models or leave an evidence snapshot.
    if __package__:
        from .campaign_analysis import make_report
    else:
        from campaign_analysis import make_report
    with tempfile.TemporaryDirectory(prefix="age-ml-report-input-") as temporary:
        campaign = Path(temporary) / "campaign"
        campaign.mkdir()
        wanted = {
            "campaign.json",
            "results.csv",
            "result.json",
            "selection.json",
            "validation_candidates.csv",
            "exploration_failures.json",
            "storage_cleanup.json",
        }
        for name in z.namelist():
            if not name.startswith("campaign/") or Path(name).name not in wanted:
                continue
            relative = Path(name[len("campaign/") :])
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("Unsafe archive member")
            dest = campaign / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(z.read(name))
        make_report(
            campaign,
            outdir / "performance",
            repetitions="all",
            audit=tables / "run_audit.csv",
        )
    z.close()
    print(
        runframe.groupby(["condition", "audit_outcome"]).size().to_string(), flush=True
    )
    return coverage


def write_summary(summary, runs, outdir):
    selected = summary.loc[summary.population.eq("winning_instances")].set_index(
        "condition"
    )
    rows = []
    for condition, label in LABELS.items():
        part = runs.loc[runs.condition.eq(condition)]
        a = selected.loc[condition]
        rows.append(
            {
                "condition": condition,
                "label": label,
                "expected_outcomes": len(part),
                "selected_winners": int(a.total),
                "strict_winner_violations": int(a.any_violation_count),
                "adapters_allowed_winner_violations": int(
                    a.adapter_allowed_any_violation_count
                ),
                "unsuccessful_outcomes": int(part.status.ne("completed").sum()),
            }
        )
    table = pd.DataFrame(rows)
    table.to_csv(outdir / "tables/winner_outcomes_summary.csv", index=False)
    from importlib import import_module

    analysis = import_module(
        (__package__ + "." if __package__ else "") + "campaign_analysis"
    )
    text = [
        "# Gemini campaign: post hoc compliance analysis",
        analysis.markdown_table(table),
        "Strict counts refer to selected implementations, not the number of individual findings. One winner can have multiple findings. The adapters-allowed column permits categorical representation adapters only; missing/substituted models, task mismatches, global extra components and parameter mismatches remain violations.",
    ]
    for condition in ("baseline", "validation-no-semantic-retry"):
        row = selected.loc[condition]
        version = summary.loc[
            summary.condition.eq(condition)
            & summary.population.eq("implementation_versions")
        ].iloc[0]
        text.append(
            f"{LABELS[condition]}: {int(row.any_violation_count)}/{int(row.total)} strict winner violations; {int(row.adapter_allowed_any_violation_count)}/{int(row.total)} with categorical adapters allowed. Structural violation rate among resolved registered code versions: {100 * version.any_structural_violation_rate:.2f}% ({int(version.any_structural_violation_count)}/{int(version.auditable)})."
        )
    text += [
        "These are descriptive differences in the registered population, not evidence of statistical significance or a causal judge effect. Versions and fits are clustered; technical repetitions share recorded seeds. A smaller violation rate among successful candidates does not estimate precision/recall of the judge.",
        "The strict and adapters-allowed policies answer different questions; this choice materially affects interpretation and should be stated in the paper. A wrong_task_recipe finding refers to planning a classifier for a regression task (or the reverse), not to code deviating from that same recipe.",
        "Filtered figures drop original winners with confirmed violations or undetermined checks; they do not choose an alternative candidate. Some dataset/configuration cells may have no included result. This does not mean their score is zero. Costs include all outcomes.",
        "## Files",
        "tables/run_audit.csv: all dataset outcomes and winner verdicts. tables/individual_findings.csv: individual violations with source locations. tables/instance_audit.csv: registered parameter instances. tables/implementation_audit.csv: versions deduplicated within pipeline/run. Additional versions and unlinked sources are separate. coverage.json and methodology.md define coverage and limitations.",
        "performance/figures/: all winners and outcome/resource figures. performance/figures/without_detected_violations/: filtered performance figures. performance/tables/: CSV, Markdown and LaTeX tables, including paper layouts and filtered variants. audit_figures/: population violation rates and dataset-level rates.",
        "## Reproduce",
        "Run `python scripts/compliance_audit.py --input evidence.zip --outdir reports/compliance` after applying the companion code ZIP. To regenerate plots from repository results, run `python scripts/campaign_analysis.py report --campaign PATH --repetitions all --audit reports/compliance/tables/run_audit.csv --outdir reports/performance`. The evidence ZIP remains the source for reproduction; large extracted evidence files are omitted from the downloadable report package.",
    ]
    (outdir / "README.md").write_text("\n\n".join(text) + "\n")


def audit_plots(summary, perrun, runs, directory):
    """Plot one strict contract throughout: structure, hyperparameters, union."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MultipleLocator

    directory.mkdir(exist_ok=True)
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "pdf.fonttype": 42,
        }
    )
    perrun = perrun.copy()
    # Older CSVs can contain True/False for a one-record group's sum.
    for column in (
        "structural_violations",
        "parameter_violations",
        "either_violations",
    ):
        perrun[column] = pd.to_numeric(
            perrun[column].map(
                lambda value: {"true": 1, "false": 0}.get(str(value).lower(), value)
            ),
            errors="raise",
        )
    conditions = list(LABELS)
    labels = [LABELS[c] for c in conditions]
    populations = [
        (
            "implementation_versions",
            "Pipeline implementations",
            "Distinct code versions within each pipeline/run",
        ),
        (
            "eligible_instances",
            "Eligible instances",
            "Successful fits admitted to candidate selection",
        ),
        (
            "winning_instances",
            "Selected winners",
            "Best candidate in each successful dataset run",
        ),
    ]
    measures = [
        ("any_structural_violation", "Structure", "#345995"),
        ("any_parameter_violation", "Hyperparameters", "#c65f53"),
        ("any_violation", "Any violation", "#e6b83f"),
    ]
    # All three bars use the SAME denominator and policy. The third is a union,
    # not a sum: overlap must never be counted twice.
    for _, part in summary.groupby("population"):
        n = part.auditable
        structure = part.any_structural_violation_count
        parameters = part.any_parameter_violation_count
        total = part.any_violation_count
        if (
            (total < structure)
            | (total < parameters)
            | (total > structure + parameters)
            | (total > n)
        ).any():
            raise ValueError("Inconsistent structural/hyperparameter union counts")

    def bracket(ax):
        x = -0.43
        ax.plot(
            [x + 0.025, x, x, x + 0.025],
            [-0.4, -0.4, 2.4, 2.4],
            transform=ax.get_yaxis_transform(),
            clip_on=False,
            color="#333333",
            lw=1,
        )
        ax.text(
            x - 0.035,
            1,
            "AGE-ML",
            transform=ax.get_yaxis_transform(),
            rotation=90,
            ha="right",
            va="center",
            fontsize=9,
        )

    def save(fig, name):
        for ext in ("png", "pdf"):
            fig.savefig(directory / f"{name}.{ext}", dpi=190, bbox_inches="tight")
        plt.close(fig)

    limit = 100
    fig, axes = plt.subplots(1, 3, figsize=(17.5, 6), sharey=True, sharex=True)
    for ax, (pop, title, subtitle) in zip(axes, populations):
        part = (
            summary.loc[summary.population.eq(pop)]
            .set_index("condition")
            .reindex(conditions)
        )
        for j, (field, label, color) in enumerate(measures):
            vals = 100 * part[field + "_rate"].to_numpy()
            bars = ax.barh(
                np.arange(len(conditions)) + (j - 1) * 0.24,
                vals,
                height=0.21,
                label=label,
                color=color,
            )
            annotations = [
                f"{v:.1f}%" + (f"  (n={int(n):,})" if field == "any_violation" else "")
                for v, n in zip(vals, part.auditable)
            ]
            ax.bar_label(bars, labels=annotations, padding=4, fontsize=8)
        ax.set_title(title, fontsize=13, pad=34)
        ax.text(
            0.5,
            1.025,
            subtitle,
            transform=ax.transAxes,
            ha="center",
            fontsize=8,
            color="#555555",
        )
        ax.set_yticks(range(len(conditions)), labels)
        ax.set_xlim(0, limit)
        ax.xaxis.set_major_locator(MultipleLocator(20 if limit >= 80 else 10))
        ax.set_xlabel("With at least one violation (%)", fontsize=9)
        ax.grid(axis="x", alpha=0.15)
        ax.set_axisbelow(True)
    axes[0].invert_yaxis()
    bracket(axes[0])
    handles, legend = axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        legend,
        loc="upper center",
        bbox_to_anchor=(0.55, 1.015),
        ncol=3,
        frameon=False,
    )
    fig.text(
        0.01,
        0.015,
        "All bars use the strict specification contract. Any violation = structure OR hyperparameters; records violating both count once.\nn = audited records in that panel/condition. Invalid or unresolved records are excluded; denominators differ between panels. Counts and exclusions are in comparison_summary.csv.",
        fontsize=8,
        color="#555555",
    )
    fig.tight_layout(rect=(0, 0.10, 1, 0.91))
    save(fig, "01_violation_rates")

    # Replace the crowded scatter with a dataset/configuration matrix. Each
    # dataset/repetition gets equal weight; candidate-rich runs do not dominate.
    order = list(dict.fromkeys(runs.dataset))
    matrix = np.full((len(order), len(conditions)), np.nan)
    coverage = np.zeros_like(matrix, dtype=int)
    expected = runs.groupby(["dataset", "condition"]).size()
    records = []
    for i, dataset in enumerate(order):
        for j, condition in enumerate(conditions):
            part = perrun.loc[
                perrun.dataset.eq(dataset)
                & perrun.condition.eq(condition)
                & perrun.auditable.gt(0)
            ]
            rates = 100 * part.either_violations / part.auditable
            if len(rates):
                matrix[i, j] = rates.mean()
            coverage[i, j] = len(rates)
            records.append(
                {
                    "dataset": dataset,
                    "condition": condition,
                    "mean_strict_instance_violation_rate_percent": matrix[i, j],
                    "audited_dataset_runs": len(rates),
                    "expected_dataset_runs": int(expected.get((dataset, condition), 0)),
                }
            )
    pd.DataFrame(records).to_csv(
        directory / "02_violations_by_dataset.csv", index=False
    )
    fig, ax = plt.subplots(figsize=(12.5, max(6.5, 0.6 * len(order) + 2)))
    cmap = plt.get_cmap("Blues").with_extremes(bad="#eeeeee")
    artist = ax.imshow(
        np.ma.masked_invalid(matrix), aspect="auto", vmin=0, vmax=100, cmap=cmap
    )
    ax.set_xticks(
        range(len(conditions)),
        [
            x.replace("No semantic retry", "No semantic\nretry").replace(
                "No execution retry", "No execution\nretry"
            )
            for x in labels
        ],
        fontsize=9,
    )
    pretty = lambda n: {"har": "HAR", "mnist_784": "MNIST", "auto_mpg": "Auto MPG"}.get(
        n, n.replace("_", " ").capitalize()
    )
    ax.set_yticks(range(len(order)), [pretty(n) for n in order])
    for i, dataset in enumerate(order):
        for j, condition in enumerate(conditions):
            v = matrix[i, j]
            n = coverage[i, j]
            exp = int(expected.get((dataset, condition), 0))
            text = (
                f"{v:.1f}%\n{n}/{exp} runs" if np.isfinite(v) else f"N/A\n0/{exp} runs"
            )
            ax.text(
                j,
                i,
                text,
                ha="center",
                va="center",
                fontsize=9,
                color="white" if np.isfinite(v) and v > 55 else "#222222",
            )
    ax.set_xticks(np.arange(-0.5, len(conditions), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(order), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=2)
    ax.tick_params(which="both", length=0)
    ax.plot(
        [-0.4, -0.4, 2.4, 2.4],
        [1.025, 1.055, 1.055, 1.025],
        transform=ax.get_xaxis_transform(),
        clip_on=False,
        color="#333333",
        lw=1,
    )
    ax.text(
        1,
        1.065,
        "AGE-ML",
        transform=ax.get_xaxis_transform(),
        ha="center",
        va="bottom",
        fontsize=10,
    )
    ax.set_title("Any specification violation by dataset", pad=48, fontsize=14)
    fig.colorbar(artist, ax=ax, shrink=0.85, label="Instances with any violation (%)")
    fig.text(
        0.01,
        0.015,
        "Same strict contract as Figure 01: structure OR hyperparameters. Each cell averages the per-run instance violation percentages equally.\nThe fraction shows dataset runs with auditable candidate records / expected runs. This includes failed and nonwinning fits; it is not a winner-performance plot.",
        fontsize=8,
        color="#555555",
    )
    fig.tight_layout(rect=(0, 0.10, 1, 0.98))
    save(fig, "02_violations_by_dataset")
    for ext in ("png", "pdf"):
        old = directory / f"02_run_level_distribution.{ext}"
        if old.exists():
            old.unlink()


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", required=True, type=Path)
    p.add_argument("--outdir", required=True, type=Path)
    args = p.parse_args(argv)
    write_report(args.input.resolve(), args.outdir)


if __name__ == "__main__":
    main()
