# -*- coding: utf-8 -*-
"""Mechanical first reader for PREREG_FIR_POINTWISE_V1."""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np
from scipy import stats
import torch

import run_fir_pointwise_v1 as campaign


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ALPHA = 0.05
IDENTITY = "identity"
LEARNED = "learned"
POINTWISE = "pointwise"
PROTOCOL = campaign.PROTOCOL
FROZEN_FILES = {
    "trainer": "_bestrec_run/run_sasrec_sbert_pointwise_v1_frozen.py",
    "evaluator": "_bestrec_run/eval_fir_pointwise_v1.py",
    "runner": "_bestrec_run/run_fir_pointwise_v1.py",
    "structural_test": "_bestrec_run/test_fir_pointwise_v1.py",
    "preregistration": "PREREG_FIR_POINTWISE_V1.md",
}
# Filled and committed before launch. Hashing is over canonical LF bytes.
FROZEN_SHA256_LF = {
    "trainer": "46dbbc2f2a3c86a8410e549f92d70228edc24d0b05d66da0fa081298e2a73ac8",
    "evaluator": "0dfd22c49d2454d64960777286c29fb0dfe425e4afa0d8ded767542bd517c2c8",
    "runner": "a9a79eab4c79dddb991e549382a69c8fa0e40a330ef79f57d62eab1a3f7e103d",
    "structural_test": "6b4ae09d0e007158f2bb201758625ec2c3c14fcabc22c450a686226214aed30c",
    "preregistration": "e109ae98a825e7fb48cb2ca988c17d3a882c5e5af6fe9de1930e82e16223cfdf",
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def sha256_lf(path):
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
        t = math.copysign(math.inf, mean) if mean else 0.0
        p = 0.0 if mean else 1.0
        ci = (mean, mean)
    else:
        t = mean / se
        p = float(2.0 * stats.t.sf(abs(t), n - 1))
        q = float(stats.t.ppf(0.975, n - 1))
        ci = (mean - q * se, mean + q * se)
    return {
        "mean": mean, "sd": sd, "t": t, "df": n - 1, "p": p,
        "ci95": [float(ci[0]), float(ci[1])],
        "per_seed": [float(v) for v in d],
    }


def holm(raw):
    ordered = sorted(raw, key=raw.get)
    m = len(ordered)
    adjusted = {}
    running = 0.0
    for i, name in enumerate(ordered):
        running = max(running, (m - i) * raw[name])
        adjusted[name] = min(1.0, running)
    return {
        name: {
            "p_raw": float(raw[name]),
            "p_holm": float(adjusted[name]),
            "reject": bool(adjusted[name] < ALPHA),
        }
        for name in raw
    }


def normalized_config(cfg):
    return {k: v for k, v in cfg.items()
            if k not in {"fir_control", "seed", "out"}}


def expected_dct(width=16, dim=64):
    c = torch.arange(dim, dtype=torch.float32).view(1, -1)
    r = torch.arange(width, dtype=torch.float32).view(-1, 1)
    p = math.sqrt(2.0 / dim) * torch.cos(
        math.pi * (c + 0.5) * r / dim)
    p[0].fill_(math.sqrt(1.0 / dim))
    return p


def main():
    for role, rel in FROZEN_FILES.items():
        actual = sha256_lf(ROOT / rel)
        if actual != FROZEN_SHA256_LF[role]:
            die(f"frozen {role} digest mismatch: {actual}")

    values = {arm: {} for arm in campaign.ARMS}
    backbone_hashes = {seed: {} for seed in campaign.SEEDS}
    trainable = {}
    normalized = None
    test_split_hash = None
    missing = []
    expected_projection = expected_dct(campaign.KERNEL, 64)

    for seed in campaign.SEEDS:
        for arm in campaign.ARMS:
            run_path = Path(campaign.path_for(arm, seed))
            stem = run_path.with_suffix("")
            ckpt_path = run_path.with_suffix(".best.pt")
            final_path = run_path.with_suffix(".finaleval.json")
            users_path = run_path.with_suffix(".finaleval.users.npz")
            seal_path = run_path.with_suffix(".finaleval.started.json")
            absent = [p.name for p in (
                run_path, ckpt_path, final_path, users_path, seal_path)
                if not p.exists()]
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
            if arm == POINTWISE:
                if base.get("fir_control_profile_axis") != "pointwise_dct_feature":
                    die(f"pointwise profile axis mismatch in {run_path.name}")
            elif base.get("fir_control_profile_axis") != "lag":
                die(f"temporal profile axis mismatch in {run_path.name}")
            backbone_hashes[seed][arm] = base.get("backbone_init_sha256")
            trainable[arm] = base.get("n_trainable_params")

            ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
            state = ckpt.get("state_dict", {})
            if arm == POINTWISE:
                p = state.get("fir_control_pointwise_projection")
                w = state.get("fir_control_module.weight")
                if (p is None or w is None or p.shape != (16, 64)
                        or w.shape != (64, 16)
                        or not torch.equal(p.cpu(), expected_projection)):
                    die(f"pointwise structure mismatch in {ckpt_path.name}")
            elif "fir_control_pointwise_projection" in state:
                die(f"unexpected pointwise buffer in {ckpt_path.name}")

            prov = final.get("provenance", {})
            if (final.get("protocol") != PROTOCOL
                    or final.get("category") != campaign.CATEGORY
                    or final.get("seed") != seed
                    or final.get("arm") != arm):
                die(f"final binding mismatch in {final_path.name}")
            expected = {
                "run_json_sha256": sha256(run_path),
                "checkpoint_sha256": sha256(ckpt_path),
                "started_seal_sha256": sha256(seal_path),
                "users_sidecar_sha256": sha256(users_path),
                "trainer_sha256_lf": FROZEN_SHA256_LF["trainer"],
                "evaluator_sha256_lf": FROZEN_SHA256_LF["evaluator"],
            }
            for key, expected_value in expected.items():
                if prov.get(key) != expected_value:
                    die(f"{key} mismatch in {final_path.name}")
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
                if not np.isclose(
                        users["ndcg10"].mean(), metric, atol=1e-12):
                    die(f"per-user endpoint mismatch in {users_path.name}")
            values[arm][seed] = float(metric)

    if missing:
        print(f"NOT READY: {len(missing)} required artifact(s) missing")
        for name in missing[:12]:
            print("  -", name)
        return 3
    for seed, hashes in backbone_hashes.items():
        if None in hashes.values() or len(set(hashes.values())) != 1:
            die(f"seed {seed} lacks one shared backbone initialization: {hashes}")
    if trainable[LEARNED] != trainable[POINTWISE]:
        die("learned FIR and pointwise placebo have unequal trainable counts")

    vectors = {arm: [values[arm][s] for s in campaign.SEEDS]
               for arm in campaign.ARMS}
    contrasts = {
        "learned-identity": paired(vectors[LEARNED], vectors[IDENTITY]),
        "pointwise-identity": paired(vectors[POINTWISE], vectors[IDENTITY]),
        "learned-pointwise": paired(vectors[LEARNED], vectors[POINTWISE]),
    }
    decisions = holm({k: v["p"] for k, v in contrasts.items()})

    def positive(name):
        result, decision = contrasts[name], decisions[name]
        return bool(result["mean"] > 0 and result["ci95"][0] > 0
                    and decision["reject"])

    if not positive("learned-identity"):
        verdict = "POINTWISE-NO-REPLICATION"
    elif positive("learned-pointwise"):
        verdict = "POINTWISE-FIR-DISCRIMINATED"
    elif positive("pointwise-identity"):
        verdict = "POINTWISE-GENERIC-RESIDUAL-SUPPORTED"
    else:
        verdict = "POINTWISE-INCONCLUSIVE"

    print(f"{PROTOCOL} adjudication (mechanical first read)")
    print("ordinary paired 95% CIs; one three-test Holm family")
    for arm in campaign.ARMS:
        print(f"  {arm:10s} mean test NDCG@10 = {np.mean(vectors[arm]):.6f}")
    for name, result in contrasts.items():
        decision = decisions[name]
        print(f"  {name:22s} d={result['mean']:+.6f} "
              f"CI=[{result['ci95'][0]:+.6f},{result['ci95'][1]:+.6f}] "
              f"p={result['p']:.4g} p_Holm={decision['p_holm']:.4g} "
              f"{'reject' if decision['reject'] else 'retain'}")
    print("VERDICT:", verdict)
    print("A retained contrast is not evidence of equivalence.")

    artifact = {
        "protocol": PROTOCOL,
        "verdict": verdict,
        "scope": "internal outcome-known parameter-matched placebo study",
        "alpha": ALPHA,
        "category": campaign.CATEGORY,
        "kernel_or_width": campaign.KERNEL,
        "seeds": list(campaign.SEEDS),
        "means": {a: float(np.mean(vectors[a])) for a in campaign.ARMS},
        "values": vectors,
        "contrasts": contrasts,
        "holm": decisions,
        "positive": {name: positive(name) for name in contrasts},
        "backbone_hashes": backbone_hashes,
        "n_trainable_params": trainable,
        "test_split_sha256": test_split_hash,
        "frozen_sha256_lf": FROZEN_SHA256_LF,
    }
    out = HERE / "fir_pointwise_v1_adjudication.json"
    tmp = out.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(artifact, f, indent=2, allow_nan=False)
    os.replace(tmp, out)
    print("wrote", out)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(exc)
        raise SystemExit(2)
