#!/usr/bin/env python3
"""First authorized endpoint reader and mechanical adjudicator for E-E V3."""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy import stats

import ee_v3_common as common


METRIC_KEYS = ({"n_eval", "MRR", "eval_seconds", "users_per_second",
                "cuda_peak_allocated_bytes", "profiler_probe_users",
                "profiler_accounted_flops_total",
                "profiler_accounted_flops_per_user", "profiler_scope"}
               | {f"{metric}@{cutoff}" for metric in ("HR", "NDCG", "MRR")
                  for cutoff in (5, 10, 20, 50)})
ENDPOINT_KEYS = {
    "arm", "checkpoint_file", "checkpoint_sha256", "completed_utc", "environment",
    "evaluator", "metrics", "model_type", "protocol", "ready_file", "ready_sha256",
    "repository_commit", "seal_file", "seal_sha256", "seed", "selected_epoch",
    "sidecar_file", "sidecar_sha256", "state", "test_data_sha256", "training_file",
    "training_sha256", "upstream_commit",
}


def fail(message: str) -> None:
    raise RuntimeError(message)


def normalized_lf_sha256(path: Path) -> str:
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def mean_sd_ci(values: list[float]) -> dict[str, object]:
    x = np.asarray(values, dtype=np.float64)
    if x.ndim != 1 or len(x) < 2 or not np.isfinite(x).all():
        fail("invalid seed vector")
    mean = float(x.mean())
    sd = float(x.std(ddof=1))
    half = float(stats.t.ppf(0.975, len(x) - 1) * sd / math.sqrt(len(x)))
    return {"n": int(len(x)), "vector": x.tolist(), "mean": mean, "sd": sd,
            "ci95": [mean - half, mean + half]}


def welch(a: list[float], b: list[float]) -> dict[str, object]:
    x = np.asarray(a, dtype=np.float64)
    y = np.asarray(b, dtype=np.float64)
    vx, vy = x.var(ddof=1), y.var(ddof=1)
    se2 = vx / len(x) + vy / len(y)
    if se2 <= 0 or not math.isfinite(float(se2)):
        fail("degenerate Welch contrast")
    df = float(se2 * se2 / ((vx / len(x)) ** 2 / (len(x) - 1)
                            + (vy / len(y)) ** 2 / (len(y) - 1)))
    delta = float(x.mean() - y.mean())
    half = float(stats.t.ppf(0.975, df) * math.sqrt(se2))
    lo, hi = delta - half, delta + half
    p = float(2.0 * stats.t.sf(abs(delta / math.sqrt(se2)), df))
    direction = "ABOVE" if lo > 0 else "BELOW" if hi < 0 else "OVERLAP"
    return {"estimand": "first arm minus second arm", "delta": delta,
            "ci95": [lo, hi], "welch_df": df, "p_two_sided_unadjusted": p,
            "direction": direction,
            "inference_boundary": "descriptive independent-arm Welch on optimizer-seed estimates"}


def bootstrap_ci(effect: np.ndarray, targets: np.ndarray) -> dict[str, object]:
    if (effect.shape != (common.N_USERS,) or targets.shape != (common.N_USERS,)
            or not np.isfinite(effect).all()):
        fail("bootstrap input schema mismatch")
    rng = np.random.default_rng(common.BOOTSTRAP_SEED)
    user_draws = np.empty(common.N_BOOTSTRAP, dtype=np.float64)
    for start in range(0, common.N_BOOTSTRAP, 40):
        stop = min(start + 40, common.N_BOOTSTRAP)
        idx = rng.integers(0, common.N_USERS,
                           size=(stop - start, common.N_USERS), dtype=np.int64)
        user_draws[start:stop] = effect[idx].mean(axis=1)

    unique, inverse = np.unique(targets, return_inverse=True)
    sums = np.bincount(inverse, weights=effect).astype(np.float64)
    counts = np.bincount(inverse).astype(np.float64)
    cluster_draws = np.empty(common.N_BOOTSTRAP, dtype=np.float64)
    n_clusters = len(unique)
    for start in range(0, common.N_BOOTSTRAP, 80):
        stop = min(start + 80, common.N_BOOTSTRAP)
        idx = rng.integers(0, n_clusters,
                           size=(stop - start, n_clusters), dtype=np.int64)
        cluster_draws[start:stop] = sums[idx].sum(axis=1) / counts[idx].sum(axis=1)
    return {
        "estimand": "mean over users of eight-seed AlphaFuse NDCG@10 minus eight-seed ID NDCG@10",
        "point_estimate": float(effect.mean()),
        "replicates": common.N_BOOTSTRAP,
        "rng_seed": common.BOOTSTRAP_SEED,
        "user_resample_percentile_ci95": np.quantile(user_draws, [0.025, 0.975]).tolist(),
        "target_item_cluster_resample_percentile_ci95": np.quantile(
            cluster_draws, [0.025, 0.975]).tolist(),
        "n_target_item_clusters": int(n_clusters),
        "boundary": "fixed-split sensitivity only; not optimizer or population inference",
    }


