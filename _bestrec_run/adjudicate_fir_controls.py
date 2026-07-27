# -*- coding: utf-8 -*-
"""Mechanical first reader and adjudicator for PREREG_FIR_CONTROLS."""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np
from scipy import stats

import run_fir_controls as campaign

HERE = Path(__file__).resolve().parent
ALPHA = 0.05
IDENTITY = "identity"
LEARNED = "learned"
CONTROLS = ("fixed_ma", "fixed_hp", "shared", "nonlinear")
ACTIVE = (LEARNED,) + CONTROLS
FROZEN_SOURCE_HASHES = {
    # Stage-2 records captured raw Windows worktree bytes.  The trainer had
    # CRLF endings; Git stores/checks out the canonical LF blob elsewhere.
    "trainer": {
        "recorded_raw": "7bdde0bf615c3e29fada251ba4ec8141032e8e9cc747e0daf8a812711e5d51f4",
        "canonical_lf": "5620d4e2c2a38bd5a4db7f1b8f01bbbf9ccf9071d19dced7f4be94444261d854",
    },
    "evaluator": {
        "recorded_raw": "36598d47764ce14c79845079f3d7f5af618937460fb001a673ef4136b65d9d02",
        "canonical_lf": "36598d47764ce14c79845079f3d7f5af618937460fb001a673ef4136b65d9d02",
    },
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def sha256_lf(path):
    """Hash the canonical Git representation of a text source file."""
    data = Path(path).read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def die(message):
    raise RuntimeError("INTEGRITY FAIL: " + message)


def paired(x, y):
    d = np.asarray(x, dtype=float) - np.asarray(y, dtype=float)
    n = len(d)
    mean = float(d.mean())
    sd = float(d.std(ddof=1))
    se = sd / math.sqrt(n)
    if se == 0:
        p = 0.0 if mean != 0 else 1.0
        ci = (mean, mean)
        t = math.copysign(math.inf, mean) if mean else 0.0
    else:
        t = mean / se
        p = float(2.0 * stats.t.sf(abs(t), n - 1))
        q = float(stats.t.ppf(0.975, n - 1))
        ci = (mean - q * se, mean + q * se)
    return {"mean": mean, "sd": sd, "t": t, "df": n - 1,
            "p": p, "ci95": [float(ci[0]), float(ci[1])],
            "per_seed": [float(v) for v in d]}


def holm(raw):
    names = sorted(raw, key=raw.get)
    m = len(names)
    adjusted = {}
    running = 0.0
    for i, name in enumerate(names):
        running = max(running, (m - i) * raw[name])
        adjusted[name] = min(1.0, running)
    return {name: {"p_raw": float(raw[name]),
                   "p_holm": float(adjusted[name]),
                   "reject": bool(adjusted[name] < ALPHA)}
            for name in raw}


def normalized_config(cfg):
    ignored = {"fir_control", "seed", "out"}
    return {k: v for k, v in cfg.items() if k not in ignored}


def main():
    values = {arm: {} for arm in campaign.ARMS}
    hashes = {seed: {} for seed in campaign.SEEDS}
    trainable = {}
    normalized = None
    test_split_hash = None
    missing = []
    evaluator_hash = sha256_lf(HERE / "eval_fir_controls.py")
    trainer_hash = sha256_lf(HERE / "run_sasrec_sbert.py")
    if evaluator_hash != FROZEN_SOURCE_HASHES["evaluator"]["canonical_lf"]:
        die("canonical evaluator source digest mismatch")
    if trainer_hash != FROZEN_SOURCE_HASHES["trainer"]["canonical_lf"]:
        die("canonical trainer source digest mismatch")

    for seed in campaign.SEEDS:
        for arm in campaign.ARMS:
            run_path = Path(campaign.path_for(arm, seed))
            ckpt_path = run_path.with_suffix(".best.pt")
            final_path = run_path.with_suffix(".finaleval.json")
            users_path = run_path.with_suffix(".finaleval.users.npz")
            seal_path = run_path.with_suffix(".finaleval.started.json")
            absent = [p.name for p in (run_path, ckpt_path, final_path,
                                        users_path, seal_path) if not p.exists()]
            if absent:
                missing.extend(absent)
                continue
            base = json.load(open(run_path, encoding="utf-8"))
            final = json.load(open(final_path, encoding="utf-8"))
            cfg = base["config"]
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
            nc = normalized_config(cfg)
            if normalized is None:
                normalized = nc
            elif nc != normalized:
                die(f"non-arm/non-seed config differs in {run_path.name}")
            if base.get("best_test") is not None or any(
                    "test" in epoch for epoch in base.get("history", [])):
                die(f"training accessed TEST in {run_path.name}")
            if base.get("best_ckpt_sha256") != sha256(ckpt_path):
                die(f"checkpoint digest mismatch in {run_path.name}")
            if arm == IDENTITY and base.get("fir_control_final_l2") != 0.0:
                die(f"identity taps moved in {run_path.name}")
            if arm in ("fixed_ma", "fixed_hp"):
                if base.get("fir_control_alpha") is None:
                    die(f"fixed-filter scalar absent in {run_path.name}")
            elif base.get("fir_control_alpha") is not None:
                die(f"unexpected fixed-filter scalar in {run_path.name}")
            hashes[seed][arm] = base.get("backbone_init_sha256")
            trainable[arm] = base.get("n_trainable_params")

            prov = final.get("provenance", {})
            if (final.get("protocol") != "PREREG_FIR_CONTROLS"
                    or final.get("category") != campaign.CATEGORY
                    or final.get("seed") != seed
                    or final.get("arm") != arm):
                die(f"final-evaluation binding mismatch in {final_path.name}")
            expected = {
                "run_json_sha256": sha256(run_path),
                "checkpoint_sha256": sha256(ckpt_path),
                "started_seal_sha256": sha256(seal_path),
                "users_sidecar_sha256": sha256(users_path),
            }
            for key, value in expected.items():
                if prov.get(key) != value:
                    die(f"{key} mismatch in {final_path.name}")
            for source in ("evaluator", "trainer"):
                key = f"{source}_sha256"
                if prov.get(key) != FROZEN_SOURCE_HASHES[source]["recorded_raw"]:
                    die(f"recorded raw {key} mismatch in {final_path.name}")
            if test_split_hash is None:
                test_split_hash = prov.get("test_split_sha256")
            elif prov.get("test_split_sha256") != test_split_hash:
                die("TEST split digest differs across arms")
            metric = final.get("test", {}).get("NDCG@10")
            if metric is None or not np.isfinite(metric):
                die(f"missing/nonfinite endpoint in {final_path.name}")
            with np.load(users_path) as users:
                if len(users["ndcg10"]) != final["test"].get("n_eval"):
                    die(f"per-user row count mismatch in {users_path.name}")
                if not np.isclose(users["ndcg10"].mean(), metric, atol=1e-12):
                    die(f"per-user endpoint mismatch in {users_path.name}")
            values[arm][seed] = float(metric)

    if missing:
        print(f"NOT READY: {len(missing)} required artifact(s) missing")
        for name in missing[:12]:
            print("  -", name)
        return 3
    for seed, arm_hashes in hashes.items():
        if None in arm_hashes.values() or len(set(arm_hashes.values())) != 1:
            die(f"seed {seed} does not share one backbone initialization: "
                f"{arm_hashes}")
    if trainable[LEARNED] != trainable["nonlinear"]:
        die("parameter-matched nonlinear arm has different trainable count")

    vectors = {arm: [values[arm][s] for s in campaign.SEEDS]
               for arm in campaign.ARMS}
    family_a = {}
    for arm in ACTIVE:
        name = f"{arm}-identity"
        family_a[name] = paired(vectors[arm], vectors[IDENTITY])
    family_b = {}
    for arm in CONTROLS:
        name = f"learned-{arm}"
        family_b[name] = paired(vectors[LEARNED], vectors[arm])
    holm_a = holm({k: v["p"] for k, v in family_a.items()})
    holm_b = holm({k: v["p"] for k, v in family_b.items()})

    def positive(result, decision):
        return bool(result["mean"] > 0 and result["ci95"][0] > 0
                    and decision["reject"])

    learned_rep = positive(family_a["learned-identity"],
                           holm_a["learned-identity"])
    learned_discriminates = {
        arm: positive(family_b[f"learned-{arm}"],
                      holm_b[f"learned-{arm}"])
        for arm in CONTROLS
    }
    supported_controls = [
        arm for arm in CONTROLS
        if positive(family_a[f"{arm}-identity"],
                    holm_a[f"{arm}-identity"])
    ]
    if not learned_rep:
        verdict = "CTRL-NO-REPLICATION"
    elif all(learned_discriminates.values()):
        verdict = "CTRL-LEARNED-DISCRIMINATED"
    elif supported_controls:
        verdict = "CTRL-ACTIVE-CONTROL-SUPPORTED"
    else:
        verdict = "CTRL-INCONCLUSIVE"

    print("PREREG_FIR_CONTROLS adjudication (mechanical first read)")
    print("ordinary paired 95% CIs; Holm decisions are reported separately")
    for arm in campaign.ARMS:
        print(f"  {arm:10s} mean test NDCG@10 = {np.mean(vectors[arm]):.6f}")
    print("Family A: active arm minus identity")
    for name, result in family_a.items():
        decision = holm_a[name]
        print(f"  {name:22s} d={result['mean']:+.6f} "
              f"CI=[{result['ci95'][0]:+.6f},{result['ci95'][1]:+.6f}] "
              f"p={result['p']:.4g} p_Holm={decision['p_holm']:.4g} "
              f"{'reject' if decision['reject'] else 'retain'}")
    print("Family B: learned arm minus active control")
    for name, result in family_b.items():
        decision = holm_b[name]
        print(f"  {name:22s} d={result['mean']:+.6f} "
              f"CI=[{result['ci95'][0]:+.6f},{result['ci95'][1]:+.6f}] "
              f"p={result['p']:.4g} p_Holm={decision['p_holm']:.4g} "
              f"{'reject' if decision['reject'] else 'retain'}")
    print("VERDICT:", verdict)
    print("supported active controls:", supported_controls or "none")
    print("A retained contrast is not evidence of equivalence.")

    out = {
        "protocol": "PREREG_FIR_CONTROLS", "verdict": verdict,
        "alpha": ALPHA, "category": campaign.CATEGORY,
        "kernel": campaign.KERNEL, "seeds": list(campaign.SEEDS),
        "means": {a: float(np.mean(vectors[a])) for a in campaign.ARMS},
        "values": vectors, "family_a": family_a, "holm_a": holm_a,
        "family_b": family_b, "holm_b": holm_b,
        "learned_replication": learned_rep,
        "learned_discriminates": learned_discriminates,
        "supported_controls": supported_controls,
        "backbone_hashes": hashes, "n_trainable_params": trainable,
        "test_split_sha256": test_split_hash,
        "scope": "internal outcome-known active-control study; no external "
                 "comparator or distributional claim",
    }
    out_path = HERE / "fir_controls_adjudication.json"
    tmp = out_path.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, allow_nan=False)
    os.replace(tmp, out_path)
    print("wrote", out_path)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(exc)
        raise SystemExit(2)
