# -*- coding: utf-8 -*-
"""Mechanical adjudicator for PREREG_COLDFUSE_V2 (E-G2), frozen BEFORE
launch. First reader of every test value (sequestered design). Exit 0 =
adjudication completed; 2 = integrity failure; 3 = not ready."""
import glob
import itertools
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SEEDS = (20260741, 20260742, 20260743, 20260744,
         20260745, 20260746, 20260747, 20260748)
CATS = {
    "MI": ("Musical_Instruments", True,
           "results_MI_V2_ls02_filter16_seed20260608.json"),
    "IS": ("Industrial_and_Scientific", True,
           "results_FIRB_Industrial_and_Scientific_filter_seed20260713.json"),
    "VG": ("Video_Games", True,
           "results_V2_ls02_filter8_seed20260610_VG.json"),
    "OFFICE": ("Office_Products", False,
               "results_OFFICEV3_k16_seed20260728.json"),
    "CDS": ("CDs_and_Vinyl", False,
            "results_FIRB_CDs_and_Vinyl_filter_seed20260713.json"),
}
SAME_ERA_REF = "results_FIRB_Industrial_and_Scientific_filter_seed20260713.json"
EXEMPT = {"seed", "out", "save_ckpt", "no_test_eval",
          "fir_v3", "fir_v3_kernel", "fir_v3_wd"}
T_SET = (0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.6)
MH_SET = (0.0, 0.05, 0.1)
G_OVER, G_MID, G_HEAD = 0.0002, 0.0010, 0.0005
F15_MARGIN = 0.0005
COST_GATES = {"overall": -0.0005, "mid": -0.0015, "head": -0.0008}
ALPHA = 0.05


def cand_keys():
    ks = set()
    for prof in ("uniform", "exp0.9"):
        for t in T_SET:
            for m in MH_SET:
                for h in MH_SET:
                    if t >= m >= h:
                        ks.add(json.dumps({"profile": prof, "wt_tail": t,
                                           "wt_mid": m, "wt_head": h},
                                          sort_keys=True))
    return ks


def sign_p(deltas):
    d = [v for v in deltas if v != 0]
    n = len(d)
    if n == 0:
        return 1.0
    k = sum(1 for v in d if v > 0)
    cdf = lambda x: sum(math.comb(n, i) for i in range(0, x + 1)) / 2.0 ** n
    return min(1.0, 2.0 * min(cdf(k), 1.0 - cdf(k - 1) if k >= 1 else 1.0))


def t_ci(vals, label):
    n = len(vals)
    m = sum(vals) / n
    sd = math.sqrt(sum((v - m) ** 2 for v in vals) / (n - 1))
    if sd == 0:
        print(f"INTEGRITY FAIL: zero SD for {label}")
        sys.exit(2)
    se = sd / math.sqrt(n)
    t = m / se
    try:
        from scipy import stats
        p = float(2.0 * stats.t.sf(abs(t), n - 1))
        tc = float(stats.t.ppf(0.975, n - 1))
    except Exception:
        print("FATAL: SciPy required.")
        sys.exit(2)
    return m, sd, float(t), p, (float(m - tc * se), float(m + tc * se))


