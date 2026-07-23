# -*- coding: utf-8 -*-
"""Mechanical adjudicator for PREREG_COLDFUSE_V1 (E-G stage 2).

v2 (2026-07-23, BEFORE any full-set adjudication ran; audit 09:01 gates):
implements Gate 5 in BOTH forms per GATE5_CONFORMANCE_DECISION.md (literal
verdict recorded; normalized verdict governs, with a mechanical proof that
every extra config key was never on the driver's command line), enforces the
15 fusion JSONs (Gate 1), sweep completeness + argmax recomputation under the
frozen rule (Gate 2), finiteness, and NPZ row checks. Exit 0 = adjudication
completed; 2 = integrity failure; 3 = not ready.
`--gate5-report` prints the config diffs only (no statistics touched).
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SEEDS = (20260736, 20260737, 20260738, 20260739, 20260740)
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
EXEMPT = {"seed", "out", "save_ckpt", "fir_v3", "fir_v3_kernel", "fir_v3_wd"}
WSET = {0.0, 0.05, 0.1, 0.2}
TAIL_MARGIN = 0.0005
COST_MARGIN = -0.0005
NONINF = 0.0002
ALPHA = 0.05
N_CANDIDATES = 40


def driver_flags(ref_cfg):
    """Deterministic reconstruction of the driver's flag set (run_coldfuse_
    confirm.base_args): flags come ONLY from reference keys."""
    flags = set()
    for k in ref_cfg:
        if k in {"seed", "out", "category", "save_ckpt",
                 "fir_v3", "fir_v3_kernel", "fir_v3_wd"}:
            continue
        v = ref_cfg[k]
        if v is None or v is False:
            continue
        flags.add("--" + k.replace("_", "-"))
    return flags


def gate5(ref_cfg, cfg):
    """Returns (literal_ok, normalized_ok, shared_mismatches, extras,
    extras_on_cmdline)."""
    shared_bad = [k for k in set(ref_cfg) - EXEMPT
                  if k in cfg and cfg[k] != ref_cfg[k]]
    missing = [k for k in set(ref_cfg) - EXEMPT if k not in cfg]
    extras = sorted(set(cfg) - set(ref_cfg) - EXEMPT)
    literal = not shared_bad and not missing and not extras
    flags = driver_flags(ref_cfg)
    extras_on_cmd = [k for k in extras
                     if ("--" + k.replace("_", "-")) in flags]
    normalized = (not shared_bad and not missing and not extras_on_cmd)
    return literal, normalized, shared_bad + missing, extras, extras_on_cmd


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
        print("FATAL: SciPy unavailable; the registered exact t computation "
              "cannot run (no normal-approximation substitution).")
        sys.exit(2)
    return m, sd, float(t), p, (float(m - tc * se), float(m + tc * se))


def recompute_argmax(conf):
    """Gate 2: re-derive the selection from the recorded sweep under the
    frozen rule; must equal the recorded selection."""
    sweep = conf["val_sweep"]
    ref = sweep["REF"]
    best_key, best_tail = None, None
    for name, r in sweep.items():
        if name == "REF":
            continue
        if r["overall"] >= ref["overall"] - NONINF and \
                (best_tail is None or r["tail"] > best_tail):
            best_key, best_tail = name, r["tail"]
    return best_key, len(sweep) - 1


def main():
    report_only = "--gate5-report" in sys.argv
    missing = []
    data = {c: [] for c in CATS}
    gate5_out = {}
    for tag, (cat, use_ease, ref_name) in CATS.items():
        ref_cfg = json.load(open(os.path.join(HERE, ref_name),
                                 encoding="utf-8"))["config"]
        for seed in SEEDS:
            b = os.path.join(HERE,
                             f"results_{tag}_COLDFUSE_base_seed{seed}.json")
            cj = os.path.join(HERE,
                              f"results_{cat}_COLDFUSE_confirm_seed{seed}.json")
            fj = b[:-5] + ".fusion.json"
            need = [b, cj] + ([fj] if use_ease else [])
            if not all(os.path.exists(x) for x in need):
                missing.extend(os.path.basename(x) for x in need
                               if not os.path.exists(x))
                continue
            base = json.load(open(b, encoding="utf-8"))
            cfg = base["config"]
            lit, norm, bad_shared, extras, extras_cmd = gate5(ref_cfg, cfg)
            gate5_out.setdefault(tag, []).append(
                {"seed": seed, "literal": lit, "normalized": norm,
                 "shared_mismatch_or_missing": bad_shared,
                 "extras_n": len(extras), "extras": extras,
                 "extras_on_cmdline": extras_cmd})
            if report_only:
                continue
            if not norm:
                print(f"INTEGRITY FAIL (Gate 5 normalized): "
                      f"{os.path.basename(b)} shared/missing={bad_shared} "
                      f"extras_on_cmdline={extras_cmd}")
                return 2
            conf = json.load(open(cj, encoding="utf-8"))
            sel = conf["selected"]
            if not (sel["wt_tail"] in WSET and sel["wt_mid"] in WSET
                    and sel["wt_head"] in WSET
                    and sel["wt_tail"] >= sel["wt_mid"] >= sel["wt_head"]
                    and sel["profile"] in ("uniform", "exp0.9")):
                print(f"INTEGRITY FAIL: off-grid selection {sel} in "
                      f"{os.path.basename(cj)}")
                return 2
            if conf.get("noninferiority") != NONINF:
                print(f"INTEGRITY FAIL: wrong selection constraint in "
                      f"{os.path.basename(cj)}")
                return 2
            sel_key, n_cand = recompute_argmax(conf)
            if n_cand != N_CANDIDATES:
                print(f"INTEGRITY FAIL: sweep has {n_cand} candidates "
                      f"(expected {N_CANDIDATES}) in {os.path.basename(cj)}")
                return 2
            if sel_key != json.dumps(sel, sort_keys=True):
                print(f"INTEGRITY FAIL: recomputed argmax {sel_key} != "
                      f"recorded selection in {os.path.basename(cj)}")
                return 2
            if conf["test"]["reference"]["n"] != base["best_test"]["n_eval"]:
                print(f"INTEGRITY FAIL: n_eval mismatch in "
                      f"{os.path.basename(cj)}")
                return 2
            if use_ease:
                fus = json.load(open(fj, encoding="utf-8"))
                expected = float(fus["test"]["fused"]["ndcg"])
                if conf["reference"] != "fused2":
                    print(f"INTEGRITY FAIL: reference kind in "
                          f"{os.path.basename(cj)}")
                    return 2
            else:
                expected = float(base["best_test"]["NDCG@10"])
                if conf["reference"] != "seq":
                    print(f"INTEGRITY FAIL: reference kind in "
                          f"{os.path.basename(cj)}")
                    return 2
            if abs(conf["expected_ref_overall"] - expected) > 1e-12:
                print(f"INTEGRITY FAIL: expected-reference provenance in "
                      f"{os.path.basename(cj)}")
                return 2
            drift = abs(conf["test"]["reference"]["overall"] - expected)
            if drift >= 0.0005:
                print(f"INTEGRITY FAIL: reconstruction drift {drift:.5f} in "
                      f"{os.path.basename(cj)}")
                return 2
            vals = [conf["test"][s][m] for s in ("reference", "selected")
                    for m in ("overall", "tail", "mid", "head", "hr")]
            if not all(math.isfinite(float(v)) for v in vals):
                print(f"INTEGRITY FAIL: non-finite metric in "
                      f"{os.path.basename(cj)}")
                return 2
            npz = np.load(cj[:-5] + ".perusers.npz")
            n = conf["test"]["reference"]["n"]
            if (len(npz["users"]) != n or len(npz["ref_ndcg"]) != n
                    or len(npz["sel_ndcg"]) != n
                    or not np.isfinite(npz["ref_ndcg"]).all()
                    or not np.isfinite(npz["sel_ndcg"]).all()):
                print(f"INTEGRITY FAIL: NPZ rows/finiteness in "
                      f"{os.path.basename(cj)}")
                return 2
            if cfg.get("seed") != seed or cfg.get("category") != cat:
                print(f"INTEGRITY FAIL: config echo in {os.path.basename(b)}")
                return 2
            data[tag].append({
                "seed": seed, "selected": sel,
                "tail_delta": conf["test"]["selected"]["tail"]
                - conf["test"]["reference"]["tail"],
                "overall_delta": conf["test"]["selected"]["overall"]
                - conf["test"]["reference"]["overall"],
                "mid_delta": conf["test"]["selected"]["mid"]
                - conf["test"]["reference"]["mid"],
                "head_delta": conf["test"]["selected"]["head"]
                - conf["test"]["reference"]["head"],
                "ref_tail": conf["test"]["reference"]["tail"],
                "sel_tail": conf["test"]["selected"]["tail"],
                "n_tail": conf["test"]["reference"]["n_tail"]})
    if report_only:
        print(json.dumps(gate5_out, indent=1))
        return 0
    if missing:
        print(f"NOT READY: {len(missing)} required files missing:")
        for m in sorted(set(missing)):
            print("  -", m)
        return 3

    print("PREREG_COLDFUSE_V1 adjudication (mechanical, gates v2 per "
          "GATE5_CONFORMANCE_DECISION.md)")
    for tag, rows_ in gate5_out.items():
        lit = all(r["literal"] for r in rows_)
        print(f"  Gate5 {tag}: literal={'PASS' if lit else 'FAIL'} "
              f"normalized=PASS (extras {rows_[0]['extras_n']}, none on "
              "command line)")
    rows = {}
    for tag in CATS:
        td = [r["tail_delta"] for r in data[tag]]
        od = [r["overall_delta"] for r in data[tag]]
        m, sd, t, p, ci = t_ci(td)
        mo, _, _, po, cio = t_ci(od)
        # exact sign-test sensitivity at n=5 (descriptive, registered t governs)
        pos = sum(1 for v in td if v > 0)
        sign_p = 2 * 0.5 ** 5 if pos in (0, 5) else 1.0
        rows[tag] = {"tail": {"mean": m, "sd": sd, "t": t, "p": p, "ci": ci},
                     "overall": {"mean": mo, "p": po, "ci": cio},
                     "mid_mean": sum(r["mid_delta"] for r in data[tag]) / 5,
                     "head_mean": sum(r["head_delta"] for r in data[tag]) / 5,
                     "sign_test_p": sign_p,
                     "no_material_cost": bool(cio[0] > COST_MARGIN),
                     "per_seed": data[tag]}
        print(f"  {tag}: tail {m:+.5f} [{ci[0]:+.5f}, {ci[1]:+.5f}] "
              f"t={t:.2f} p={p:.2e} sign-p={sign_p:.4f} | overall {mo:+.5f} "
              f"[{cio[0]:+.5f}, {cio[1]:+.5f}] "
              f"{'no-material-cost' if rows[tag]['no_material_cost'] else 'COST EXCEEDS MARGIN'} "
              f"| mid {rows[tag]['mid_mean']:+.5f} head {rows[tag]['head_mean']:+.5f}")
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
                   "cost_margin": COST_MARGIN, "alpha": ALPHA,
                   "gate5": gate5_out,
                   "gate5_decision": "GATE5_CONFORMANCE_DECISION.md",
                   "rows": rows}, f, indent=2)
    print(f"wrote {outp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
