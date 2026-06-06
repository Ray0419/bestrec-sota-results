"""Finalize an isolated SOTA-lab run from streamed JSONL records."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import wilcoxon

from sota_common import (
    DATASET_LABELS,
    DATASET_STATS,
    DATASETS,
    LAB_CANDIDATE,
    LAB_METHODS,
    LAB_PROTOCOL,
    OFFICIAL_DROPOUTNET_FEATURE_CONFIG,
    NUM_FOLDS,
    ROOT,
    RUNS_DIR,
    load_dataset,
    make_item_kfold,
    metric_fmt,
    read_json,
    utc_now,
    write_json,
    write_manifest,
)

REQUIRED_COLD_FIELDS = {
    "dataset",
    "fold_id",
    "seed",
    "method",
    "user_id",
    "target_item_id",
    "candidate_scope",
    "ndcg10",
    "hr10",
    "rr",
}
REQUIRED_WARM_FIELDS = {
    "dataset",
    "fold_id",
    "seed",
    "method",
    "user_id",
    "target_item_id",
    "ndcg10",
    "hr10",
    "rr",
}
METRIC_FIELDS = ("ndcg10", "hr10", "rr")


def _validate_record(row: dict[str, Any], path: Path, line_no: int, expected_dataset: str | None, required: set[str], expected_scope: str | None) -> None:
    missing = required - set(row)
    if missing:
        raise ValueError(f"{path}:{line_no}: missing fields {sorted(missing)}")
    if expected_dataset is not None and row.get("dataset") != expected_dataset:
        raise ValueError(f"{path}:{line_no}: dataset={row.get('dataset')} expected {expected_dataset}")
    if expected_scope is not None and row.get("candidate_scope") != expected_scope:
        raise ValueError(f"{path}:{line_no}: candidate_scope={row.get('candidate_scope')} expected {expected_scope}")
    for field in ("seed", "fold_id", "user_id", "target_item_id"):
        int(row[field])
    if not str(row["method"]):
        raise ValueError(f"{path}:{line_no}: empty method")
    for field in METRIC_FIELDS:
        value = float(row[field])
        if not math.isfinite(value) or value < 0.0 or value > 1.0:
            raise ValueError(f"{path}:{line_no}: {field}={value} outside [0, 1]")


def stream_jsonl(path: Path, *, expected_dataset: str | None = None, required: set[str] | None = None, expected_scope: str | None = None):
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if line:
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{path}:{line_no}: bad JSONL row: {exc}") from exc
                if required is not None:
                    _validate_record(row, path, line_no, expected_dataset, required, expected_scope)
                yield row


def summarize_cold_dataset(path: Path, dataset: str) -> tuple[dict[str, Any], dict[str, dict[int, tuple[float, int]]]]:
    stats: dict[str, dict[str, float]] = defaultdict(lambda: {"ndcg": 0.0, "hr": 0.0, "rr": 0.0, "n": 0.0})
    user_sums: dict[str, dict[int, list[float]]] = defaultdict(lambda: defaultdict(lambda: [0.0, 0.0]))
    fold_counts: dict[str, Counter] = defaultdict(Counter)
    for row in stream_jsonl(path, expected_dataset=dataset, required=REQUIRED_COLD_FIELDS, expected_scope="full_catalog"):
        method = row["method"]
        seed_fold = (int(row["seed"]), int(row["fold_id"]))
        val = float(row["ndcg10"])
        st = stats[method]
        st["ndcg"] += val
        st["hr"] += float(row["hr10"])
        st["rr"] += float(row["rr"])
        st["n"] += 1
        fold_counts[method][seed_fold] += 1
        us = user_sums[method][int(row["user_id"])]
        us[0] += val
        us[1] += 1
    summary = {
        method: {
            "NDCG@10": st["ndcg"] / st["n"] if st["n"] else None,
            "HR@10": st["hr"] / st["n"] if st["n"] else None,
            "MRR": st["rr"] / st["n"] if st["n"] else None,
            "n_records": int(st["n"]),
            "seed_fold_count": len(fold_counts[method]),
            "fold_counts": {f"{seed}:{fold_id}": int(count) for (seed, fold_id), count in sorted(fold_counts[method].items())},
        }
        for method, st in sorted(stats.items())
    }
    user_means = {
        method: {u: (vals[0], int(vals[1])) for u, vals in users.items()}
        for method, users in user_sums.items()
    }
    return summary, user_means


def expected_seed_fold_count(seeds: list[int]) -> int:
    return len(seeds) * int(NUM_FOLDS)


def has_full_seed_fold_coverage(method_summary: dict[str, Any], seeds: list[int]) -> bool:
    return int(method_summary.get("seed_fold_count", 0) or 0) == expected_seed_fold_count(seeds)


def missing_seed_folds(method_summary: dict[str, Any], seeds: list[int], limit: int = 8) -> list[str]:
    present = set(str(x) for x in method_summary.get("fold_counts", {}))
    missing: list[str] = []
    for seed in seeds:
        for fold_id in range(int(NUM_FOLDS)):
            key = f"{seed}:{fold_id}"
            if key not in present:
                missing.append(key)
                if len(missing) >= limit:
                    return missing
    return missing


_EXPECTED_FOLD_COUNTS: dict[tuple[str, tuple[int, ...]], dict[str, int]] = {}


def expected_fold_record_counts(dataset: str, seeds: list[int]) -> dict[str, int]:
    key = (dataset, tuple(int(x) for x in seeds))
    if key in _EXPECTED_FOLD_COUNTS:
        return _EXPECTED_FOLD_COUNTS[key]
    interactions, _, _, n_items, _ = load_dataset(dataset)
    expected: dict[str, int] = {}
    for seed in seeds:
        splits = make_item_kfold(interactions, n_items, n_splits=int(NUM_FOLDS), seed=int(seed))
        for fold_id, (tr_idx, te_idx, _) in enumerate(splits):
            train_users = {int(interactions[int(idx)]["user_id"]) for idx in tr_idx}
            expected_count = sum(1 for idx in te_idx if int(interactions[int(idx)]["user_id"]) in train_users)
            expected[f"{int(seed)}:{int(fold_id)}"] = int(expected_count)
    _EXPECTED_FOLD_COUNTS[key] = expected
    return expected


def record_coverage_problems(method_summary: dict[str, Any], dataset: str, seeds: list[int], limit: int = 8) -> list[str]:
    expected = expected_fold_record_counts(dataset, seeds)
    actual = {str(key): int(value) for key, value in method_summary.get("fold_counts", {}).items()}
    problems: list[str] = []
    for key, expected_count in sorted(expected.items()):
        actual_count = actual.get(key)
        if actual_count is None:
            problems.append(f"{key} missing")
        elif actual_count != expected_count:
            problems.append(f"{key} has {actual_count}, expected {expected_count}")
        if len(problems) >= limit:
            return problems
    extra = sorted(set(actual) - set(expected))
    for key in extra:
        problems.append(f"{key} unexpected")
        if len(problems) >= limit:
            break
    return problems


def has_exact_record_coverage(method_summary: dict[str, Any], dataset: str, seeds: list[int]) -> bool:
    return not record_coverage_problems(method_summary, dataset, seeds, limit=1)


def summarize_warm_dataset(path: Path, dataset: str) -> dict[str, Any]:
    counts: dict[str, Counter] = defaultdict(Counter)
    stats: dict[str, dict[str, float]] = defaultdict(lambda: {"ndcg": 0.0, "hr": 0.0, "rr": 0.0, "n": 0.0})
    for row in stream_jsonl(path, expected_dataset=dataset, required=REQUIRED_WARM_FIELDS):
        method = row["method"]
        seed_fold = (int(row["seed"]), int(row["fold_id"]))
        counts[method][seed_fold] += 1
        st = stats[method]
        st["ndcg"] += float(row["ndcg10"])
        st["hr"] += float(row["hr10"])
        st["rr"] += float(row["rr"])
        st["n"] += 1
    return {
        "methods": {
            method: {
                "NDCG@10": st["ndcg"] / st["n"] if st["n"] else None,
                "HR@10": st["hr"] / st["n"] if st["n"] else None,
                "MRR": st["rr"] / st["n"] if st["n"] else None,
                "n_records": int(st["n"]),
            }
            for method, st in sorted(stats.items())
        },
        "fold_counts": {method: [int(v) for _, v in sorted(counter.items())] for method, counter in counts.items()},
    }


def user_mean_dict(user_sums: dict[int, tuple[float, int]]) -> dict[int, float]:
    return {u: s / c for u, (s, c) in user_sums.items() if c}


def holm(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted(rows, key=lambda x: x["p_raw"])
    active = True
    out = []
    for i, row in enumerate(ordered):
        threshold = 0.05 / max(1, len(ordered) - i)
        sig = bool(active and row["p_raw"] <= threshold)
        if not sig:
            active = False
        marker = "***" if sig and row["p_raw"] < 0.001 else "**" if sig and row["p_raw"] < 0.01 else "*" if sig else "n.s."
        out.append({**row, "holm_threshold": threshold, "holm_significant": sig, "marker": marker})
    return sorted(out, key=lambda x: x["comparison"])


def paired_bootstrap(path: Path, dataset: str, candidate: str, baseline: str, reps: int, seed: int) -> dict[str, Any]:
    base: dict[tuple[int, int, int, int], float] = {}
    for row in stream_jsonl(path, expected_dataset=dataset, required=REQUIRED_COLD_FIELDS, expected_scope="full_catalog"):
        if row["method"] == baseline:
            key = (int(row["seed"]), int(row["fold_id"]), int(row["user_id"]), int(row["target_item_id"]))
            base[key] = float(row["ndcg10"])
    users: list[int] = []
    items: list[int] = []
    folds: list[int] = []
    diffs: list[float] = []
    for row in stream_jsonl(path, expected_dataset=dataset, required=REQUIRED_COLD_FIELDS, expected_scope="full_catalog"):
        if row["method"] != candidate:
            continue
        key = (int(row["seed"]), int(row["fold_id"]), int(row["user_id"]), int(row["target_item_id"]))
        if key in base:
            users.append(key[2])
            items.append(key[3])
            folds.append(key[0] * 100 + key[1])
            diffs.append(float(row["ndcg10"]) - base[key])
    if not diffs:
        return {"delta_point": None, "ci_lo_95": None, "ci_hi_95": None, "B_replicates": reps, "resampling_unit": "user/item/fold clustered bootstrap"}
    del base
    diffs_arr = np.asarray(diffs, dtype=np.float32)
    _, user_inv = np.unique(np.asarray(users, dtype=np.int32), return_inverse=True)
    _, item_inv = np.unique(np.asarray(items, dtype=np.int32), return_inverse=True)
    _, fold_inv = np.unique(np.asarray(folds, dtype=np.int32), return_inverse=True)
    rng = np.random.RandomState(seed)
    vals = []
    for _ in range(reps):
        uw = np.bincount(rng.choice(user_inv.max() + 1, user_inv.max() + 1, replace=True), minlength=user_inv.max() + 1)
        iw = np.bincount(rng.choice(item_inv.max() + 1, item_inv.max() + 1, replace=True), minlength=item_inv.max() + 1)
        fw = np.bincount(rng.choice(fold_inv.max() + 1, fold_inv.max() + 1, replace=True), minlength=fold_inv.max() + 1)
        w = uw[user_inv] * iw[item_inv] * fw[fold_inv]
        den = int(w.sum())
        if den:
            vals.append(float(np.dot(w, diffs_arr) / den))
    if not vals:
        return {"delta_point": float(diffs_arr.mean()), "ci_lo_95": None, "ci_hi_95": None, "B_replicates": reps, "resampling_unit": "user/item/fold clustered bootstrap"}
    return {
        "delta_point": float(diffs_arr.mean()),
        "ci_lo_95": float(np.percentile(vals, 2.5)),
        "ci_hi_95": float(np.percentile(vals, 97.5)),
        "B_replicates": reps,
        "resampling_unit": "user/item/fold clustered bootstrap",
    }


def build_significance(run_dir: Path, cold: dict[str, Any], user_means: dict[str, Any], bootstrap_reps: int) -> dict[str, Any]:
    out = {
        "schema_version": 1,
        "candidate_method": LAB_CANDIDATE,
        "sample_unit": "per-user mean full-catalog cold-item NDCG@10",
        "correction_family": "Holm within dataset across candidate-vs-baseline comparisons",
        "cold_full_catalog": {},
    }
    for dataset, methods in cold.items():
        candidate_summary = methods.get(LAB_CANDIDATE, {})
        baseline_scores = {m: v["NDCG@10"] for m, v in methods.items() if m != LAB_CANDIDATE and v.get("NDCG@10") is not None}
        best = max(baseline_scores, key=baseline_scores.get) if baseline_scores else None
        cand_users = user_mean_dict(user_means[dataset].get(LAB_CANDIDATE, {}))
        rows = []
        for method in sorted(baseline_scores):
            base_users = user_mean_dict(user_means[dataset].get(method, {}))
            common = sorted(set(cand_users) & set(base_users))
            diffs = np.asarray([cand_users[u] - base_users[u] for u in common], dtype=np.float64)
            p = 1.0 if len(diffs) == 0 or np.allclose(diffs, 0) else float(wilcoxon(diffs, alternative="greater", zero_method="wilcox").pvalue)
            rows.append(
                {
                    "comparison": f"{LAB_CANDIDATE} > {method}",
                    "baseline": method,
                    "n_users": len(common),
                    "candidate_ndcg10": candidate_summary.get("NDCG@10"),
                    "baseline_ndcg10": baseline_scores[method],
                    "mean_delta": float(diffs.mean()) if len(diffs) else None,
                    "positive_users": int((diffs > 0).sum()),
                    "negative_users": int((diffs < 0).sum()),
                    "zero_users": int((diffs == 0).sum()),
                    "p_raw": p,
                }
            )
        boot = paired_bootstrap(run_dir / f"cold_full_catalog_records_{dataset}.jsonl", dataset, LAB_CANDIDATE, best, bootstrap_reps, 8675309) if best else {}
        out["cold_full_catalog"][dataset] = {
            "candidate_ndcg10": candidate_summary.get("NDCG@10"),
            "best_baseline": best,
            "best_baseline_ndcg10": baseline_scores.get(best) if best else None,
            "comparisons": holm(rows),
            "best_baseline_bootstrap": boot,
        }
    return out


def _resolve_path(raw: str | None) -> Path | None:
    if not raw:
        return None
    path = Path(raw)
    if path.is_absolute():
        return path
    return ROOT / path


def _official_source_audit(import_audit: dict[str, Any], audit_name: str) -> dict[str, Any]:
    source_dir = _resolve_path(import_audit.get("source_dir"))
    if not source_dir:
        return {}
    path = source_dir / audit_name
    return read_json(path, {}) if path.exists() else {}


def _all_datasets_have_method(cold: dict[str, Any], method: str) -> bool:
    return all(cold.get(dataset, {}).get(method, {}).get("n_records", 0) for dataset in DATASETS)


def _all_datasets_have_full_method(cold: dict[str, Any], method: str, seeds: list[int]) -> bool:
    return all(has_exact_record_coverage(cold.get(dataset, {}).get(method, {}), dataset, seeds) for dataset in DATASETS)


def baseline_audit(cold: dict[str, Any], seeds: list[int], run_dir: Path) -> dict[str, Any]:
    baselines = {}
    expected_folds = expected_seed_fold_count(seeds)
    direct_slots = {
        "official_dropoutnet_fixed": "official_dropoutnet_fixed_audit.json",
        "official_dropoutnet": "official_dropoutnet_audit.json",
        "official_blair": "official_blair_audit.json",
        "official_clcrec": "official_clcrec_audit.json",
        "official_melt": "official_melt_audit.json",
        "tiger_liger_retrieval": "tiger_liger_retrieval_audit.json",
    }
    for method, audit_name in direct_slots.items():
        audit_path = run_dir / audit_name
        method_audit = read_json(audit_path, {}) if audit_path.exists() else {}
        present = _all_datasets_have_method(cold, method)
        full_present = _all_datasets_have_full_method(cold, method, seeds)
        audit_status = method_audit.get("status")
        if full_present and audit_path.exists() and audit_status in {"complete", "partial", "partial_complete"}:
            status = "complete"
        elif present:
            status = "partial"
        else:
            status = audit_status or "not_run"
        notes = method_audit.get("notes", "")
        if status == "complete" and audit_status in {"partial", "partial_complete"}:
            chunk_note = (
                "Marked complete by exact canonical record coverage across all frozen datasets, seeds, and folds; "
                f"the evidence audit status is {audit_status} because the independent rebuild was executed in chunks."
            )
            if isinstance(notes, list):
                notes = [*notes, chunk_note]
            elif notes:
                notes = [str(notes), chunk_note]
            else:
                notes = chunk_note
        if method == "official_clcrec" and status == "complete":
            source_audit = _official_source_audit(method_audit, "official_clcrec_source_audit.json")
            if source_audit and not source_audit.get("sweep_hp"):
                status = "fixed_hp_only"
                notes = "Imported faithful CLCRec records used fixed modal hyperparameters, not the required HP sweep."
        baselines[method] = {
            "status": status,
            "seeds": seeds,
            "evidence_file": audit_name if audit_path.exists() else None,
            "records_present_all_datasets": bool(full_present),
            "expected_seed_folds_per_dataset": expected_folds,
            "notes": notes,
        }
    official_slots = {
        "blair_text": ("official_blair", "official_blair_audit.json"),
        "faithful_dropoutnet": ("official_dropoutnet", "official_dropoutnet_audit.json"),
        "clcrec_contrastive": ("official_clcrec", "official_clcrec_audit.json"),
        "melt_tail_transfer": ("official_melt", "official_melt_audit.json"),
    }
    for method in ["faithful_dropoutnet", "clcrec_contrastive", "melt_tail_transfer", "blair_text"]:
        present = any(cold.get(ds, {}).get(method, {}).get("n_records", 0) for ds in DATASETS)
        official_method, audit_name = official_slots[method]
        official_present = all(cold.get(ds, {}).get(official_method, {}).get("n_records", 0) for ds in DATASETS)
        official_full = _all_datasets_have_full_method(cold, official_method, seeds)
        audit_path = run_dir / audit_name
        official_audit = read_json(audit_path, {}) if audit_path.exists() else {}
        if official_full:
            baselines[method] = {
                "status": "complete",
                "seeds": seeds,
                "evidence_method": official_method,
                "evidence_file": audit_name,
                "checkpoint": official_audit.get("checkpoint"),
                "notes": f"Publication-grade {official_method} full-catalog records are present in the canonical cold JSONL files.",
            }
        elif official_present:
            baselines[method] = {
                "status": "partial",
                "seeds": seeds,
                "evidence_method": official_method,
                "evidence_file": audit_name if audit_path.exists() else None,
                "expected_seed_folds_per_dataset": expected_folds,
                "notes": f"{official_method} records are present but do not cover every frozen seed/fold.",
            }
        else:
            baselines[method] = {
                "status": "proxy_complete" if present else "not_run",
                "seeds": seeds,
                "notes": "Generated inside isolated lab; not an official publication-grade external implementation.",
            }
    for method in ["tiger_liger_retrieval", "lightgcn", "multivae", "ials"]:
        if method in baselines:
            continue
        audit_name = f"{method}_audit.json"
        audit_path = run_dir / audit_name
        method_audit = read_json(audit_path, {}) if audit_path.exists() else {}
        full_present = _all_datasets_have_full_method(cold, method, seeds)
        if method_audit.get("status") == "complete" and full_present:
            baselines[method] = {
                "status": "complete",
                "seeds": seeds,
                "evidence_file": audit_name,
                "notes": method_audit.get("notes", "Publication-grade baseline audit is present."),
            }
        elif method_audit.get("status") == "complete":
            baselines[method] = {
                "status": "partial",
                "seeds": seeds,
                "evidence_file": audit_name,
                "expected_seed_folds_per_dataset": expected_folds,
                "notes": "Audit reports complete, but canonical records do not cover every frozen seed/fold.",
            }
        else:
            baselines[method] = {"status": method_audit.get("status", "not_run"), "seeds": seeds}
    return {"schema_version": 1, "baselines": baselines}


def evaluate_gate(
    stage: str,
    warm: dict[str, Any],
    cold: dict[str, Any],
    sig: dict[str, Any],
    audit: dict[str, Any],
    config: dict[str, Any],
    seeds: list[int],
    bootstrap_reps: int,
    protocol: dict[str, Any],
) -> dict[str, Any]:
    failures = []
    protocol_id = protocol.get("protocol_id")
    if stage != "confirmatory":
        failures.append("Research/development stage cannot authorize publication claims.")
    ablation = config.get("frozen_config", {}).get("ablation")
    if ablation:
        role = ablation.get("publication_role", "diagnostic_ablation_only")
        if role != "publication_candidate":
            failures.append(
                f"Frozen config is an ablation ({ablation.get('ablation_id', 'unknown')}) "
                f"with publication_role={role}; diagnostic ablations cannot authorize publication claims."
            )
    if config.get("protocol", {}).get("protocol_id") != protocol_id:
        failures.append(f"Run was not created under frozen protocol {protocol_id}.")
    expected_seeds = [int(x) for x in protocol.get("fresh_confirmatory_seeds", [])]
    if stage == "confirmatory" and expected_seeds and list(seeds) != expected_seeds:
        failures.append(f"Confirmatory seeds {seeds} do not match frozen fresh seeds {expected_seeds}.")
    frozen_protocol = config.get("frozen_config", {}).get("protocol", {})
    frozen_seeds = [int(x) for x in frozen_protocol.get("fresh_confirmatory_seeds", [])]
    if frozen_seeds and frozen_seeds != expected_seeds:
        failures.append(f"Frozen candidate config seeds {frozen_seeds} do not match active fresh seeds {expected_seeds}.")
    if config.get("candidate_scope") != protocol.get("candidate_scope"):
        failures.append(f"Candidate scope is {config.get('candidate_scope')}, expected {protocol.get('candidate_scope')}.")
    ltr_config = config.get("frozen_config", {}).get("ltr_config", {})
    required_ltr = protocol.get("required_candidate_ltr_config", {})
    for key, expected in sorted(required_ltr.items()):
        if ltr_config.get(key) != expected:
            failures.append(f"Candidate LTR config {key}={ltr_config.get(key)} does not match required publication value {expected}.")
    if config.get("dropoutnet_feature_config") != OFFICIAL_DROPOUTNET_FEATURE_CONFIG:
        failures.append("Run config does not record the frozen DropoutNet feature config used by the candidate.")
    min_reps = int(protocol.get("minimum_bootstrap_reps", 0))
    if bootstrap_reps < min_reps:
        failures.append(f"Bootstrap used {bootstrap_reps} reps, below strict minimum {min_reps}.")
    required_datasets = list(protocol.get("datasets", DATASETS))
    expected_folds = expected_seed_fold_count(seeds)
    for dataset in required_datasets:
        if dataset not in cold:
            failures.append(f"{dataset} missing cold full-catalog results.")
            continue
        candidate_summary = cold.get(dataset, {}).get(LAB_CANDIDATE, {})
        if not candidate_summary.get("n_records"):
            failures.append(f"{dataset} missing candidate full-catalog records for {LAB_CANDIDATE}.")
        else:
            coverage_problems = record_coverage_problems(candidate_summary, dataset, seeds)
            if coverage_problems:
                missing = ", ".join(coverage_problems)
                failures.append(
                    f"{dataset} candidate {LAB_CANDIDATE} has incomplete exact record coverage: "
                    f"{int(candidate_summary.get('seed_fold_count', 0) or 0)}/{expected_folds} seed/folds; "
                    f"examples: {missing}."
                )
        ds_sig = sig["cold_full_catalog"].get(dataset, {})
        best = ds_sig.get("best_baseline")
        if not best:
            failures.append(f"{dataset} has no best baseline.")
            continue
        if float(ds_sig.get("candidate_ndcg10") or -1.0) <= float(ds_sig.get("best_baseline_ndcg10") or 0.0):
            failures.append(f"{dataset} {LAB_CANDIDATE} does not beat best baseline {best}.")
        best_comp = next((x for x in ds_sig.get("comparisons", []) if x.get("baseline") == best), {})
        if not best_comp.get("holm_significant"):
            failures.append(f"{dataset} {LAB_CANDIDATE} is not Holm-significant against {best}.")
        lc2c_comp = next((x for x in ds_sig.get("comparisons", []) if x.get("baseline") == "lc2c_v2"), {})
        if not lc2c_comp:
            failures.append(f"{dataset} missing paired significance comparison against LC2C V2.")
        elif not lc2c_comp.get("holm_significant"):
            failures.append(f"{dataset} {LAB_CANDIDATE} is not Holm-significant against LC2C V2.")
        for method in protocol.get("required_against_methods", []):
            if method == "lc2c_v2":
                continue
            comp = next((x for x in ds_sig.get("comparisons", []) if x.get("baseline") == method), {})
            if not comp:
                failures.append(f"{dataset} missing paired significance comparison against {method}.")
            elif not comp.get("holm_significant"):
                failures.append(f"{dataset} {LAB_CANDIDATE} is not Holm-significant against {method}.")
        boot = ds_sig.get("best_baseline_bootstrap", {})
        if boot.get("ci_lo_95") is None or float(boot["ci_lo_95"]) <= 0:
            failures.append(f"{dataset} clustered bootstrap lower CI is not above zero against {best}.")
    if "books" in warm:
        counts = warm["books"].get("fold_counts", {}).get("ease_sbert", [])
        if counts and min(counts) < DATASET_STATS["books"]["users"]:
            failures.append("Books warm-LOO is capped.")
    accepted_non_applicable: dict[str, Any] = {}
    non_applicable_cfg = protocol.get("documented_non_applicable_methods", {})
    for method in protocol.get("required_evidence_methods", []):
        entry = audit.get("baselines", {}).get(method, {})
        status = entry.get("status", "not_run")
        method_non_applicable = non_applicable_cfg.get(method)
        if method_non_applicable and status == method_non_applicable.get("allowed_status"):
            if not entry.get("evidence_file"):
                failures.append(f"Mandatory evidence method {method} is non-applicable but missing required audit evidence.")
            elif entry.get("evidence_file") != method_non_applicable.get("required_audit_file"):
                failures.append(
                    f"Mandatory evidence method {method} non-applicability audit is {entry.get('evidence_file')}, "
                    f"expected {method_non_applicable.get('required_audit_file')}."
                )
            else:
                accepted_non_applicable[method] = {
                    "status": status,
                    "evidence_file": entry.get("evidence_file"),
                    "claim_limitation": method_non_applicable.get("claim_limitation"),
                }
            continue
        if status != "complete":
            failures.append(f"Mandatory evidence method {method} is not publication-grade complete: status={status}.")
        for dataset in required_datasets:
            method_summary = cold.get(dataset, {}).get(method, {})
            if method_summary.get("n_records", 0) <= 0:
                failures.append(f"{dataset} missing full-catalog records for mandatory evidence method {method}.")
            else:
                coverage_problems = record_coverage_problems(method_summary, dataset, seeds)
                if coverage_problems:
                    missing = ", ".join(coverage_problems)
                    failures.append(
                        f"{dataset} mandatory evidence method {method} has incomplete exact record coverage: "
                        f"{int(method_summary.get('seed_fold_count', 0) or 0)}/{expected_folds} seed/folds; "
                        f"examples: {missing}."
                    )
    macro_c = [float(v.get("candidate_ndcg10") or 0.0) for v in sig["cold_full_catalog"].values()]
    macro_b = [float(v.get("best_baseline_ndcg10") or 0.0) for v in sig["cold_full_catalog"].values()]
    if macro_c and macro_b and np.mean(macro_c) <= np.mean(macro_b):
        failures.append(f"{LAB_CANDIDATE} does not beat best baseline macro-average.")
    return {
        "passed": not failures,
        "stage": stage,
        "checked_at_utc": utc_now(),
        "failures": failures,
        "standard": "strict frozen full-catalog cold-SOTA gate",
        "protocol_id": protocol_id,
        "accepted_non_applicable_methods": accepted_non_applicable,
    }


def build_tables(cold: dict[str, Any], warm: dict[str, Any], sig: dict[str, Any], gate: dict[str, Any], audit: dict[str, Any]) -> dict[str, Any]:
    rows = []
    sig_rows = []
    proxy_disallowed = set(LAB_PROTOCOL.get("proxy_methods_disallowed_for_publication", []))
    method_order = [
        *LAB_METHODS,
        "official_dropoutnet_fixed",
        "official_dropoutnet",
        "official_blair",
        "official_clcrec",
        "official_melt",
        "tiger_liger_retrieval",
    ]
    present_methods = []
    for method in method_order:
        if method in proxy_disallowed:
            continue
        if any(method in cold.get(dataset, {}) for dataset in DATASETS) and method not in present_methods:
            present_methods.append(method)
    for dataset_methods in cold.values():
        for method in sorted(dataset_methods):
            if method in proxy_disallowed:
                continue
            if method not in present_methods:
                present_methods.append(method)
    for dataset in DATASETS:
        methods = cold.get(dataset, {})
        rows.append([DATASET_LABELS[dataset], *[metric_fmt(methods.get(m, {}).get("NDCG@10")) for m in present_methods]])
        ds_sig = sig["cold_full_catalog"].get(dataset, {})
        best = ds_sig.get("best_baseline")
        best_comp = next((x for x in ds_sig.get("comparisons", []) if x.get("baseline") == best), {})
        boot = ds_sig.get("best_baseline_bootstrap", {})
        sig_rows.append([
            DATASET_LABELS[dataset],
            best or "-",
            metric_fmt(best_comp.get("mean_delta")),
            best_comp.get("marker", "n.s."),
            metric_fmt(boot.get("delta_point")),
            metric_fmt(boot.get("ci_lo_95")),
            metric_fmt(boot.get("ci_hi_95")),
        ])
    return {
        "schema_version": 1,
        "candidate": LAB_CANDIDATE,
        "sota_claim_allowed": gate["passed"],
        "sota_claim_scope": "algorithmic cold-item full-catalog gate only",
        "full_publication_reproducibility_approval": "requires strict clean rebuild and tracked/archive-pinned source tree",
        "publication_gate": gate,
        "baseline_audit": audit,
        "table_cold_full_catalog": {"columns": ["Dataset", *present_methods], "rows": rows},
        "table_significance": {
            "columns": ["Dataset", "Best baseline", "User mean delta", "Holm marker", "Cluster delta", "CI low", "CI high"],
            "rows": sig_rows,
        },
    }


def write_failure_report(run_dir: Path, gate: dict[str, Any], sig: dict[str, Any]) -> None:
    lines = ["# Internal SOTA Failure Report", "", f"Run directory: `{run_dir}`", f"Generated: {utc_now()}", "", "## Decision", "", "Reject for SOTA/publication claims.", "", "## Failures", ""]
    lines.extend(f"- {x}" for x in gate.get("failures", []))
    lines.extend(["", "## Summary", ""])
    for dataset, block in sig.get("cold_full_catalog", {}).items():
        lines.append(f"- {dataset}: {LAB_CANDIDATE}={metric_fmt(block.get('candidate_ndcg10'))}, best={block.get('best_baseline')} ({metric_fmt(block.get('best_baseline_ndcg10'))})")
    (run_dir / "INTERNAL_SOTA_FAILURE_REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    if (run_dir / "SOTA_PASS_REPORT.md").exists():
        revoked = [
            "# SOTA Pass Report Revoked",
            "",
            f"Generated: {utc_now()}",
            "",
            "The strict publication gate failed. Any earlier pass decision for this run is revoked.",
            "",
            "## Failures",
            "",
            *[f"- {x}" for x in gate.get("failures", [])],
        ]
        (run_dir / "SOTA_PASS_REPORT.md").write_text("\n".join(revoked), encoding="utf-8")


def remove_stale_failure_report(run_dir: Path) -> None:
    for name in ["INTERNAL_SOTA_FAILURE_REPORT.md", "SOTA_PASS_REPORT.md"]:
        path = run_dir / name
        if path.exists():
            path.unlink()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--bootstrap-reps", type=int, default=int(LAB_PROTOCOL.get("minimum_bootstrap_reps", 2000)))
    args = parser.parse_args()
    run_dir = RUNS_DIR / args.run_id
    config = read_json(run_dir / "run_config.json")
    datasets = config.get("datasets", list(DATASETS))
    seeds = [int(x) for x in config.get("seeds", [])]
    stage = config.get("stage", "research")
    cold: dict[str, Any] = {}
    user_means: dict[str, Any] = {}
    for dataset in datasets:
        path = run_dir / f"cold_full_catalog_records_{dataset}.jsonl"
        if path.exists():
            cold[dataset], user_means[dataset] = summarize_cold_dataset(path, dataset)
    warm: dict[str, Any] = {}
    for dataset in datasets:
        path = run_dir / f"warm_records_{dataset}.jsonl"
        if path.exists():
            warm[dataset] = summarize_warm_dataset(path, dataset)
    sig = build_significance(run_dir, cold, user_means, args.bootstrap_reps)
    audit = baseline_audit(cold, seeds, run_dir)
    gate = evaluate_gate(stage, warm, cold, sig, audit, config, seeds, args.bootstrap_reps, LAB_PROTOCOL)
    tables = build_tables(cold, warm, sig, gate, audit)
    payload = {"schema_version": 1, "run_id": args.run_id, "stage": stage, "warm": warm, "cold_full_catalog": cold, "publication_gate": gate}
    write_json(run_dir / "results_final.json", payload)
    write_json(run_dir / "significance.json", sig)
    write_json(run_dir / "baseline_audit.json", audit)
    write_json(run_dir / "publication_gate.json", gate)
    write_json(run_dir / "tables.json", tables)
    if not gate["passed"]:
        write_failure_report(run_dir, gate, sig)
    else:
        remove_stale_failure_report(run_dir)
    write_manifest(
        run_dir,
        ["python", "_bestrec_sota_lab/finalize.py", "--run-id", args.run_id, "--bootstrap-reps", str(args.bootstrap_reps)],
        datasets,
        seeds,
        [run_dir / name for name in ["results_final.json", "significance.json", "baseline_audit.json", "publication_gate.json", "tables.json", "INTERNAL_SOTA_FAILURE_REPORT.md"] if (run_dir / name).exists()],
        f"finalized isolated SOTA lab run; gate_passed={gate['passed']}",
    )
    print(f"Finalized {run_dir}")
    print("Gate:", "PASSED" if gate["passed"] else "FAILED")
    for failure in gate.get("failures", [])[:12]:
        print("-", failure)
    return 0 if gate["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
