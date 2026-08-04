# -*- coding: utf-8 -*-
"""Mechanical adjudicator for PREREG_FIR_V3 (E-A nonsingular FIR factorial).

Frozen alongside PREREG_FIR_V3.md BEFORE launch. Reads the 24 declared result
files, enforces the integrity gates, computes the frozen analysis (Welch +
Holm + equivalence margin), and prints exactly one frozen wording code
(W-POS / W-NEG / W-EQUIV / W-INC). Exit 0 = adjudication completed (any
direction); exit 2 = integrity gate failed; exit 3 = files missing.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ARMS = ("a0ident", "a1learned", "a2learnedwd0")
SEEDS = (20260713, 20260714, 20260715, 20260716,
         20260717, 20260718, 20260719, 20260720)
MARGIN = 0.0008
ALPHA = 0.05

ARM_EXPECT = {
    "a0ident": {"fir_v3": "frozen", "fir_v3_wd": "backbone"},
    "a1learned": {"fir_v3": "learned", "fir_v3_wd": "backbone"},
    "a2learnedwd0": {"fir_v3": "learned", "fir_v3_wd": "zero"},
}


def welch(x, y):
    nx, ny = len(x), len(y)
    mx = sum(x) / nx
    my = sum(y) / ny
    vx = sum((v - mx) ** 2 for v in x) / (nx - 1)
    vy = sum((v - my) ** 2 for v in y) / (ny - 1)
    se = math.sqrt(vx / nx + vy / ny)
    if se == 0:
        return mx - my, 0.0, float("inf"), 1.0, (mx - my, mx - my)
    t = (mx - my) / se
    df = (vx / nx + vy / ny) ** 2 / (
        (vx / nx) ** 2 / (nx - 1) + (vy / ny) ** 2 / (ny - 1))
    try:
        from scipy import stats
        p = 2.0 * stats.t.sf(abs(t), df)
        tc = stats.t.ppf(0.975, df)
    except Exception:
        p = 2.0 * 0.5 * math.erfc(abs(t) / math.sqrt(2))  # normal approx
        tc = 1.96
    est = mx - my
    return est, t, df, p, (est - tc * se, est + tc * se)


def main():
    vals = {a: {} for a in ARMS}
    init_hash = {}
    missing = []
    for arm in ARMS:
        for seed in SEEDS:
            f = os.path.join(HERE, f"results_MI_FIRV3_{arm}_seed{seed}.json")
            if not os.path.exists(f):
                missing.append(os.path.basename(f))
                continue
            d = json.load(open(f, encoding="utf-8"))
            cfg = d["config"]
            for k, v in ARM_EXPECT[arm].items():
                if cfg.get(k) != v:
                    print(f"INTEGRITY FAIL: {os.path.basename(f)} config {k}="
                          f"{cfg.get(k)!r} != {v!r}")
                    return 2
            if (cfg.get("fir_v3_kernel") != 16
                    or cfg.get("category") != "Musical_Instruments"
                    or cfg.get("epochs") != 20 or cfg.get("seed") != seed
                    or cfg.get("causal_filter")):
                print(f"INTEGRITY FAIL: {os.path.basename(f)} frozen-config "
                      "mismatch (kernel/category/epochs/seed/causal_filter)")
                return 2
            if arm == "a0ident" and d.get("fir_v3_final_l2") not in (0, 0.0):
                print(f"INTEGRITY FAIL: {os.path.basename(f)} control taps "
                      f"moved: l2={d.get('fir_v3_final_l2')}")
                return 2
            init_hash.setdefault(seed, {})[arm] = d.get("init_state_sha256")
            vals[arm][seed] = float(d["best_test"]["NDCG@10"])
    if missing:
        print(f"NOT READY: {len(missing)} of {len(ARMS)*len(SEEDS)} result "
              "files missing:")
        for m in missing:
            print("  -", m)
        return 3
    for seed, h in init_hash.items():
        if len(set(h.values())) != 1 or None in h.values():
            print(f"INTEGRITY FAIL: seed {seed} arms do NOT share one "
                  f"init_state_sha256: {h}")
            return 2

    x = {a: [vals[a][s] for s in SEEDS] for a in ARMS}
    print("PREREG_FIR_V3 adjudication (mechanical)")
    for a in ARMS:
        m = sum(x[a]) / len(x[a])
        sd = math.sqrt(sum((v - m) ** 2 for v in x[a]) / (len(x[a]) - 1))
        print(f"  {a}: mean NDCG@10 = {m:.5f}  sd = {sd:.5f}  n = {len(x[a])}")
        print(f"    per-seed: {[round(v, 5) for v in x[a]]}")

    contrasts = [
        ("A1-A0 (PRIMARY)", x["a1learned"], x["a0ident"]),
        ("A2-A0", x["a2learnedwd0"], x["a0ident"]),
        ("A2-A1", x["a2learnedwd0"], x["a1learned"]),
    ]
    rows = []
    for name, xa, xb in contrasts:
        est, t, df, p, ci = welch(xa, xb)
        # cast to native Python types (scipy returns numpy scalars, which
        # break json.dump); serialization-only, no analysis change
        rows.append({"contrast": name, "est": float(est), "t": float(t),
                     "df": float(df), "p": float(p),
                     "ci": (float(ci[0]), float(ci[1]))})
    # Holm over the three contrasts
    order = sorted(range(3), key=lambda i: rows[i]["p"])
    holm_sig = {}
    alive = True
    for rank, i in enumerate(order):
        thr = ALPHA / (3 - rank)
        sig = bool(alive and rows[i]["p"] <= thr)
        if not sig:
            alive = False
        holm_sig[i] = sig
        rows[i]["holm_threshold"] = thr
        rows[i]["holm_significant"] = sig
    for r in rows:
        print(f"  {r['contrast']}: est {r['est']:+.6f}  "
              f"[{r['ci'][0]:+.6f}, {r['ci'][1]:+.6f}]  t={r['t']:.3f} "
              f"df={r['df']:.1f} p={r['p']:.4f} "
              f"Holm-{'SIG' if r['holm_significant'] else 'ns'}")

    # paired-by-seed sensitivity (descriptive only)
    diffs = [vals["a1learned"][s] - vals["a0ident"][s] for s in SEEDS]
    md = sum(diffs) / len(diffs)
    sdd = math.sqrt(sum((v - md) ** 2 for v in diffs) / (len(diffs) - 1))
    print(f"  paired-by-seed A1-A0 (descriptive): mean {md:+.6f} sd {sdd:.6f}")

    prim = rows[0]
    lo, hi = prim["ci"]
    if prim["holm_significant"] and prim["est"] > 0:
        verdict = "W-POS"
    elif prim["holm_significant"] and prim["est"] < 0:
        verdict = "W-NEG"
    elif -MARGIN < lo and hi < MARGIN:
        verdict = "W-EQUIV"
    else:
        verdict = "W-INC"
    print(f"VERDICT: {verdict} (margin ±{MARGIN}; wording frozen in "
          "PREREG_FIR_V3.md §6)")

    outp = os.path.join(HERE, "fir_v3_adjudication.json")
    with open(outp, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"verdict": verdict, "margin": MARGIN, "alpha": ALPHA,
                   "contrasts": rows, "per_arm": vals,
                   "paired_descriptive": {"mean": md, "sd": sdd},
                   "init_hash_by_seed": init_hash}, f, indent=2)
    print(f"wrote {outp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