def verify_reference() -> tuple[list[float], dict[str, str]]:
    vector: list[float] = []
    hashes: dict[str, str] = {}
    for name in common.REFERENCE_FILES:
        path = common.HERE / name
        expected = common.REFERENCE_RAW_SHA256[name]
        if not path.is_file() or (common.sha256(path) != expected
                                  and normalized_lf_sha256(path) != expected):
            fail(f"paper reference identity mismatch: {name}")
        value = common.load_json(path)
        try:
            score = float(value["best_test"]["NDCG@10"])
            n_eval = int(value["best_test"]["n_eval"])
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError(f"paper reference schema mismatch: {name}") from exc
        if not math.isfinite(score) or n_eval != common.N_USERS:
            fail(f"paper reference value mismatch: {name}")
        vector.append(score)
        hashes[name] = expected
    return vector, hashes


def load_endpoint(arm: str, seed: int, ready: dict[str, object], ready_sha: str
                  ) -> tuple[dict[str, object], dict[str, np.ndarray]]:
    endpoint_path = common.endpoint_path(arm, seed)
    sidecar_path = common.endpoint_users_path(arm, seed)
    seal_path = common.endpoint_seal_path(arm, seed)
    if not endpoint_path.is_file() or not sidecar_path.is_file() or not seal_path.is_file():
        fail(f"incomplete sealed endpoint bundle: {arm}/{seed}")
    obj = common.load_json(endpoint_path)
    if set(obj) != ENDPOINT_KEYS:
        fail(f"endpoint schema drift: {arm}/{seed}")
    train = common.validate_training_bundle(
        arm, seed, expected_commit=str(ready["repository_commit"]))
    seal = common.load_json(seal_path)
    if (set(seal) != {"arm", "checkpoint_sha256", "protocol", "ready_sha256",
                     "repository_commit", "seed", "started_utc", "state",
                     "training_sha256"}
            or seal["protocol"] != common.PROTOCOL
            or seal["state"] != "sealed_test_attempt_started"
            or seal["arm"] != arm or seal["seed"] != seed
            or seal["repository_commit"] != ready["repository_commit"]
            or seal["ready_sha256"] != ready_sha):
        fail(f"TEST seal identity drift: {arm}/{seed}")
    if (obj["protocol"] != common.PROTOCOL
            or obj["state"] != "assessment_complete_sealed"
            or obj["arm"] != arm or obj["seed"] != seed
            or obj["model_type"] != common.MODEL_TYPES[arm]
            or obj["repository_commit"] != ready["repository_commit"]
            or obj["upstream_commit"] != common.UPSTREAM_COMMIT
            or obj["ready_file"] != common.READY.name
            or obj["ready_sha256"] != ready_sha
            or obj["seal_file"] != seal_path.name
            or obj["seal_sha256"] != common.sha256(seal_path)
            or obj["training_file"] != common.training_path(arm, seed).name
            or obj["training_sha256"] != common.sha256(common.training_path(arm, seed))
            or obj["checkpoint_file"] != common.best_path(arm, seed).name
            or obj["checkpoint_sha256"] != common.sha256(common.best_path(arm, seed))
            or obj["selected_epoch"] != train["best_epoch"]
            or obj["test_data_sha256"] != common.DATA_HASHES["test_data.df"]
            or obj["evaluator"] != {
                "candidate_set": f"all {common.N_ITEMS} items",
                "model_input": "most recent 50 TRAIN+VALID interactions",
                "mask": "complete TRAIN+VALID history; target exception",
                "ties": "strict-greater",
                "rank_definition": "rank0=count(eligible_score > target_score)",
            }
            or obj["sidecar_file"] != sidecar_path.name
            or obj["sidecar_sha256"] != common.sha256(sidecar_path)):
        fail(f"endpoint identity drift: {arm}/{seed}")
    metrics = obj["metrics"]
    if not isinstance(metrics, dict) or set(metrics) != METRIC_KEYS:
        fail(f"endpoint metric schema drift: {arm}/{seed}")
    for key, value in metrics.items():
        if key != "profiler_scope" and not math.isfinite(float(value)):
            fail(f"non-finite endpoint metric {key}: {arm}/{seed}")
    if int(metrics["n_eval"]) != common.N_USERS:
        fail(f"endpoint user count mismatch: {arm}/{seed}")
    if (int(metrics["profiler_probe_users"]) != 64
            or int(metrics["profiler_accounted_flops_total"]) <= 0
            or float(metrics["eval_seconds"]) <= 0
            or float(metrics["users_per_second"]) <= 0
            or int(metrics["cuda_peak_allocated_bytes"]) <= 0):
        fail(f"endpoint resource record invalid: {arm}/{seed}")

    with np.load(sidecar_path, allow_pickle=False) as z:
        if set(z.files) != {"user_index", "target_item_id", "rank0", "ndcg10", "hr10", "rr"}:
            fail(f"sidecar schema drift: {arm}/{seed}")
        arrays = {name: z[name].copy() for name in z.files}
    if (arrays["user_index"].tolist() != list(range(common.N_USERS))
            or arrays["target_item_id"].shape != (common.N_USERS,)
            or arrays["rank0"].shape != (common.N_USERS,)
            or arrays["rank0"].min() < 0 or arrays["rank0"].max() >= common.N_ITEMS):
        fail(f"sidecar geometry drift: {arm}/{seed}")
    reconstructed = common.metric_family(arrays["rank0"])
    for key, value in reconstructed.items():
        if not math.isclose(float(metrics[key]), float(value), rel_tol=0.0, abs_tol=1e-12):
            fail(f"rank reconstruction mismatch {key}: {arm}/{seed}")
    rank = arrays["rank0"].astype(np.float64)
    expected_ndcg = np.where(rank < 10, 1.0 / np.log2(rank + 2.0), 0.0)
    if (not np.array_equal(arrays["hr10"], (rank < 10).astype(np.int8))
            or not np.allclose(arrays["ndcg10"], expected_ndcg, rtol=0.0, atol=0.0)
            or not np.allclose(arrays["rr"], 1.0 / (rank + 1.0), rtol=0.0, atol=0.0)):
        fail(f"sidecar derived arrays mismatch: {arm}/{seed}")
    return obj, arrays


