#!/usr/bin/env python3
"""Mechanical first endpoint reader for prospective Software FIR V2."""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np
from scipy import stats

import run_fir_prospective_sw_v2 as campaign


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ALPHA = 0.05
PRACTICAL = 0.0005
PROTOCOL = campaign.PROTOCOL
FROZEN_FILES = {
    "base_trainer": "_bestrec_run/run_sasrec_sbert_pointwise_v1_frozen.py",
    "wrapper": "_bestrec_run/run_sasrec_sbert_software_v2_frozen.py",
    "evaluator": "_bestrec_run/eval_fir_prospective_sw_v2.py",
    "runner": "_bestrec_run/run_fir_prospective_sw_v2.py",
    "structural_test": "_bestrec_run/test_fir_pointwise_v1.py",
    "preregistration": "PREREG_FIR_PROSPECTIVE_SW_V2.md",
}
# Filled mechanically before launch; canonical-LF digests.
FROZEN_SHA256_LF = {
    "base_trainer": "46dbbc2f2a3c86a8410e549f92d70228edc24d0b05d66da0fa081298e2a73ac8",
    "wrapper": "296f80e63af04364c3346e0422ef562ced7310117d078ba8b74ebfddbcbab050",
    "evaluator": "c159fd76902c944a38b2d1a1fa6afaa8948a89e1f28388ad68be3980a4119e25",
    "runner": "32cf612f7cde60124b0178122ec2468aef7add9766501ac58fbd1154ee20e859",
    "structural_test": "6b4ae09d0e007158f2bb201758625ec2c3c14fcabc22c450a686226214aed30c",
    "preregistration": "d36193259f2fa90921d9feb8448883294b849424f16f8722b66cf35b9af1c55f",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def sha256_lf(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def die(message: str) -> None:
    raise RuntimeError("INTEGRITY FAIL: " + message)


def paired(learned: list[float], identity: list[float]) -> dict:
    differences = np.asarray(learned, dtype=float) - np.asarray(identity, dtype=float)
    n = len(differences)
    mean = float(differences.mean())
    sd = float(differences.std(ddof=1))
    se = sd / math.sqrt(n)
    if se == 0:
        statistic = math.copysign(math.inf, mean) if mean else 0.0
        pvalue = 0.0 if mean else 1.0
        interval = (mean, mean)
    else:
        statistic = mean / se
        pvalue = float(2.0 * stats.t.sf(abs(statistic), n - 1))
        quantile = float(stats.t.ppf(0.975, n - 1))
        interval = (mean - quantile * se, mean + quantile * se)
    return {
        "mean": mean,
        "sd": sd,
        "t": statistic,
        "df": n - 1,
        "p_two_sided": pvalue,
        "ci95": [float(interval[0]), float(interval[1])],
        "per_seed": [float(value) for value in differences],
    }


def normalized_config(cfg: dict) -> dict:
    return {key: value for key, value in cfg.items()
            if key not in {"fir_control", "seed", "out"}}


def main() -> int:
    for role, rel in FROZEN_FILES.items():
        actual = sha256_lf(ROOT / rel)
        if actual != FROZEN_SHA256_LF[role]:
            die(f"frozen {role} digest mismatch: {actual}")
    for rel, expected in campaign.EXPECTED_INPUT_SHA256.items():
        if sha256(ROOT / rel) != expected:
            die(f"frozen input mismatch: {rel}")

    values = {arm: {} for arm in campaign.ARMS}
    secondary = {metric: {arm: {} for arm in campaign.ARMS}
                 for metric in ("HR@10", "MRR")}
    backbone_hashes = {seed: {} for seed in campaign.SEEDS}
    execution_heads: set[str] = set()
    normalized = None
    missing: list[str] = []
    evidence = {}
    for seed in campaign.SEEDS:
        for arm in campaign.ARMS:
            run_path = campaign.path_for(arm, seed)
            ckpt_path = run_path.with_suffix(".best.pt")
            final_path = run_path.with_suffix(".finaleval.json")
            users_path = run_path.with_suffix(".finaleval.users.npz")
            seal_path = run_path.with_suffix(".finaleval.started.json")
            absent = [path.name for path in (run_path, ckpt_path, final_path, users_path, seal_path)
                      if not path.is_file()]
            if absent:
                missing.extend(absent)
                continue
            base = json.loads(run_path.read_text(encoding="utf-8"))
            final = json.loads(final_path.read_text(encoding="utf-8"))
            cfg = base.get("config", {})
            custody = base.get("prospective_custody", {})
            if (cfg.get("category") != campaign.CATEGORY
                    or cfg.get("seed") != seed
                    or cfg.get("epochs") != 20
                    or cfg.get("fir_control") != arm
                    or cfg.get("fir_control_kernel") != campaign.KERNEL
                    or cfg.get("fir_v3") != "off"
                    or cfg.get("causal_filter")
                    or not cfg.get("no_test_eval")
                    or not cfg.get("save_ckpt")):
                die(f"frozen config mismatch in {run_path.name}")
            config_without_arm = normalized_config(cfg)
            if normalized is None:
                normalized = config_without_arm
            elif normalized != config_without_arm:
                die(f"non-arm/non-seed config differs in {run_path.name}")
            if base.get("best_test") is not None or any(
                    "test" in epoch for epoch in base.get("history", [])):
                die(f"training accessed TEST in {run_path.name}")
            if base.get("best_ckpt_sha256") != sha256(ckpt_path):
                die(f"checkpoint digest mismatch in {run_path.name}")
            if arm == "identity" and base.get("fir_control_final_l2") != 0.0:
                die(f"identity taps moved in {run_path.name}")
            if arm == "learned" and not (base.get("fir_control_final_l2", 0.0) > 0.0):
                die(f"learned FIR did not move in {run_path.name}")
            if (custody.get("protocol") != PROTOCOL
                    or custody.get("base_trainer_sha256_lf") != FROZEN_SHA256_LF["base_trainer"]
                    or custody.get("wrapper_sha256_lf") != FROZEN_SHA256_LF["wrapper"]):
                die(f"training custody mismatch in {run_path.name}")
            execution_heads.add(custody.get("execution_git_head"))
            backbone_hashes[seed][arm] = base.get("backbone_init_sha256")

            provenance = final.get("provenance", {})
            if (final.get("protocol") != PROTOCOL
                    or final.get("category") != campaign.CATEGORY
                    or final.get("seed") != seed
                    or final.get("arm") != arm
                    or provenance.get("execution_git_head") != custody.get("execution_git_head")):
                die(f"final binding mismatch in {final_path.name}")
            expected_provenance = {
                "run_json_sha256": sha256(run_path),
                "checkpoint_sha256": sha256(ckpt_path),
                "started_seal_sha256": sha256(seal_path),
                "users_sidecar_sha256": sha256(users_path),
                "base_trainer_sha256_lf": FROZEN_SHA256_LF["base_trainer"],
                "evaluator_sha256_lf": FROZEN_SHA256_LF["evaluator"],
                "train_split_sha256": campaign.EXPECTED_INPUT_SHA256["data_5core/5core/last_out/Software.train.csv"],
                "valid_split_sha256": campaign.EXPECTED_INPUT_SHA256["data_5core/5core/last_out/Software.valid.csv"],
                "test_split_sha256": campaign.EXPECTED_INPUT_SHA256["data_5core/5core/last_out/Software.test.csv"],
                "title_cache_sha256": campaign.EXPECTED_INPUT_SHA256["cache_5core/sbert_titles_Software.npy"],
            }
            for key, expected in expected_provenance.items():
                if provenance.get(key) != expected:
                    die(f"{key} mismatch in {final_path.name}")
            metrics = final.get("test", {})
            for metric in ("NDCG@10", "HR@10", "MRR"):
                if metric not in metrics or not np.isfinite(metrics[metric]):
                    die(f"missing/nonfinite {metric} in {final_path.name}")
            with np.load(users_path) as users:
                if len(users["ndcg10"]) != metrics.get("n_eval"):
                    die(f"per-user row count mismatch in {users_path.name}")
                if not np.isclose(users["ndcg10"].mean(), metrics["NDCG@10"], atol=1e-12):
                    die(f"per-user endpoint mismatch in {users_path.name}")
            values[arm][seed] = float(metrics["NDCG@10"])
            for metric in secondary:
                secondary[metric][arm][seed] = float(metrics[metric])
            evidence[f"{arm}:{seed}"] = {
                "run_json_sha256": sha256(run_path),
                "checkpoint_sha256": sha256(ckpt_path),
                "finaleval_sha256": sha256(final_path),
                "users_sha256": sha256(users_path),
                "seal_sha256": sha256(seal_path),
            }

    if missing:
        print(f"NOT READY: {len(missing)} required artifact(s) missing")
        for name in missing[:16]:
            print("  -", name)
        return 3
    if len(execution_heads) != 1 or None in execution_heads:
        die(f"runs do not share one execution Git HEAD: {execution_heads}")
    for seed, hashes in backbone_hashes.items():
        if None in hashes.values() or len(set(hashes.values())) != 1:
            die(f"seed {seed} lacks matched backbone initialization: {hashes}")

    vectors = {arm: [values[arm][seed] for seed in campaign.SEEDS]
               for arm in campaign.ARMS}
    result = paired(vectors["learned"], vectors["identity"])
    if (result["mean"] >= PRACTICAL and result["ci95"][0] > 0
            and result["p_two_sided"] < ALPHA):
        verdict = "SW-V2-CONFIRM-POS"
    elif result["ci95"][0] > 0 and result["p_two_sided"] < ALPHA:
        verdict = "SW-V2-STATISTICAL-SMALL"
    elif (result["mean"] < 0 and result["ci95"][1] < 0
          and result["p_two_sided"] < ALPHA):
        verdict = "SW-V2-CONFIRM-NEG"
    else:
        verdict = "SW-V2-INCONCLUSIVE"

    print(f"{PROTOCOL} adjudication (mechanical first endpoint read)")
    for arm in campaign.ARMS:
        print(f"  {arm:8s} mean TEST NDCG@10 = {np.mean(vectors[arm]):.6f}")
    print(f"  learned-identity d={result['mean']:+.6f} "
          f"CI=[{result['ci95'][0]:+.6f},{result['ci95'][1]:+.6f}] "
          f"t({result['df']})={result['t']:.4f} p={result['p_two_sided']:.6g}")
    print("VERDICT:", verdict)
    print("A retained null is not evidence of equivalence.")

    artifact = {
        "protocol": PROTOCOL,
        "verdict": verdict,
        "scope": "preregistered untouched-category confirmation attempt; same investigators, code lineage, and dataset family",
        "category": campaign.CATEGORY,
        "alpha": ALPHA,
        "practical_threshold": PRACTICAL,
        "seeds": list(campaign.SEEDS),
        "means": {arm: float(np.mean(vectors[arm])) for arm in campaign.ARMS},
        "values": vectors,
        "primary_contrast": result,
        "secondary_descriptive_means": {
            metric: {arm: float(np.mean([secondary[metric][arm][seed]
                                        for seed in campaign.SEEDS]))
                     for arm in campaign.ARMS}
            for metric in secondary
        },
        "backbone_hashes": backbone_hashes,
        "execution_git_head": next(iter(execution_heads)),
        "input_sha256": campaign.EXPECTED_INPUT_SHA256,
        "frozen_sha256_lf": FROZEN_SHA256_LF,
        "evidence": evidence,
    }
    out = HERE / "fir_prospective_sw_v2_adjudication.json"
    if out.exists():
        die(f"adjudication output exists; refusing overwrite: {out}")
    tmp = out.with_suffix(".json.tmp")
    with tmp.open("x", encoding="utf-8", newline="\n") as fh:
        json.dump(artifact, fh, indent=2, allow_nan=False)
        fh.write("\n")
    os.replace(tmp, out)
    print("wrote", out)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(exc)
        raise SystemExit(2)
