#!/usr/bin/env python3
"""Mechanical first endpoint reader for PREREG_WEAREC_BASELINE_V1."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy import stats

import wearec_baseline_v1_common as common


HERE = Path(__file__).resolve().parent
STATUS = HERE / "wearec_baseline_v1_status.json"
SELECTION = HERE / "wearec_baseline_v1_selection.json"
OUT = HERE / "wearec_baseline_v1_adjudication.json"
REFERENCE = {
    "results_V2_ls02_filter8_VG.json": "d391651bac4a2354054a4165f3df536a78e2604ad763d44bd0f509f6a588f1bd",
    "results_V2_ls02_filter8_seed20260609_VG.json": "737b2434cf1ce2cd1a01d646f06079b9a8644d34759a3929f331a2e82e63c183",
    "results_V2_ls02_filter8_seed20260610_VG.json": "db4f693bc37d5830569a69ea854dda19de74c505af9d5b59e560064e47c5d32f",
    "results_V2_ls02_filter8_seed20260611_VG.json": "f3a0032f76230fa9ab66e2c9e576856f13ad18930b480f9ef128073952ead3fa",
    "results_V2_ls02_filter8_seed20260612_VG.json": "ab2110f0c0973f65aba9359258528cf88a577a9f8bf549689e48778e02d3f422",
    "results_V2_confirm_seed20260613_VG.json": "d37cb83ba049b64bd2f5fdf694871d2d5948eccbbfb667b4cbfdc7ad3ac51c0b",
}


def fail(message: str) -> None:
    raise SystemExit(f"WEAREC-INTEGRITY-FAIL: {message}")


def read_json(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception as exc:
        fail(f"cannot read {path}: {exc}")


def one_sample(values: list[float]) -> dict:
    arr = np.asarray(values, dtype=np.float64)
    n = len(arr)
    mean = float(arr.mean())
    sd = float(arr.std(ddof=1))
    half = float(stats.t.ppf(0.975, n - 1) * sd / math.sqrt(n))
    return {"n": n, "mean": mean, "sd": sd, "ci95": [mean - half, mean + half]}


def welch(a: list[float], b: list[float]) -> dict:
    aa = np.asarray(a, dtype=np.float64)
    bb = np.asarray(b, dtype=np.float64)
    va = float(aa.var(ddof=1) / len(aa))
    vb = float(bb.var(ddof=1) / len(bb))
    se = math.sqrt(va + vb)
    df = (va + vb) ** 2 / (va * va / (len(aa) - 1) + vb * vb / (len(bb) - 1))
    delta = float(aa.mean() - bb.mean())
    half = float(stats.t.ppf(0.975, df) * se)
    t_value = delta / se
    p = float(2.0 * stats.t.sf(abs(t_value), df))
    return {
        "estimand": "WEARec minus existing full-model reference",
        "delta": delta,
        "se": se,
        "t": t_value,
        "df": df,
        "p_two_sided_unadjusted": p,
        "ci95_unadjusted": [delta - half, delta + half],
        "warning": "descriptive outcome-known cross-system contrast; not randomized, paired, or confirmatory",
    }


def main() -> int:
    if OUT.exists():
        fail(f"refusing to overwrite prior adjudication: {OUT}")
    status = read_json(STATUS)
    if (
        status.get("protocol") != common.PROTOCOL
        or status.get("state") != "complete"
        or status.get("assessment_trained") != len(common.ASSESSMENT_SEEDS)
        or status.get("assessment_evaluated") != len(common.ASSESSMENT_SEEDS)
    ):
        fail("campaign status is not complete 8/8")
    selection = read_json(SELECTION)
    if selection.get("protocol") != common.PROTOCOL or selection.get("test_read_or_scored") is not False:
        fail("selection provenance mismatch")
    tune_values: dict[str, float] = {}
    tune_commits: set[str] = set()
    for preset in common.PRESET_ORDER:
        train = read_json(common.train_output("tune", preset, common.TUNE_SEED))
        if train.get("test_read_or_scored") is not False:
            fail(f"tuning record reports TEST access: {preset}")
        tune_values[preset] = float(train["best_valid"]["NDCG@10"])
        tune_commits.add(str(train.get("config", {}).get("repository_commit")))
    selected = max(
        common.PRESET_ORDER,
        key=lambda name: (tune_values[name], -common.PRESET_ORDER.index(name)),
    )
    if selection.get("selected_preset") != selected or selection.get("validation_ndcg10") != tune_values:
        fail("selected preset does not mechanically maximize frozen VALID endpoint")

    values: list[float] = []
    hrs: list[float] = []
    mrrs: list[float] = []
    resources: list[dict] = []
    endpoint_hashes: dict[str, str] = {}
    repository_commits: set[str] = set()
    for seed in common.ASSESSMENT_SEEDS:
        train_path = common.train_output("assessment", selected, seed)
        checkpoint = common.checkpoint_path("assessment", selected, seed)
        endpoint_path = common.endpoint_path(selected, seed)
        users_path = common.endpoint_users_path(selected, seed)
        seal_path = common.endpoint_seal_path(selected, seed)
        for path in (train_path, checkpoint, endpoint_path, users_path, seal_path):
            if not path.is_file():
                fail(f"missing required artifact: {path}")
        train = read_json(train_path)
        endpoint = read_json(endpoint_path)
        seal = read_json(seal_path)
        if (
            train.get("protocol") != common.PROTOCOL
            or train.get("state") != "training_complete_test_unread"
            or train.get("test_read_or_scored") is not False
            or train.get("config", {}).get("preset") != selected
            or train.get("config", {}).get("seed") != seed
            or train.get("checkpoint_sha256") != common.sha256(checkpoint)
        ):
            fail(f"training provenance mismatch for seed {seed}")
        if (
            seal.get("state") != "final_test_started_no_repeat"
            or seal.get("checkpoint_sha256") != common.sha256(checkpoint)
            or endpoint.get("protocol") != common.PROTOCOL
            or endpoint.get("state") != "final_test_complete"
            or endpoint.get("preset") != selected
            or endpoint.get("seed") != seed
            or endpoint.get("repository_commit") != train.get("config", {}).get("repository_commit")
            or endpoint.get("checkpoint_sha256") != common.sha256(checkpoint)
            or endpoint.get("train_artifact_sha256") != common.sha256(train_path)
            or endpoint.get("catalog_sha256") != common.CATALOG_SHA256
            or endpoint.get("split_sha256") != common.SPLIT_HASHES
            or endpoint.get("perusers_sha256") != common.sha256(users_path)
        ):
            fail(f"sealed endpoint provenance mismatch for seed {seed}")
        with np.load(users_path, allow_pickle=False) as records:
            required = {"user_index", "target_item_id", "rank0", "ndcg10", "hr10", "rr"}
            if set(records.files) != required:
                fail(f"per-user schema mismatch for seed {seed}")
            if len(records["rank0"]) != common.N_EXPECTED_USERS:
                fail(f"per-user row count mismatch for seed {seed}")
            rank = records["rank0"].astype(np.int64)
            ndcg = np.where(rank < 10, 1.0 / np.log2(rank.astype(np.float64) + 2.0), 0.0)
            hr = (rank < 10).astype(np.float64)
            rr = 1.0 / (rank.astype(np.float64) + 1.0)
            if not np.array_equal(records["user_index"], np.arange(common.N_EXPECTED_USERS)):
                fail(f"per-user order mismatch for seed {seed}")
            if not np.allclose(records["ndcg10"], ndcg, rtol=0, atol=1e-15):
                fail(f"per-user NDCG mismatch for seed {seed}")
            metrics = endpoint.get("metrics", {})
            recomputed = {
                "NDCG@10": float(ndcg.mean()),
                "HR@10": float(hr.mean()),
                "MRR": float(rr.mean()),
            }
            for key, value in recomputed.items():
                if not math.isfinite(float(metrics.get(key, math.nan))) or abs(float(metrics[key]) - value) > 1e-15:
                    fail(f"endpoint {key} mismatch for seed {seed}")
        values.append(recomputed["NDCG@10"])
        repository_commits.add(str(train["config"]["repository_commit"]))
        hrs.append(recomputed["HR@10"])
        mrrs.append(recomputed["MRR"])
        resources.append(
            {
                "seed": seed,
                "n_params": int(train["n_params"]),
                "best_epoch": int(train["best_epoch"]),
                "train_seconds": float(train["train_seconds"]),
                "peak_cuda_memory_bytes": int(train["peak_cuda_memory_bytes"]),
                "eval_seconds": float(endpoint["metrics"]["eval_seconds"]),
            }
        )
        endpoint_hashes[str(seed)] = common.sha256(endpoint_path)

    if len(repository_commits) != 1 or tune_commits != repository_commits:
        fail("assessment runs do not share one frozen repository commit")

    reference_values: list[float] = []
    for name, expected in REFERENCE.items():
        path = HERE / name
        if common.sha256(path) != expected:
            fail(f"existing reference identity mismatch: {name}")
        obj = read_json(path)
        value = float(obj["best_test"]["NDCG@10"])
        if not math.isfinite(value) or int(obj["best_test"]["n_eval"]) != common.N_EXPECTED_USERS:
            fail(f"existing reference endpoint mismatch: {name}")
        reference_values.append(value)

    contrast = welch(values, reference_values)
    lower, upper = contrast["ci95_unadjusted"]
    if lower > 0:
        verdict = "WEAREC-ABOVE-EXISTING-REFERENCE"
    elif upper < 0:
        verdict = "WEAREC-BELOW-EXISTING-REFERENCE"
    else:
        verdict = "WEAREC-REFERENCE-OVERLAP"
    adjudication = {
        "protocol": common.PROTOCOL,
        "verdict": verdict,
        "evidence_class": "prospectively frozen execution on an outcome-known split by the same investigators",
        "claim_boundary": (
            "official 2026 WEARec model/training code under the paper's shared split, full-catalog mask, "
            "and tie rule; not independent confirmation, SOTA, a paired experiment, or equal tuning budgets"
        ),
        "upstream": {"url": common.UPSTREAM_URL, "commit": common.UPSTREAM_COMMIT},
        "execution_repository_commit": next(iter(repository_commits)),
        "selected_preset": selected,
        "validation_selection": tune_values,
        "assessment_seeds": list(common.ASSESSMENT_SEEDS),
        "wearec_ndcg10": one_sample(values),
        "wearec_hr10": one_sample(hrs),
        "wearec_mrr": one_sample(mrrs),
        "existing_full_model_reference_ndcg10": one_sample(reference_values),
        "descriptive_welch_contrast": contrast,
        "vectors": {"wearec_ndcg10": values, "existing_reference_ndcg10": reference_values},
        "resources": resources,
        "endpoint_sha256": endpoint_hashes,
        "reference_sha256": REFERENCE,
    }
    common.atomic_json(OUT, adjudication)
    print(f"{common.PROTOCOL} adjudication (mechanical first read)")
    print(f"verdict: {verdict}")
    print(
        f"WEARec NDCG@10 mean={adjudication['wearec_ndcg10']['mean']:.10f} "
        f"95% CI=[{adjudication['wearec_ndcg10']['ci95'][0]:.10f},"
        f"{adjudication['wearec_ndcg10']['ci95'][1]:.10f}]"
    )
    print(
        f"WEARec-reference delta={contrast['delta']:+.10f} "
        f"95% CI=[{lower:+.10f},{upper:+.10f}], p={contrast['p_two_sided_unadjusted']:.6g}"
    )
    print("BOUNDARY: outcome-known same-investigator equal-evaluation comparator; not confirmation or SOTA")
    return 0


if __name__ == "__main__":
    sys.exit(main())