def main() -> int:
    if common.ADJUDICATION.exists():
        fail("refusing to overwrite existing E-E V3 adjudication")
    status = common.load_json(common.STATUS)
    expected_status_values = {
        "protocol": common.PROTOCOL,
        "state": "endpoints_complete_adjudicating",
        "repository_commit": common.repository_head(),
        "training_complete": 16,
        "assessment_complete": 16,
        "total": 16,
        "errors": [],
    }
    for key, value in expected_status_values.items():
        if status.get(key) != value:
            fail(f"campaign status is not adjudication-ready: {key}")
    if set(status) != set(expected_status_values) | {"updated_utc"}:
        fail("campaign status schema drift")
    ready = common.load_json(common.READY)
    if ready != common.ready_payload():
        fail("READY record drift before first endpoint read")
    ready_sha = common.sha256(common.READY)

    endpoints: dict[str, dict[int, dict[str, object]]] = {arm: {} for arm in common.ARMS}
    records: dict[str, dict[int, dict[str, np.ndarray]]] = {arm: {} for arm in common.ARMS}
    ledger: list[dict[str, object]] = []
    for arm, seed in common.expected_pairs():
        endpoint, sidecar = load_endpoint(arm, seed, ready, ready_sha)
        endpoints[arm][seed] = endpoint
        records[arm][seed] = sidecar
        ledger.append({"arm": arm, "seed": seed,
                       "endpoint_file": common.endpoint_path(arm, seed).name,
                       "endpoint_sha256": common.sha256(common.endpoint_path(arm, seed)),
                       "sidecar_file": common.endpoint_users_path(arm, seed).name,
                       "sidecar_sha256": common.sha256(common.endpoint_users_path(arm, seed))})

    family = {}
    for arm in common.ARMS:
        family[arm] = {}
        for metric in ("NDCG@10", "HR@10", "MRR"):
            family[arm][metric] = mean_sd_ci([
                float(endpoints[arm][seed]["metrics"][metric]) for seed in common.SEEDS])

    alpha = family["alphafuse_package"]["NDCG@10"]["vector"]
    identity = family["sasrec_id"]["NDCG@10"]["vector"]
    reference, reference_hashes = verify_reference()
    contrast_id = welch(alpha, identity)
    contrast_reference = welch(alpha, reference)

    alpha_users = np.stack([records["alphafuse_package"][seed]["ndcg10"]
                            for seed in common.SEEDS]).mean(axis=0)
    id_users = np.stack([records["sasrec_id"][seed]["ndcg10"]
                         for seed in common.SEEDS]).mean(axis=0)
    targets = records["alphafuse_package"][common.SEEDS[0]]["target_item_id"]
    for arm in common.ARMS:
        for seed in common.SEEDS:
            if not np.array_equal(records[arm][seed]["target_item_id"], targets):
                fail("target-item vectors differ across endpoint sidecars")
    sensitivity = bootstrap_ci(alpha_users - id_users, targets)

    resources = {}
    for arm in common.ARMS:
        resources[arm] = {}
        resource_fields = {
            "total_params": [common.load_json(common.training_path(arm, s))["total_params"]
                             for s in common.SEEDS],
            "trainable_params": [common.load_json(common.training_path(arm, s))["trainable_params"]
                                 for s in common.SEEDS],
            "training_wall_seconds": [common.load_json(common.training_path(arm, s))["training_wall_seconds"]
                                      for s in common.SEEDS],
            "selected_epoch": [endpoints[arm][s]["selected_epoch"] for s in common.SEEDS],
            "eval_seconds": [endpoints[arm][s]["metrics"]["eval_seconds"] for s in common.SEEDS],
            "users_per_second": [endpoints[arm][s]["metrics"]["users_per_second"] for s in common.SEEDS],
            "cuda_peak_allocated_bytes": [endpoints[arm][s]["metrics"]["cuda_peak_allocated_bytes"]
                                           for s in common.SEEDS],
            "profiler_accounted_flops_per_user": [
                endpoints[arm][s]["metrics"]["profiler_accounted_flops_per_user"]
                for s in common.SEEDS],
        }
        for key, values in resource_fields.items():
            resources[arm][key] = {"vector": values,
                                   "median": float(np.median(np.asarray(values, dtype=np.float64)))}

    output = {
        "protocol": common.PROTOCOL,
        "classification": "PROSPECTIVELY_FROZEN_OUTCOME_KNOWN_SAME_INVESTIGATOR_EXPLORATORY",
        "countable_as_current_comparator": True,
        "independent_confirmation": False,
        "general_sota_claim_allowed": False,
        "verdict": "EEV3-REPORTABLE-OUTCOME-KNOWN",
        "repository_commit": ready["repository_commit"],
        "upstream_commit": common.UPSTREAM_COMMIT,
        "arms": list(common.ARMS),
        "seeds": list(common.SEEDS),
        "ready_sha256": ready_sha,
        "endpoint_ledger": ledger,
        "arm_seed_summaries": family,
        "contrasts": {
            "alphafuse_package_minus_sasrec_id": contrast_id,
            "alphafuse_package_minus_existing_paper_reference": contrast_reference,
        },
        "existing_paper_reference": {
            "files_sha256": reference_hashes,
            "NDCG@10": mean_sd_ci(reference),
        },
        "fixed_dataset_sensitivity": sensitivity,
        "resources": resources,
        "resource_scope": "profiler FLOPs are operator-accounted forward-plus-full-catalog-score lower bounds",
        "claim_boundary": (
            "Prospectively frozen but outcome-known same-investigator execution; AlphaFuse-style "
            "MiniLM representation package versus its repository SASRec ID backbone under shared "
            "data and complete-history-masked evaluator. Architectures, text availability, "
            "initialization, trainable capacity, and parameter allocation are not equalized. "
            "This is not independent confirmation, an isolation of null-space fusion, equal-"
            "tuning evidence, or a general SOTA claim."
        ),
        "completed_utc": common.utc_now(),
    }
    common.exclusive_json(common.ADJUDICATION, output)
    print(json.dumps({
        "verdict": output["verdict"],
        "alphafuse_minus_sasrec_id": contrast_id,
        "alphafuse_minus_existing_paper_reference": contrast_reference,
        "adjudication_sha256": common.sha256(common.ADJUDICATION),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"E-E V3 ADJUDICATION FAILURE: {exc}", file=sys.stderr, flush=True)
        raise
