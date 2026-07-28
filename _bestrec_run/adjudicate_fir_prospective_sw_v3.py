#!/usr/bin/env python3
"""Mechanical first intentional endpoint reader for Software FIR V3."""

from __future__ import annotations

import json
import math
import os

import numpy as np
from scipy import stats

import fir_prospective_sw_v3_common as common
import run_fir_prospective_sw_v3 as campaign


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


def main() -> int:
    head = common.assert_tagged_tree()  # includes adjudicator self-integrity
    env = common.assert_environment()
    common.assert_inputs()
    _, attempt_sha = common.load_attempt()
    ready, ready_sha = common.load_ready()
    if not common.ENDPOINTS_COMPLETE.is_file():
        die("ENDPOINTS-COMPLETE seal is missing")
    completed = json.loads(common.ENDPOINTS_COMPLETE.read_text(encoding="utf-8"))
    if (completed.get("protocol") != common.PROTOCOL
            or completed.get("execution_git_head") != head
            or completed.get("attempt_sha256") != attempt_sha
            or completed.get("ready_sha256") != ready_sha
            or completed.get("endpoint_semantically_parsed_by_driver") is not False):
        die("ENDPOINTS-COMPLETE binding mismatch")
    if common.ADJUDICATION.exists():
        die("adjudication output exists; refusing overwrite")

    values = {arm: {} for arm in common.ARMS}
    secondary = {metric: {arm: {} for arm in common.ARMS}
                 for metric in ("HR@10", "MRR")}
    backbone = {seed: {} for seed in common.SEEDS}
    evidence = {}
    normalized_cfg = None

    # First endpoint-content reads begin here, after all 16 endpoint sets and
    # the content-blind digest inventory exist.
    for arm, seed in common.ordered_jobs():
        run = common.path_for(arm, seed)
        ckpt = run.with_suffix(".best.pt")
        final_path = run.with_suffix(".finaleval.json")
        users_path = run.with_suffix(".finaleval.users.npz")
        seal_path = run.with_suffix(".finaleval.started.json")
        record = completed["artifacts"][f"{arm}:{seed}"]
        for key, path in (("finaleval", final_path), ("users", users_path),
                          ("started_seal", seal_path)):
            if (not path.is_file()
                    or record[key]["name"] != path.name
                    or record[key]["sha256"] != common.sha256(path)):
                die(f"endpoint inventory mismatch: {arm}:{seed}:{key}")

        base = campaign.validate_training_json(run, arm, seed, head, attempt_sha)
        final = json.loads(final_path.read_text(encoding="utf-8"))
        cfg = base["config"]
        normalized = {key: value for key, value in cfg.items()
                      if key not in {"fir_control", "seed", "out"}}
        if normalized_cfg is None:
            normalized_cfg = normalized
        elif normalized != normalized_cfg:
            die(f"non-arm configuration drift: {run.name}")
        custody = base["prospective_custody"]
        provenance = final.get("provenance", {})
        if (final.get("protocol") != common.PROTOCOL
                or final.get("category") != common.CATEGORY
                or final.get("seed") != seed
                or final.get("arm") != arm
                or provenance.get("execution_git_head") != head
                or provenance.get("attempt_sha256") != attempt_sha
                or provenance.get("ready_sha256") != ready_sha
                or provenance.get("run_json_sha256") != common.sha256(run)
                or provenance.get("checkpoint_sha256") != common.sha256(ckpt)
                or provenance.get("started_seal_sha256") != common.sha256(seal_path)
                or provenance.get("users_sidecar_sha256") != common.sha256(users_path)
                or provenance.get("exact_argv_sha256") != custody["exact_argv_sha256"]
                or provenance.get("model_builder_sha256") != common.sha256(common.MODEL_BUILDER)
                or provenance.get("base_trainer_sha256") != common.sha256(common.BASE_TRAINER)):
            die(f"endpoint provenance mismatch: {final_path.name}")
        metrics = final.get("test", {})
        for metric in ("NDCG@10", "HR@10", "MRR"):
            if metric not in metrics or not np.isfinite(metrics[metric]):
                die(f"missing/nonfinite {metric}: {final_path.name}")
        with np.load(users_path, allow_pickle=False) as users:
            if len(users["ndcg10"]) != metrics.get("n_eval"):
                die(f"per-user row mismatch: {users_path.name}")
            if not np.isclose(users["ndcg10"].mean(), metrics["NDCG@10"], atol=1e-12):
                die(f"per-user endpoint mismatch: {users_path.name}")
        values[arm][seed] = float(metrics["NDCG@10"])
        for metric in secondary:
            secondary[metric][arm][seed] = float(metrics[metric])
        backbone[seed][arm] = base.get("backbone_init_sha256")
        evidence[f"{arm}:{seed}"] = {
            "run_json_sha256": common.sha256(run),
            "checkpoint_sha256": common.sha256(ckpt),
            "finaleval_sha256": common.sha256(final_path),
            "users_sha256": common.sha256(users_path),
            "seal_sha256": common.sha256(seal_path),
        }

    for seed, hashes in backbone.items():
        if None in hashes.values() or len(set(hashes.values())) != 1:
            die(f"unmatched backbone initialization: {seed}")
    vectors = {arm: [values[arm][seed] for seed in common.SEEDS]
               for arm in common.ARMS}
    result = paired(vectors["learned"], vectors["identity"])
    if result["ci95"][0] > common.PRACTICAL and result["p_two_sided"] < common.ALPHA:
        verdict = "SW-V3-PRACTICAL-POS"
    elif result["ci95"][0] > 0 and result["p_two_sided"] < common.ALPHA:
        verdict = "SW-V3-POS-BELOW-PRACTICAL"
    elif (result["mean"] < 0 and result["ci95"][1] < 0
          and result["p_two_sided"] < common.ALPHA):
        verdict = "SW-V3-NEG"
    else:
        verdict = "SW-V3-INCONCLUSIVE"

    artifact = {
        "protocol": common.PROTOCOL,
        "verdict": verdict,
        "scope": "prospective same-investigator, same-code-lineage, same-Amazon-family category attempt; not independent confirmation",
        "custody_scope": "local same-user operational first-reader handoff; no external escrow or independent custody",
        "category": common.CATEGORY,
        "alpha": common.ALPHA,
        "practical_threshold": common.PRACTICAL,
        "practical_rule": "ordinary paired 95% CI lower bound must exceed +0.000500",
        "seeds": list(common.SEEDS),
        "means": {arm: float(np.mean(vectors[arm])) for arm in common.ARMS},
        "values": vectors,
        "primary_contrast": result,
        "secondary_descriptive_means": {
            metric: {arm: float(np.mean([secondary[metric][arm][seed]
                                        for seed in common.SEEDS]))
                     for arm in common.ARMS}
            for metric in secondary
        },
        "backbone_hashes": backbone,
        "execution_git_tag": common.TAG,
        "execution_git_head": head,
        "runtime": env,
        "attempt_sha256": attempt_sha,
        "ready_sha256": ready_sha,
        "endpoints_complete_sha256": common.sha256(common.ENDPOINTS_COMPLETE),
        "adjudicator_self_sha256": common.sha256(common.ADJUDICATOR),
        "input_sha256": common.EXPECTED_INPUT_SHA256,
        "reference_sha256": common.EXPECTED_REFERENCE_SHA256,
        "evidence": evidence,
    }
    common.atomic_json_x(common.ADJUDICATION, artifact)
    print(f"{common.PROTOCOL} adjudication")
    print(f"  identity mean TEST NDCG@10 = {np.mean(vectors['identity']):.6f}")
    print(f"  learned  mean TEST NDCG@10 = {np.mean(vectors['learned']):.6f}")
    print(f"  learned-identity d={result['mean']:+.6f} "
          f"CI=[{result['ci95'][0]:+.6f},{result['ci95'][1]:+.6f}] "
          f"t({result['df']})={result['t']:.4f} p={result['p_two_sided']:.6g}")
    print("VERDICT:", verdict)
    print("A retained null is not evidence of equivalence.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(exc)
        raise SystemExit(2)
