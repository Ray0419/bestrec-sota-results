# -*- coding: utf-8 -*-
"""Mechanical adjudicator for PREREG_COLDFUSE_V1 (E-G stage 2).

Frozen alongside PREREG_COLDFUSE_V1.md BEFORE launch. Enforces integrity
gates; computes the frozen analysis (per-category paired t on per-seed
tail-bin deltas, Holm across five categories, +/-0.0005 tail margin,
-0.0005 overall-cost margin); prints one frozen wording code per category.
Exit 0 = adjudication completed; 2 = integrity failure; 3 = not ready.
"""
import itertools
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SEEDS = (20260736, 20260737, 20260738, 20260739, 20260740)
CATS = {
    "MI": ("Musical_Instruments", True),
    "IS": ("Industrial_and_Scientific", True),
    "VG": ("Video_Games", True),
    "OFFICE": ("Office_Products", False),
    "CDS": ("CDs_and_Vinyl", False),
}
WSET = {0.0, 0.05, 0.1, 0.2}
TAIL_MARGIN = 0.0005
COST_MARGIN = -0.0005
ALPHA = 0.05


def t_ci(vals):
    n = len(vals)
    m = sum(vals) / n
    sd = math.sqrt(sum((v - m) ** 2 for v in vals) / (n - 1))
    se = sd / math.sqrt(n)
    t = m / se if se > 0 else float("inf")
    try:
        from scipy import stats
        p = float(2.0 * stats.t.sf(abs(t), n - 1))
        tc = float(stats.t.ppf(0.975, n - 1))
    except Exception:
        p = 2.0 * 0.5 * math.erfc(abs(t) / math.sqrt(2))
        tc = 2.776
    return m, sd, float(t), p, (m - tc * se, m + tc * se)


def main():
    missing = []
    data = {c: [] for c in CATS}
    for tag, (cat, use_ease) in CATS.items():
        for seed in SEEDS:
            b = os.path.join(HERE, f"results_{tag}_COLDFUSE_base_seed{seed}.json")
            cj = os.path.join(HERE,
                              f"results_{cat}_COLDFUSE_confirm_seed{seed}.json")
            if not (os.path.exists(b) and os.path.exists(cj)):
                missing.append(os.path.basename(cj))
                continue
            base = json.load(open(b, encoding="utf-8"))
            conf = json.load(open(cj, encoding="utf-8"))
            sel = conf["selected"]
            if not (sel["wt_tail"] in WSET and sel["wt_mid"] in WSET
                    and sel["wt_head"] in WSET
                    and sel["wt_tail"] >= sel["wt_mid"] >= sel["wt_head"]
                    and sel["profile"] in ("uniform", "exp0.9")):
                print(f"INTEGRITY FAIL: off-grid selection {sel} in "
                      f"{os.path.basename(cj)}")
                return 2
            if conf.get("noninferiority") != 0.0002:
                print(f"INTEGRITY FAIL: wrong selection constraint in "
                      f"{os.path.basename(cj)}")
                return 2
            if conf["test"]["reference"]["n"] != base["best_test"]["n_eval"]:
                print(f"INTEGRITY FAIL: n_eval mismatch in "
                      f"{os.path.basename(cj)}")
                return 2
            drift = abs(conf["test"]["reference"]["overall"]
                        - conf["expected_ref_overall"])
            if drift >= 0.0005:
                print(f"INTEGRITY FAIL: reconstruction drift {drift:.5f} in "
                      f"{os.path.basename(cj)}")
                return 2
            if base["config"].get("seed") != seed or \
                    base["config"].get("category") != cat:
                print(f"INTEGRITY FAIL: config echo in {os.path.basename(b)}")
                return 2
            if (conf["reference"] == "fused2") != use_ease:
                print(f"INTEGRITY FAIL: reference kind in "
                      f"{os.path.basename(cj)}")
                return 2
            data[tag].append({
                "seed": seed, "selected": sel,
                "tail_delta": conf["test"]["selected"]["tail"]
                - conf["test"]["reference"]["tail"],
                "overall_delta": conf["test"]["selected"]["overall"]
                - conf["test"]["reference"]["overall"],
                "ref_tail": conf["test"]["reference"]["tail"],
                "sel_tail": conf["test"]["selected"]["tail"],
                "n_tail": conf["test"]["reference"]["n_tail"]})
    if missing:
        print(f"NOT READY: {len(missing)} confirm files missing:")
        for m in missing:
            print("  -", m)
        return 3

    print("PREREG_COLDFUSE_V1 adjudication (mechanical)")
    rows = {}
    for tag in CATS:
        td = [r["tail_delta"] for r in data[tag]]
        od = [r["overall_delta"] for r in data[tag]]
        m, sd, t, p, ci = t_ci(td)
        mo, sdo, to_, po, cio = t_ci(od)
        rows[tag] = {"tail": {"mean": m, "sd": sd, "t": t, "p": p, "ci": ci},
                     "overall": {"mean": mo, "ci": cio},
                     "no_material_cost": bool(cio[0] > COST_MARGIN),
                     "per_seed": data[tag]}
        print(f"  {tag}: tail delta {m:+.5f} [{ci[0]:+.5f}, {ci[1]:+.5f}] "
              f"t={t:.2f} p={p:.4f} | overall {mo:+.5f} "
              f"[{cio[0]:+.5f}, {cio[1]:+.5f}] "
              f"{'no-material-cost' if rows[tag]['no_material_cost'] else 'COST EXCEEDS MARGIN'}")
        for r in data[tag]:
            print(f"    seed {r['seed']}: ref tail {r['ref_tail']:.5f} -> "
                  f"sel {r['sel_tail']:.5f} (n_tail {r['n_tail']:,}; "
                  f"{r['selected']['profile']} "
                  f"{r['selected']['wt_tail']}/{r['selected']['wt_mid']}/"
                  f"{r['selected']['wt_head']})")
    order = sorted(CATS, key=lambda c: rows[c]["tail"]["p"])
    alive = True
    for rank, c in enumerate(order):
        thr = ALPHA / (5 - rank)
        sig = bool(alive and rows[c]["tail"]["p"] <= thr)
        if not sig:
            alive = False
        rows[c]["holm_significant"] = sig
    verdicts = {}
    for c in CATS:
        r = rows[c]
        lo, hi = r["tail"]["ci"]
        if r["holm_significant"] and r["tail"]["mean"] > 0:
            verdicts[c] = "W-C-POS"
        elif r["holm_significant"] and r["tail"]["mean"] < 0:
            verdicts[c] = "W-C-NEG"
        elif -TAIL_MARGIN < lo and hi < TAIL_MARGIN:
            verdicts[c] = "W-C-EQUIV"
        else:
            verdicts[c] = "W-C-INC"
        print(f"VERDICT {c}: {verdicts[c]}")

    outp = os.path.join(HERE, "coldfuse_v1_adjudication.json")
    with open(outp, "w", encoding="utf-8") as f:
        json.dump({"verdicts": verdicts, "tail_margin": TAIL_MARGIN,
                   "cost_margin": COST_MARGIN, "alpha": ALPHA, "rows": rows},
                  f, indent=2)
    print(f"wrote {outp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
