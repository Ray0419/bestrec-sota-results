# -*- coding: utf-8 -*-
"""Mechanical first endpoint reader for ML1M FIR efficiency V1."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
from scipy import stats
import torch

import run_fir_efficiency_ml1m_v1 as campaign


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PROTOCOL = campaign.PROTOCOL
ALPHA = 0.05
MARGIN = 0.0005
BOOTSTRAP_REPS = 10000
BOOTSTRAP_SEED = 20261190
PRIMARY = campaign.PRIMARY_CATEGORY
IDENTITY = "identity"
LEARNED = "learned"
POINTWISE = "pointwise"
CANDIDATES = ("shared", "grouped", "lowrank")
EXPECTED_FILTER_PARAMS = {
    "identity": 0,
    "shared": 16,
    "grouped": 128,
    "lowrank": 320,
    "learned": 1024,
    "pointwise": 1024,
}
FROZEN_FILES = {
    "trainer": "_bestrec_run/run_sasrec_sbert_efficiency_ml1m_v1_frozen.py",
    "evaluator": "_bestrec_run/eval_fir_efficiency_ml1m_v1.py",
    "runner": "_bestrec_run/run_fir_efficiency_ml1m_v1.py",
    "structural_test": "_bestrec_run/test_fir_efficiency_v1.py",
    "sequestration_test": "_bestrec_run/test_fir_efficiency_sequestration_v1.py",
    "acquisition": "_bestrec_run/acquire_movielens_fir_efficiency_v1.py",
    "preregistration": "PREREG_FIR_EFFICIENCY_ML1M_V1.md",
}
# Filled only in the final freeze commit, before acquisition or training.
FROZEN_SHA256_LF = {
    "trainer": "f15d3912603c976f8600bf12dfc780536a0cddb1504e39409891fb072066fd56",
    "evaluator": "fb431bf40e714c668a106276142858dfd5939e89a54b1dacee75c9f0e75ecffd",
    "runner": "205ca48bc567f72acb3efb816d1c8deddf58d56127324da2958dfaad31713c39",
    "structural_test": "106dfc040933d1756c8696c3e6c8a3bb3993de7056ddf5e035316880f76ade59",
    "sequestration_test": "ceb730569d749f627f461f98a731b84653a9cea731acfcbcd5cc1a43e924c47c",
    "acquisition": "c76d33616e93a46ea937f84762fa3293892ea698ab5be249fc1361ab31e6a47c",
    "preregistration": "866f682019a9936ca16ff53a3bbb16465f639aad54c112b6d23d679e48e6021c",
}


def die(message):
    raise RuntimeError("INTEGRITY FAIL: " + message)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def sha256_lf(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def paired(x, y, confidence=0.95):
    difference = np.asarray(x, dtype=float) - np.asarray(y, dtype=float)
    n = len(difference)
    mean = float(difference.mean())
    sd = float(difference.std(ddof=1))
    se = sd / math.sqrt(n)
    if se == 0:
        statistic = math.copysign(math.inf, mean) if mean else 0.0
        p = 0.0 if mean else 1.0
        interval = (mean, mean)
    else:
        statistic = mean / se
        p = float(2.0 * stats.t.sf(abs(statistic), n - 1))
        quantile = float(stats.t.ppf((1.0 + confidence) / 2.0, n - 1))
        interval = (mean - quantile * se, mean + quantile * se)
    return {
        "mean": mean,
        "sd": sd,
        "t": statistic,
        "df": n - 1,
        "p_two_sided": p,
        "ci": [float(interval[0]), float(interval[1])],
        "confidence": confidence,
        "per_seed": [float(value) for value in difference],
    }


def noninferiority(candidate, reference):
    difference = np.asarray(candidate, dtype=float) - np.asarray(reference, dtype=float)
    n = len(difference)
    mean = float(difference.mean())
    sd = float(difference.std(ddof=1))
    se = sd / math.sqrt(n)
    if se == 0:
        statistic = math.inf if mean > -MARGIN else -math.inf
        p = 0.0 if mean > -MARGIN else 1.0
    else:
        statistic = (mean + MARGIN) / se
        p = float(stats.t.sf(statistic, n - 1))
    # Simultaneous one-sided Bonferroni lower confidence bound for 3 candidates.
    family_confidence = 1.0 - ALPHA / len(CANDIDATES)
    quantile = float(stats.t.ppf(family_confidence, n - 1))
    lower = mean - quantile * se if se else mean
    return {
        "mean": mean,
        "sd": sd,
        "t_margin": statistic,
        "df": n - 1,
        "p_one_sided": p,
        "margin": MARGIN,
        "simultaneous_lower": float(lower),
        "simultaneous_confidence": family_confidence,
        "per_seed": [float(value) for value in difference],
    }


def holm(raw):
    ordered = sorted(raw, key=raw.get)
    running = 0.0
    adjusted = {}
    for index, name in enumerate(ordered):
        running = max(running, (len(ordered) - index) * raw[name])
        adjusted[name] = min(1.0, running)
    return {name: {
        "p_raw": float(raw[name]),
        "p_holm": float(adjusted[name]),
        "reject": bool(adjusted[name] < ALPHA),
    } for name in raw}


def percentile_interval(values):
    return [float(np.quantile(values, 0.025)),
            float(np.quantile(values, 0.975))]


def cluster_sensitivities(candidate_records, reference_records):
    # Inputs are seed -> {user_id,target_item_id,ndcg10}. Every arm must have
    # exactly the same ordered user/target keys within each seed.
    seed_order = list(campaign.SEEDS)
    user_keys = None
    per_seed_difference = []
    for seed in seed_order:
        candidate = candidate_records[seed]
        reference = reference_records[seed]
        keys = np.stack([candidate["user_id"], candidate["target_item_id"]], axis=1)
        reference_keys = np.stack(
            [reference["user_id"], reference["target_item_id"]], axis=1)
        if not np.array_equal(keys, reference_keys):
            die(f"per-user key mismatch for cluster sensitivity seed {seed}")
        if user_keys is None:
            user_keys = keys
        elif not np.array_equal(user_keys, keys):
            die("per-user key order differs across seeds")
        per_seed_difference.append(
            candidate["ndcg10"].astype(float)
            - reference["ndcg10"].astype(float))
    per_user = np.mean(np.stack(per_seed_difference, axis=0), axis=0)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    user_boot = np.empty(BOOTSTRAP_REPS, dtype=float)
    for index in range(BOOTSTRAP_REPS):
        draw = rng.integers(0, len(per_user), len(per_user))
        user_boot[index] = per_user[draw].mean()

    item_ids = user_keys[:, 1]
    unique_items = np.unique(item_ids)
    item_means = np.asarray([
        per_user[item_ids == item].mean() for item in unique_items], dtype=float)
    item_boot = np.empty(BOOTSTRAP_REPS, dtype=float)
    for index in range(BOOTSTRAP_REPS):
        draw = rng.integers(0, len(item_means), len(item_means))
        item_boot[index] = item_means[draw].mean()
    return {
        "user_weighted_mean": float(per_user.mean()),
        "user_cluster_percentile_ci95": percentile_interval(user_boot),
        "n_users": int(len(per_user)),
        "item_macro_mean": float(item_means.mean()),
        "item_cluster_percentile_ci95": percentile_interval(item_boot),
        "n_target_items": int(len(item_means)),
        "bootstrap_repetitions": BOOTSTRAP_REPS,
        "bootstrap_seed": BOOTSTRAP_SEED,
    }


def normalized_config(config):
    return {key: value for key, value in config.items()
            if key not in {"category", "fir_control", "seed", "out", "split_dir"}}


def verify_frozen():
    for role, relative in FROZEN_FILES.items():
        expected = FROZEN_SHA256_LF[role]
        if expected == "FILL_BEFORE_FREEZE":
            die("frozen digests have not been filled")
        actual = sha256_lf(ROOT / relative)
        if actual != expected:
            die(f"frozen {role} digest mismatch: {actual}")


def main():
    if "--verify-freeze" in sys.argv:
        verify_frozen()
        print("FIR EFFICIENCY ML1M V1 FROZEN HASHES: PASS")
        return 0
    status = json.loads(campaign.STATUS.read_text(encoding="utf-8"))
    expected_total = len(campaign.CATEGORIES) * len(campaign.ARMS) * len(campaign.SEEDS)
    if (status.get("protocol") != PROTOCOL
            or status.get("state") != "complete"
            or status.get("trained", 0) + status.get("skipped_train", 0) != expected_total
            or status.get("evaluated", 0) + status.get("skipped_eval", 0) != expected_total):
        die("campaign status is not complete for all training/evaluation runs")
    if status.get("adjudicator_sha256_lf") != sha256_lf(Path(__file__)):
        die("adjudicator differs from the pre-outcome driver-bound reader")
    verify_frozen()

    values = {category: {arm: {} for arm in campaign.ARMS}
              for category in campaign.CATEGORIES}
    records = {category: {arm: {} for arm in campaign.ARMS}
               for category in campaign.CATEGORIES}
    resources = {category: {arm: {} for arm in campaign.ARMS}
                 for category in campaign.CATEGORIES}
    backbone = {category: {seed: {} for seed in campaign.SEEDS}
                for category in campaign.CATEGORIES}
    split_hashes = {category: None for category in campaign.CATEGORIES}
    normalized = None
    missing = []

    for category in campaign.CATEGORIES:
        for seed in campaign.SEEDS:
            for arm in campaign.ARMS:
                paths = campaign.artifacts_for(category, arm, seed)
                absent = [path.name for path in paths.values() if not path.exists()]
                if absent:
                    missing.extend(absent)
                    continue
                base = json.loads(paths["run"].read_text(encoding="utf-8"))
                final = json.loads(paths["final"].read_text(encoding="utf-8"))
                config = base["config"]
                if (config.get("category") != category
                        or config.get("seed") != seed
                        or config.get("epochs") != 20
                        or config.get("fir_control") != arm
                        or config.get("fir_control_kernel") != campaign.KERNEL
                        or config.get("fir_control_groups") != campaign.GROUPS
                        or config.get("fir_control_rank") != campaign.RANK
                        or config.get("fir_v3") != "off"
                        or config.get("causal_filter")
                        or not config.get("no_test_eval")
                        or not config.get("sequester_test_load")
                        or not config.get("save_ckpt")
                        or not config.get("no_sbert")
                        or not config.get("chunked_full_softmax")
                        or config.get("label_smoothing") != 0.2):
                    die(f"frozen config mismatch in {paths['run'].name}")
                current_normalized = normalized_config(config)
                if normalized is None:
                    normalized = current_normalized
                elif current_normalized != normalized:
                    die(f"non-arm/non-seed config differs in {paths['run'].name}")
                if base.get("best_test") is not None or any(
                        "test" in row for row in base.get("history", [])):
                    die(f"training accessed TEST in {paths['run'].name}")
                provenance = base.get("provenance", {})
                if provenance.get("git_dirty_tracked"):
                    die(f"training used tracked-dirty checkout in {paths['run'].name}")
                if (provenance.get("data_sha256", {}).get("test_csv") is not None
                        or provenance.get("n_interactions", {}).get("test") != 0):
                    die(f"training touched or loaded TEST in {paths['run'].name}")
                if base.get("best_ckpt_sha256") != sha256(paths["checkpoint"]):
                    die(f"checkpoint digest mismatch in {paths['run'].name}")
                if base.get("fir_control_trainable_params") != EXPECTED_FILTER_PARAMS[arm]:
                    die(f"filter parameter count mismatch in {paths['run'].name}")
                if arm == IDENTITY and base.get("fir_control_final_l2") != 0.0:
                    die(f"identity taps moved in {paths['run'].name}")
                if arm != IDENTITY and not (base.get("fir_control_final_l2", 0.0) > 0.0):
                    die(f"active filter did not move in {paths['run'].name}")
                backbone[category][seed][arm] = base.get("backbone_init_sha256")

                if (final.get("protocol") != PROTOCOL
                        or final.get("category") != category
                        or final.get("seed") != seed
                        or final.get("arm") != arm):
                    die(f"final binding mismatch in {paths['final'].name}")
                final_provenance = final.get("provenance", {})
                expected_bindings = {
                    "run_json_sha256": sha256(paths["run"]),
                    "checkpoint_sha256": sha256(paths["checkpoint"]),
                    "started_seal_sha256": sha256(paths["seal"]),
                    "users_sidecar_sha256": sha256(paths["users"]),
                    "trainer_sha256_lf": FROZEN_SHA256_LF["trainer"],
                    "evaluator_sha256_lf": FROZEN_SHA256_LF["evaluator"],
                }
                for key, expected in expected_bindings.items():
                    if final_provenance.get(key) != expected:
                        die(f"{key} mismatch in {paths['final'].name}")
                current_splits = tuple(final_provenance.get(key) for key in (
                    "train_split_sha256", "valid_split_sha256", "test_split_sha256"))
                if split_hashes[category] is None:
                    split_hashes[category] = current_splits
                elif split_hashes[category] != current_splits:
                    die(f"split digest differs across {category} runs")

                metric = final.get("test", {}).get("NDCG@10")
                if metric is None or not np.isfinite(metric):
                    die(f"missing/nonfinite endpoint in {paths['final'].name}")
                with np.load(paths["users"]) as sidecar:
                    record = {key: sidecar[key].copy() for key in sidecar.files}
                if len(record["ndcg10"]) != final["test"].get("n_eval"):
                    die(f"per-user row count mismatch in {paths['users'].name}")
                if not np.isclose(record["ndcg10"].mean(), metric, atol=1e-12):
                    die(f"per-user endpoint mismatch in {paths['users'].name}")
                efficiency = final.get("efficiency", {})
                required_efficiency = (
                    "latency_ms_median", "latency_ms_p95", "flops_per_user",
                    "peak_cuda_memory_bytes")
                if any(efficiency.get(key) is None
                       or not np.isfinite(efficiency[key])
                       for key in required_efficiency):
                    die(f"missing/nonfinite efficiency measure in {paths['final'].name}")

                values[category][arm][seed] = float(metric)
                records[category][arm][seed] = record
                resources[category][arm][seed] = {
                    **efficiency,
                    **final["model"],
                }

    if missing:
        print(f"NOT READY: {len(missing)} required private artifact(s) missing")
        for name in missing[:12]:
            print("  -", name)
        return 3
    for category in campaign.CATEGORIES:
        for seed, hashes in backbone[category].items():
            if None in hashes.values() or len(set(hashes.values())) != 1:
                die(f"{category} seed {seed} lacks a shared backbone init: {hashes}")

    vectors = {category: {
        arm: [values[category][arm][seed] for seed in campaign.SEEDS]
        for arm in campaign.ARMS} for category in campaign.CATEGORIES}
    primary_vectors = vectors[PRIMARY]
    replication = {
        "learned-identity": paired(primary_vectors[LEARNED], primary_vectors[IDENTITY]),
        "learned-pointwise": paired(primary_vectors[LEARNED], primary_vectors[POINTWISE]),
    }
    replication_holm = holm({
        name: result["p_two_sided"] for name, result in replication.items()})
    replication_positive = {
        name: bool(result["mean"] > 0 and result["ci"][0] > 0
                   and replication_holm[name]["reject"])
        for name, result in replication.items()
    }

    noninferiority_results = {
        candidate: noninferiority(primary_vectors[candidate], primary_vectors[LEARNED])
        for candidate in CANDIDATES
    }
    noninferiority_holm = holm({
        candidate: result["p_one_sided"]
        for candidate, result in noninferiority_results.items()})
    noninferiority_pass = {
        candidate: bool(
            result["simultaneous_lower"] > -MARGIN
            and noninferiority_holm[candidate]["reject"])
        for candidate, result in noninferiority_results.items()
    }
    cluster = {
        candidate: cluster_sensitivities(
            records[PRIMARY][candidate], records[PRIMARY][LEARNED])
        for candidate in CANDIDATES
    }

    if not replication_positive["learned-identity"]:
        verdict = "ML1M-NO-FIR-REPLICATION"
    elif noninferiority_pass["shared"]:
        verdict = "ML1M-SHARED-NI"
    elif noninferiority_pass["grouped"]:
        verdict = "ML1M-GROUPED-NI"
    elif noninferiority_pass["lowrank"]:
        verdict = "ML1M-LOWRANK-NI"
    else:
        verdict = "ML1M-PERCHANNEL-ONLY"

    resource_summary = {}
    for category in campaign.CATEGORIES:
        resource_summary[category] = {}
        for arm in campaign.ARMS:
            rows = resources[category][arm]
            resource_summary[category][arm] = {
                "fir_control_trainable_params": EXPECTED_FILTER_PARAMS[arm],
                "latency_ms_median_across_seeds": float(np.median([
                    rows[seed]["latency_ms_median"] for seed in campaign.SEEDS])),
                "latency_ms_p95_across_seeds": float(np.median([
                    rows[seed]["latency_ms_p95"] for seed in campaign.SEEDS])),
                "flops_per_user_median": float(np.median([
                    rows[seed]["flops_per_user"] for seed in campaign.SEEDS])),
                "inference_peak_cuda_memory_bytes_median": int(np.median([
                    rows[seed]["peak_cuda_memory_bytes"] for seed in campaign.SEEDS])),
                "training_peak_cuda_memory_bytes_median": int(np.median([
                    rows[seed]["training_peak_cuda_memory_bytes"]
                    for seed in campaign.SEEDS])),
                "training_wall_time_s_median": float(np.median([
                    rows[seed]["training_wall_time_s"] for seed in campaign.SEEDS])),
            }

    sensitivity = {}
    for category in campaign.CATEGORIES:
        sensitivity[category] = {
            "means": {arm: float(np.mean(vectors[category][arm]))
                      for arm in campaign.ARMS},
            "candidate_minus_learned": {
                candidate: paired(vectors[category][candidate], vectors[category][LEARNED])
                for candidate in CANDIDATES},
            "learned_minus_identity": paired(
                vectors[category][LEARNED], vectors[category][IDENTITY]),
            "learned_minus_pointwise": paired(
                vectors[category][LEARNED], vectors[category][POINTWISE]),
        }

    data_provenance_path = campaign.PRIVATE_ROOT / "split_provenance.json"
    data_provenance = json.loads(data_provenance_path.read_text(encoding="utf-8"))
    if data_provenance.get("protocol") != PROTOCOL:
        die("private split provenance protocol mismatch")
    for category in campaign.CATEGORIES:
        expected = data_provenance["views"][category]["split_sha256"]
        observed = dict(zip(("train", "valid", "test"), split_hashes[category]))
        if expected != observed:
            die(f"private split provenance hash mismatch for {category}")

    print(f"{PROTOCOL} adjudication (mechanical first endpoint read)")
    print("primary rating>=4 global-time split; NI margin=0.000500 NDCG@10")
    for arm in campaign.ARMS:
        print(f"  {arm:9s} mean TEST NDCG@10 = {np.mean(primary_vectors[arm]):.6f}")
    for candidate, result in noninferiority_results.items():
        print(f"  {candidate:9s}-learned d={result['mean']:+.6f} "
              f"simul.lower={result['simultaneous_lower']:+.6f} "
              f"p_Holm={noninferiority_holm[candidate]['p_holm']:.4g} "
              f"{'NI-PASS' if noninferiority_pass[candidate] else 'NI-FAIL'}")
    for name, result in replication.items():
        print(f"  {name:20s} d={result['mean']:+.6f} "
              f"CI=[{result['ci'][0]:+.6f},{result['ci'][1]:+.6f}] "
              f"p_Holm={replication_holm[name]['p_holm']:.4g} "
              f"{'PASS' if replication_positive[name] else 'FAIL'}")
    print("VERDICT:", verdict)
    print("Scope: same-investigator non-Amazon robustness/efficiency evidence; not independent confirmation.")

    artifact = {
        "protocol": PROTOCOL,
        "verdict": verdict,
        "scope": "prospectively frozen same-investigator non-Amazon robustness and efficiency study",
        "not_independent_confirmation": True,
        "primary_category": PRIMARY,
        "alpha": ALPHA,
        "noninferiority_margin_ndcg10": MARGIN,
        "seeds": list(campaign.SEEDS),
        "arms": list(campaign.ARMS),
        "filter_trainable_parameters": EXPECTED_FILTER_PARAMS,
        "primary_means": {arm: float(np.mean(primary_vectors[arm]))
                          for arm in campaign.ARMS},
        "primary_values": primary_vectors,
        "replication": replication,
        "replication_holm": replication_holm,
        "replication_positive": replication_positive,
        "noninferiority": noninferiority_results,
        "noninferiority_holm": noninferiority_holm,
        "noninferiority_pass": noninferiority_pass,
        "cluster_sensitivities": cluster,
        "all_ratings_sensitivity": sensitivity["MovieLens1M_ALL"],
        "resource_summary": resource_summary,
        "backbone_init_sha256": backbone,
        "split_sha256": {category: dict(zip(
            ("train", "valid", "test"), split_hashes[category]))
            for category in campaign.CATEGORIES},
        "data_provenance": data_provenance,
        "frozen_sha256_lf": FROZEN_SHA256_LF,
        "caveats": [
            "The study is prospectively frozen but same-investigator and same-code-lineage.",
            "One non-Amazon dataset does not establish population-wide generalization.",
            "The 0.0005 margin is a preregistered measurement-scale SESOI, not a business KPI.",
            "User/item bootstrap intervals are fixed-dataset sensitivities, not new independent samples.",
            "MovieLens record-level artifacts remain private under the ML-1M README.",
        ],
    }
    output = HERE / "fir_efficiency_ml1m_v1_adjudication.json"
    output.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print("wrote", output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