def main():
    CK = cand_keys()
    era = json.load(open(os.path.join(HERE, SAME_ERA_REF),
                         encoding="utf-8"))["config"]
    missing, data, era_seen = [], {c: [] for c in CATS}, {}
    decl_b = {f"results_{t}_COLDFUSE2_base_seed{s}.json"
              for t in CATS for s in SEEDS}
    decl_c = {f"results_{CATS[t][0]}_COLDFUSE2_confirm_seed{s}.json"
              for t in CATS for s in SEEDS}
    got_b = {os.path.basename(p) for p in glob.glob(os.path.join(
        HERE, "results_*_COLDFUSE2_base_seed*.json"))
        if not p.endswith(".fusion.json")}
    got_c = {os.path.basename(p) for p in glob.glob(os.path.join(
        HERE, "results_*_COLDFUSE2_confirm_seed*.json"))}
    und = sorted((got_b - decl_b) | (got_c - decl_c))
    if und:
        print(f"INTEGRITY FAIL: undeclared files {und}")
        return 2
    if not os.path.exists(os.path.join(HERE, "attempts",
                                       "eg2_ledger.jsonl")):
        print("INTEGRITY FAIL: OPS ledger missing")
        return 2

    for tag, (cat, use_ease, ref_name) in CATS.items():
        ref_cfg = json.load(open(os.path.join(HERE, ref_name),
                                 encoding="utf-8"))["config"]
        for seed in SEEDS:
            b = os.path.join(HERE,
                             f"results_{tag}_COLDFUSE2_base_seed{seed}.json")
            cj = os.path.join(
                HERE, f"results_{cat}_COLDFUSE2_confirm_seed{seed}.json")
            fj = b[:-5] + ".fusion.json"
            need = [b, cj] + ([fj] if use_ease else [])
            if not all(os.path.exists(x) for x in need):
                missing += [os.path.basename(x) for x in need
                            if not os.path.exists(x)]
                continue
            base = json.load(open(b, encoding="utf-8"))
            cfg = base["config"]
            if base.get("best_test") is not None:
                print(f"INTEGRITY FAIL: test NOT sequestered in "
                      f"{os.path.basename(b)}")
                return 2
            if not base.get("best_ckpt_sha256"):
                print(f"INTEGRITY FAIL: no best_ckpt_sha256 in "
                      f"{os.path.basename(b)}")
                return 2
            bad = [k for k in set(ref_cfg) - EXEMPT
                   if cfg.get(k, "__MISSING__") != ref_cfg[k]]
            extras = sorted(set(cfg) - set(ref_cfg) - EXEMPT)
            for k in extras:
                if k not in era or cfg[k] != era[k]:
                    bad.append(f"extra:{k}")
                if era_seen.setdefault(k, cfg[k]) != cfg[k]:
                    bad.append(f"inconsistent:{k}")
            if bad:
                print(f"INTEGRITY FAIL: config gate {bad[:6]} in "
                      f"{os.path.basename(b)}")
                return 2
            if cfg.get("seed") != seed or cfg.get("category") != cat:
                print(f"INTEGRITY FAIL: echo in {os.path.basename(b)}")
                return 2
            if use_ease:
                fus = json.load(open(fj, encoding="utf-8"))
                if not fus.get("val_only") or fus.get("test") is not None:
                    print(f"INTEGRITY FAIL: fusion not val-only in "
                          f"{os.path.basename(fj)}")
                    return 2
            conf = json.load(open(cj, encoding="utf-8"))
            sweep = conf["val_sweep"]
            if set(sweep) - {"REF"} != CK:
                print(f"INTEGRITY FAIL: sweep identity in "
                      f"{os.path.basename(cj)}")
                return 2
            for r in sweep.values():
                for mk in ("overall", "f15", "mid", "head"):
                    if not math.isfinite(float(r[mk])):
                        print(f"INTEGRITY FAIL: non-finite sweep in "
                              f"{os.path.basename(cj)}")
                        return 2
            ref_v = sweep["REF"]
            best_key, best_f15 = None, None
            for name, r in sweep.items():
                if name == "REF":
                    continue
                if (r["overall"] >= ref_v["overall"] - G_OVER
                        and r["mid"] >= ref_v["mid"] - G_MID
                        and r["head"] >= ref_v["head"] - G_HEAD
                        and (best_f15 is None or r["f15"] > best_f15)):
                    best_key, best_f15 = name, r["f15"]
            rec_sel = (json.dumps(conf["selected"], sort_keys=True)
                       if conf["selected"] else None)
            if best_key != rec_sel:
                print(f"INTEGRITY FAIL: guardrail argmax mismatch in "
                      f"{os.path.basename(cj)}")
                return 2
            t = conf["test"]
            npz = np.load(cj[:-5] + ".perusers.npz")
            users = npz["users"]
            tb = npz["target_bin4"]
            n = t["REF"]["n"]
            if (len(users) != n or len(np.unique(users)) != n
                    or not bool((np.diff(users) > 0).all())
                    or tb.min() < 0 or tb.max() > 3):
                print(f"INTEGRITY FAIL: NPZ structure in "
                      f"{os.path.basename(cj)}")
                return 2
            for name in t:
                arr = npz[f"{name}_ndcg"]
                if (abs(float(arr.mean()) - t[name]["overall"]) > 1e-6
                        or abs(float(arr[tb == 1].mean()) - t[name]["f15"])
                        > 1e-6):
                    print(f"INTEGRITY FAIL: NPZ reconstruction ({name}) in "
                          f"{os.path.basename(cj)}")
                    return 2
            if "SEL" not in t:
                data[tag].append({"seed": seed, "structural_null": True})
                continue
            data[tag].append({
                "seed": seed, "structural_null": False,
                "selected": conf["selected"],
                "f15_delta": t["SEL"]["f15"] - t["REF"]["f15"],
                "overall_delta": t["SEL"]["overall"] - t["REF"]["overall"],
                "mid_delta": t["SEL"]["mid"] - t["REF"]["mid"],
                "head_delta": t["SEL"]["head"] - t["REF"]["head"],
                "f0_sel": t["SEL"]["f0"], "f0_ref": t["REF"]["f0"],
                "c1_delta": t["C1_freqonly"]["f15"] - t["REF"]["f15"],
                "c2_delta": t["C2_random"]["f15"] - t["REF"]["f15"],
                "c3_delta": t["C3_permuted"]["f15"] - t["REF"]["f15"]})
    if missing:
        print(f"NOT READY: {len(missing)} files missing")
        for m in sorted(set(missing))[:12]:
            print("  -", m)
        return 3

    print("PREREG_COLDFUSE_V2 adjudication (mechanical; first reader of the "
          "sequestered test values)")
    rows = {}
    for tag in CATS:
        rs = [r for r in data[tag] if not r.get("structural_null")]
        if len(rs) < len(SEEDS):
            print(f"  {tag}: {len(SEEDS)-len(rs)} structural nulls")
        d = [r["f15_delta"] for r in rs]
        m, sd, t_, p, ci = t_ci(d, f"{tag} f15")
        rows[tag] = {"f15": {"mean": m, "sd": sd, "t": t_, "p": p, "ci": ci,
                             "sign_p": sign_p(d)},
                     "n_used": len(rs)}
        for mkey, cg in COST_GATES.items():
            vals = [r[f"{mkey}_delta"] for r in rs]
            mm, _, _, _, cci = t_ci(vals, f"{tag} {mkey}")
            rows[tag][mkey] = {"mean": mm, "ci": cci,
                               "gate_pass": bool(cci[0] > cg)}
        c1 = sum(r["c1_delta"] for r in rs) / len(rs)
        c2 = [r["f15_delta"] - r["c2_delta"] for r in rs]
        c3 = [r["f15_delta"] - r["c3_delta"] for r in rs]
        c3_share = (sum(r["c3_delta"] for r in rs) / len(rs)) / m if m else 0
        rows[tag]["controls"] = {
            "c1_share": c1 / m if m else None,
            "sel_minus_random": t_ci(c2, f"{tag} selVSrand")[0],
            "sel_minus_permuted": t_ci(c3, f"{tag} selVSperm")[0],
            "permuted_share": c3_share}
        f0_moved = any(abs(r["f0_sel"] - r["f0_ref"]) > 1e-12 for r in rs)
        rows[tag]["f0_moved"] = bool(f0_moved)
        print(f"  {tag}: f15 {m:+.5f} [{ci[0]:+.5f},{ci[1]:+.5f}] t={t_:.2f} "
              f"p={p:.2e} sign-p={rows[tag]['f15']['sign_p']:.4f} | "
              f"cost gates "
              f"{[k for k in COST_GATES if not rows[tag][k]['gate_pass']] or 'all pass'}"
              f" | C1 share {rows[tag]['controls']['c1_share']:.2f} "
              f"perm share {c3_share:.2f} | f0 moved: {f0_moved}")
    order = sorted(CATS, key=lambda c: rows[c]["f15"]["p"])
    alive = True
    for rank, c in enumerate(order):
        thr = ALPHA / (5 - rank)
        sig = bool(alive and rows[c]["f15"]["p"] <= thr)
        if not sig:
            alive = False
        rows[c]["holm_significant"] = sig
    sem_fail = sum(1 for c in CATS
                   if rows[c]["controls"]["permuted_share"] is not None
                   and rows[c]["controls"]["permuted_share"] >= 0.5)
    verdicts = {}
    for c in CATS:
        r = rows[c]
        lo, hi = r["f15"]["ci"]
        gates_ok = all(r[k]["gate_pass"] for k in COST_GATES)
        if r["holm_significant"] and r["f15"]["mean"] > 0:
            verdicts[c] = "W2-POS" if gates_ok else "W2-POS-COST"
        elif r["holm_significant"] and r["f15"]["mean"] < 0:
            verdicts[c] = "W2-NEG"
        elif -F15_MARGIN < lo and hi < F15_MARGIN:
            verdicts[c] = "W2-EQUIV"
        else:
            verdicts[c] = "W2-INC"
        print(f"VERDICT {c}: {verdicts[c]}")
    family = ("W2-SEM-FAIL" if sem_fail >= 3 else "semantic-alignment "
              "interpretation retained")
    print(f"FAMILY: {family} (permuted>=50% on {sem_fail}/5)")

    outp = os.path.join(HERE, "coldfuse_v2_adjudication.json")
    with open(outp, "w", encoding="utf-8") as f:
        json.dump({"verdicts": verdicts, "family_semantic": family,
                   "rows": rows, "alpha": ALPHA, "margin": F15_MARGIN,
                   "cost_gates": COST_GATES}, f, indent=2)
    print(f"wrote {outp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
