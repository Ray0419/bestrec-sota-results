# -*- coding: utf-8 -*-
"""Mechanical adjudicator for PREREG_HYBRID_V1 (E-F EASE late-fusion hybrid).

Frozen alongside PREREG_HYBRID_V1.md BEFORE launch. Enforces the integrity
gates, computes the frozen analysis (per-category paired t on per-seed
fused-minus-seq deltas, Holm across the three categories, +/-0.0005
equivalence margin), and prints one frozen wording code per category plus
the descriptive published-comparator and ensemble lines. Exit 0 =
adjudication completed; exit 2 = integrity failure; exit 3 = files missing.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SEEDS = (20260721, 20260722, 20260723, 20260724, 20260725)
CATS = ("MI", "IS", "VG")
L2_GRID = {50.0, 100.0, 200.0, 500.0}
W_GRID = {0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.075, 0.1}
MARGIN = 0.0005
ALPHA = 0.05
PUB = {"MI": 0.0406, "VG": 0.0760}
REFS = {
    "MI": "results_MI_V2_ls02_filter16_seed20260608.json",
    "IS": "results_FIRB_Industrial_and_Scientific_filter_seed20260713.json",
    "VG": "results_V2_ls02_filter8_seed20260610_VG.json",
}
EXCLUDE = {"seed", "out", "save_ckpt", "fir_v3", "fir_v3_kernel", "fir_v3_wd"}


def t_p_two_sided(t, df):
    try:
        from scipy import stats
        return 2.0 * stats.t.sf(abs(t), df), stats.t.ppf(0.975, df)
    except Exception:
        return 2.0 * 0.5 * math.erfc(abs(t) / math.sqrt(2)), 2.776  # df=4


def main():
    missing = []
    deltas = {c: [] for c in CATS}
    fused_means = {c: [] for c in CATS}
    details = {c: [] for c in CATS}
    for c in CATS:
        ref_cfg = json.load(open(os.path.join(HERE, REFS[c]),
                                 encoding="utf-8"))["config"]
        for seed in SEEDS:
            b = os.path.join(HERE, f"results_{c}_HYBRIDV1_base_seed{seed}.json")
            f = b[:-5] + ".fusion.json"
            if not os.path.exists(b) or not os.path.exists(f):
                missing.append(os.path.basename(f))
                continue
            base = json.load(open(b, encoding="utf-8"))
            fus = json.load(open(f, encoding="utf-8"))
            cfg = base["config"]
            # gate 5: config echo equals reference minus excluded keys
            for k in set(ref_cfg) - EXCLUDE:
                if cfg.get(k) != ref_cfg[k]:
                    print(f"INTEGRITY FAIL: {os.path.basename(b)} config "
                          f"{k}={cfg.get(k)!r} != ref {ref_cfg[k]!r}")
                    return 2
            if cfg.get("seed") != seed:
                print(f"INTEGRITY FAIL: seed mismatch in {os.path.basename(b)}")
                return 2
            sel = fus["selected"]
            if float(sel["l2"]) not in L2_GRID or float(sel["w"]) not in W_GRID:
                print(f"INTEGRITY FAIL: off-grid selection {sel} in "
                      f"{os.path.basename(f)}")
                return 2
            n_eval = fus["test"]["n_eval"]
            if n_eval != base["best_test"]["n_eval"] or (c == "MI"
                                                         and n_eval != 57439):
                print(f"INTEGRITY FAIL: n_eval {n_eval} mismatch in "
                      f"{os.path.basename(f)}")
                return 2
            seq = fus["test"]["seq_only"]["ndcg"]
            fzd = fus["test"]["fused"]["ndcg"]
            rec = base["best_test"]["NDCG@10"]
            if abs(seq - rec) >= 0.0005:
                print(f"INTEGRITY FAIL: reconstruction drift "
                      f"|{seq:.5f}-{rec:.5f}| >= 0.0005 in "
                      f"{os.path.basename(f)}")
                return 2
            deltas[c].append(fzd - seq)
            fused_means[c].append(fzd)
            details[c].append({"seed": seed, "seq": seq, "fused": fzd,
                               "l2": sel["l2"], "w": sel["w"]})
    if missing:
        print(f"NOT READY: {len(missing)} fusion files missing:")
        for m in missing:
            print("  -", m)
        return 3

    print("PREREG_HYBRID_V1 adjudication (mechanical)")
    rows = {}
    for c in CATS:
        d = deltas[c]
        m = sum(d) / len(d)
        sd = math.sqrt(sum((v - m) ** 2 for v in d) / (len(d) - 1))
        se = sd / math.sqrt(len(d))
        t = m / se if se > 0 else float("inf")
        p, tc = t_p_two_sided(t, len(d) - 1)
        # native casts (scipy returns numpy scalars; json.dump rejects them)
        p, tc = float(p), float(tc)
        ci = (float(m - tc * se), float(m + tc * se))
        rows[c] = {"mean_delta": m, "sd": sd, "t": t, "p": p, "ci": ci,
                   "per_seed": details[c],
                   "fused_mean": sum(fused_means[c]) / len(fused_means[c])}
        print(f"  {c}: mean delta {m:+.5f}  [{ci[0]:+.5f}, {ci[1]:+.5f}]  "
              f"t={t:.2f} p={p:.4f}  fused mean {rows[c]['fused_mean']:.5f}")
        for r in details[c]:
            print(f"    seed {r['seed']}: seq {r['seq']:.5f} -> "
                  f"fused {r['fused']:.5f} (l2={r['l2']}, w={r['w']})")
    order = sorted(CATS, key=lambda c: rows[c]["p"])
    alive = True
    for rank, c in enumerate(order):
        thr = ALPHA / (3 - rank)
        sig = bool(alive and rows[c]["p"] <= thr)
        if not sig:
            alive = False
        rows[c]["holm_significant"] = sig
    verdicts = {}
    for c in CATS:
        r = rows[c]
        lo, hi = r["ci"]
        if r["holm_significant"] and r["mean_delta"] > 0:
            verdicts[c] = "W-H-POS"
        elif r["holm_significant"] and r["mean_delta"] < 0:
            verdicts[c] = "W-H-NEG"
        elif -MARGIN < lo and hi < MARGIN:
            verdicts[c] = "W-H-EQUIV"
        else:
            verdicts[c] = "W-H-INC"
        print(f"VERDICT {c}: {verdicts[c]}")
        if c in PUB:
            rel = "exceeds" if r["fused_mean"] > PUB[c] else "remains below"
            print(f"  [W-H-PUB-{c}] fused 5-seed mean {r['fused_mean']:.5f} "
                  f"{rel} published {PUB[c]}")
    ens_path = os.path.join(HERE, "results_MI_HYBRIDV1_ensemble5.json")
    ens = None
    if os.path.exists(ens_path):
        e = json.load(open(ens_path, encoding="utf-8"))
        ens = e["test"]["ensemble_fused"]["ndcg"]
        print(f"  [W-H-ENS] MI ensemble5 fused NDCG@10 = {ens:.5f} "
              f"(single evaluation, ensemble frame)")
    else:
        print("  [W-H-ENS] ensemble file absent (secondary; noted)")

    outp = os.path.join(HERE, "hybrid_v1_adjudication.json")
    with open(outp, "w", encoding="utf-8") as fo:
        json.dump({"verdicts": verdicts, "margin": MARGIN, "alpha": ALPHA,
                   "rows": rows, "published": PUB, "ensemble_mi": ens},
                  fo, indent=2)
    print(f"wrote {outp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
