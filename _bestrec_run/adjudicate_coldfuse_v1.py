# -*- coding: utf-8 -*-
"""POST-OUTCOME SENSITIVITY adjudicator (v3) for the E-G COLDFUSE campaign.

CLASSIFICATION (audit 2026-07-23 15:59, accepted): the campaign is
OUTCOME-VISIBLE and PROTOCOL-DEVIATED — interim results were observed and
committed mid-campaign contrary to PREREG_COLDFUSE_V1's no-interim clause;
the literal frozen Gate 5 FAILS MI and VG; and the governing gate/adjudicator
were amended after 24/25 outcomes were visible. Therefore NOTHING this script
prints is a preregistered confirmation. The original as-launched adjudicator
and its output are preserved verbatim:
  adjudicate_coldfuse_v1_ORIGINAL_aslaunched.py (6,514 bytes, sha256
  7931e683f53596042a726b93...), coldfuse_v1_adjudication_v1run_20260723.json,
  coldfuse_v1_adjudication_ORIGINAL_v1_output.txt; the v2 (post-outcome,
  12,839 bytes, sha256 2b57348ff3ad39960f022a36...) output is preserved as
  coldfuse_v1_adjudication_v2run_20260723.json.

v3 fixes the v2 implementation defects the audit confirmed:
 - extras check was vacuous (driver_flags iterated ref keys only, so
   extras_on_cmdline was empty by construction): now every extra key's VALUE
   must equal the same key's value in a SAME-ERA frozen reference config
   (the IS reference, whose key set matches the new runs literally), and be
   identical across all runs;
 - sweep completeness now compares the exact frozen 40-candidate identity
   set, not a count, and requires every sweep value finite;
 - NPZ checks now include unique/sorted users, target-bin length/range, and
   aggregate reconstruction of overall/tail from per-user rows;
 - Gate 1 now rejects undeclared extra base/confirm files ("exactly");
 - exact two-sided sign test is a correct binomial (4/5 -> .375), not 1.0;
 - zero-SD t is a refusal (exit 2), not an infinite statistic;
 - --gate5-report prints completeness status alongside the config diffs.

Exit 0 = sensitivity adjudication completed; 2 = integrity failure;
3 = not ready.
"""
import glob
import itertools
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
SAME_ERA_REF = "results_FIRB_Industrial_and_Scientific_filter_seed20260713.json"
EXEMPT = {"seed", "out", "save_ckpt", "fir_v3", "fir_v3_kernel", "fir_v3_wd"}
WSET = (0.0, 0.05, 0.1, 0.2)
TAIL_MARGIN = 0.0005
COST_MARGIN = -0.0005
NONINF = 0.0002
ALPHA = 0.05
CLASSIFICATION = ("post-outcome sensitivity adjudication (v3); campaign "
                  "outcome-visible and protocol-deviated (no-interim clause "
                  "violated; literal Gate 5 FAILS MI/VG; gate amended after "
                  "outcomes); original literal verdicts govern; W-C codes "
                  "below carry NO confirmatory status")


def frozen_candidate_keys():
    keys = set()
    for prof in ("uniform", "exp0.9"):
        for t, m2, h in itertools.product(WSET, WSET, WSET):
            if t >= m2 >= h:
                keys.add(json.dumps({"profile": prof, "wt_tail": t,
                                     "wt_mid": m2, "wt_head": h},
                                    sort_keys=True))
    return keys


def gate5(ref_cfg, cfg, era_cfg, era_vals_seen):
    shared_bad = [k for k in set(ref_cfg) - EXEMPT
                  if k in cfg and cfg[k] != ref_cfg[k]]
    missing = [k for k in set(ref_cfg) - EXEMPT if k not in cfg]
    extras = sorted(set(cfg) - set(ref_cfg) - EXEMPT)
    literal = not shared_bad and not missing and not extras
    bad_extras = []
    for k in extras:
        if k not in era_cfg:
            bad_extras.append(f"{k}: absent from same-era reference")
        elif cfg[k] != era_cfg[k]:
            bad_extras.append(f"{k}: {cfg[k]!r} != era default {era_cfg[k]!r}")
        if k in era_vals_seen and era_vals_seen[k] != cfg[k]:
            bad_extras.append(f"{k}: inconsistent across runs")
        era_vals_seen[k] = cfg[k]
    normalized = not shared_bad and not missing and not bad_extras
    return literal, normalized, shared_bad + missing, extras, bad_extras


def sign_p(deltas):
    n = len(deltas)
    k = sum(1 for v in deltas if v > 0)
    if any(v == 0 for v in deltas):
        n = sum(1 for v in deltas if v != 0)
    def binom_cdf_le(x):
        return sum(math.comb(n, i) for i in range(0, x + 1)) / 2.0 ** n
    lo = binom_cdf_le(k)
    hi = 1.0 - binom_cdf_le(k - 1) if k >= 1 else 1.0
    return min(1.0, 2.0 * min(lo, hi))


def t_ci(vals, label):
    n = len(vals)
    m = sum(vals) / n
    sd = math.sqrt(sum((v - m) ** 2 for v in vals) / (n - 1))
    if sd == 0:
        print(f"INTEGRITY FAIL: zero between-seed SD for {label}; the "
              "registered t statistic is undefined")
        sys.exit(2)
    se = sd / math.sqrt(n)
    t = m / se
    try:
        from scipy import stats
        p = float(2.0 * stats.t.sf(abs(t), n - 1))
        tc = float(stats.t.ppf(0.975, n - 1))
    except Exception:
        print("FATAL: SciPy unavailable; no approximation substituted.")
        sys.exit(2)
    return m, sd, float(t), p, (float(m - tc * se), float(m + tc * se))


def recompute_argmax(conf):
    sweep = conf["val_sweep"]
    ref = sweep["REF"]
    best_key, best_tail = None, None
    for name, r in sweep.items():
        if name == "REF":
            continue
        if r["overall"] >= ref["overall"] - NONINF and \
                (best_tail is None or r["tail"] > best_tail):
            best_key, best_tail = name, r["tail"]
    return best_key


def main():
    report_only = "--gate5-report" in sys.argv
    era_cfg = json.load(open(os.path.join(HERE, SAME_ERA_REF),
                             encoding="utf-8"))["config"]
    cand_keys = frozen_candidate_keys()
    missing = []
    data = {c: [] for c in CATS}
    gate5_out = {}
    era_vals_seen = {}
    # Gate 1 "exactly": no undeclared campaign files
    decl_bases = {f"results_{t}_COLDFUSE_base_seed{s}.json"
                  for t in CATS for s in SEEDS}
    decl_confirms = {f"results_{CATS[t][0]}_COLDFUSE_confirm_seed{s}.json"
                     for t in CATS for s in SEEDS}
    got_bases = {os.path.basename(p) for p in
                 glob.glob(os.path.join(HERE, "results_*_COLDFUSE_base_seed*.json"))
                 if not p.endswith(".fusion.json")}
    got_confirms = {os.path.basename(p) for p in
                    glob.glob(os.path.join(HERE,
                              "results_*_COLDFUSE_confirm_seed*.json"))}
    undeclared = sorted((got_bases - decl_bases) | (got_confirms - decl_confirms))
    if undeclared and not report_only:
        print(f"INTEGRITY FAIL (Gate 1 'exactly'): undeclared campaign files: "
              f"{undeclared}")
        return 2

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
            lit, norm, bad_shared, extras, bad_extras = gate5(
                ref_cfg, cfg, era_cfg, era_vals_seen)
            gate5_out.setdefault(tag, []).append(
                {"seed": seed, "literal": lit, "normalized": norm,
                 "shared_mismatch_or_missing": bad_shared,
                 "extras_n": len(extras), "extra_value_defects": bad_extras})
            if report_only:
                continue
            if not norm:
                print(f"INTEGRITY FAIL (Gate 5 normalized/value-checked): "
                      f"{os.path.basename(b)}: {bad_shared or bad_extras}")
                return 2
            conf = json.load(open(cj, encoding="utf-8"))
            sel = conf["selected"]
            sel_key = json.dumps(sel, sort_keys=True)
            if sel_key not in cand_keys:
                print(f"INTEGRITY FAIL: off-grid selection in "
                      f"{os.path.basename(cj)}")
                return 2
            if conf.get("noninferiority") != NONINF:
                print(f"INTEGRITY FAIL: wrong constraint in "
                      f"{os.path.basename(cj)}")
                return 2
            sweep_keys = set(conf["val_sweep"]) - {"REF"}
            if sweep_keys != cand_keys:
                print(f"INTEGRITY FAIL: sweep identity mismatch in "
                      f"{os.path.basename(cj)} (missing "
                      f"{len(cand_keys - sweep_keys)}, extra "
                      f"{len(sweep_keys - cand_keys)})")
                return 2
            for name, r in conf["val_sweep"].items():
                for mk in ("overall", "tail", "mid", "head"):
                    if not math.isfinite(float(r[mk])):
                        print(f"INTEGRITY FAIL: non-finite sweep value in "
                              f"{os.path.basename(cj)}")
                        return 2
            if recompute_argmax(conf) != sel_key:
                print(f"INTEGRITY FAIL: argmax recomputation mismatch in "
                      f"{os.path.basename(cj)}")
                return 2
            if conf["test"]["reference"]["n"] != base["best_test"]["n_eval"]:
                print(f"INTEGRITY FAIL: n_eval mismatch in "
                      f"{os.path.basename(cj)}")
                return 2
            if use_ease:
                fus = json.load(open(fj, encoding="utf-8"))
                expected = float(fus["test"]["fused"]["ndcg"])
                kind = "fused2"
            else:
                expected = float(base["best_test"]["NDCG@10"])
                kind = "seq"
            if conf["reference"] != kind or \
                    abs(conf["expected_ref_overall"] - expected) > 1e-12:
                print(f"INTEGRITY FAIL: reference provenance in "
                      f"{os.path.basename(cj)}")
                return 2
            if abs(conf["test"]["reference"]["overall"] - expected) >= 0.0005:
                print(f"INTEGRITY FAIL: reconstruction drift in "
                      f"{os.path.basename(cj)}")
                return 2
            npz = np.load(cj[:-5] + ".perusers.npz")
            n = conf["test"]["reference"]["n"]
            users = npz["users"]
            tb = npz["target_bin"]
            ok = (len(users) == n and len(npz["ref_ndcg"]) == n
                  and len(npz["sel_ndcg"]) == n and len(tb) == n
                  and np.isfinite(npz["ref_ndcg"]).all()
                  and np.isfinite(npz["sel_ndcg"]).all()
                  and len(np.unique(users)) == n
                  and bool((np.diff(users) > 0).all())
                  and tb.min() >= 0 and tb.max() <= 2)
            if not ok:
                print(f"INTEGRITY FAIL: NPZ structure in "
                      f"{os.path.basename(cj)}")
                return 2
            for arr, sysname in (("ref_ndcg", "reference"),
                                 ("sel_ndcg", "selected")):
                if abs(float(npz[arr].mean())
                       - conf["test"][sysname]["overall"]) > 1e-6:
                    print(f"INTEGRITY FAIL: NPZ overall reconstruction "
                          f"({sysname}) in {os.path.basename(cj)}")
                    return 2
                mt = tb == 0
                if abs(float(npz[arr][mt].mean())
                       - conf["test"][sysname]["tail"]) > 1e-6:
                    print(f"INTEGRITY FAIL: NPZ tail reconstruction "
                          f"({sysname}) in {os.path.basename(cj)}")
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
                - conf["test"]["reference"]["head"]})
    if report_only:
        done = sum(len(v) for v in gate5_out.values())
        print(json.dumps({"completeness": f"{done}/25 rows present",
                          "undeclared_files": undeclared,
                          "gate5": gate5_out}, indent=1))
        return 0
    if missing:
        print(f"NOT READY: {len(missing)} required files missing:")
        for m2 in sorted(set(missing)):
            print("  -", m2)
        return 3

    print("E-G COLDFUSE sensitivity adjudication (v3)")
    print("CLASSIFICATION:", CLASSIFICATION)
    for tag, rows_ in gate5_out.items():
        lit = all(r["literal"] for r in rows_)
        print(f"  Gate5 {tag}: literal={'PASS' if lit else 'FAIL'} "
              f"value-checked-normalized=PASS ({rows_[0]['extras_n']} extras, "
              "all equal to same-era reference defaults)")
    rows = {}
    for tag in CATS:
        td = [r["tail_delta"] for r in data[tag]]
        od = [r["overall_delta"] for r in data[tag]]
        m, sd, t, p, ci = t_ci(td, f"{tag} tail")
        mo, sdo, to_, po, cio = t_ci(od, f"{tag} overall")
        rows[tag] = {"tail": {"mean": m, "sd": sd, "t": t, "p": p, "ci": ci},
                     "overall": {"mean": mo, "p": po, "ci": cio},
                     "mid_mean": sum(r["mid_delta"] for r in data[tag]) / 5,
                     "head_mean": sum(r["head_delta"] for r in data[tag]) / 5,
                     "sign_test_p": sign_p(td),
                     "no_material_cost": bool(cio[0] > COST_MARGIN),
                     "per_seed": data[tag]}
        print(f"  {tag}: tail {m:+.5f} [{ci[0]:+.5f}, {ci[1]:+.5f}] "
              f"t={t:.2f} p={p:.2e} exact-sign-p={rows[tag]['sign_test_p']:.4f}"
              f" | overall {mo:+.5f} [{cio[0]:+.5f}, {cio[1]:+.5f}] "
              f"{'within cost margin' if rows[tag]['no_material_cost'] else 'COST EXCEEDS MARGIN'}"
              f" | mid {rows[tag]['mid_mean']:+.5f} "
              f"head {rows[tag]['head_mean']:+.5f}")
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
            verdicts[c] = "W-C-POS (sensitivity only)"
        elif r["holm_significant"] and r["tail"]["mean"] < 0:
            verdicts[c] = "W-C-NEG (sensitivity only)"
        elif -TAIL_MARGIN < lo and hi < TAIL_MARGIN:
            verdicts[c] = "W-C-EQUIV (sensitivity only)"
        else:
            verdicts[c] = "W-C-INC (sensitivity only)"
        print(f"SENSITIVITY VERDICT {c}: {verdicts[c]}")

    outp = os.path.join(HERE, "coldfuse_v1_adjudication.json")
    with open(outp, "w", encoding="utf-8") as f:
        json.dump({"classification": CLASSIFICATION,
                   "adjudicator_versions": {
                       "v1_original_aslaunched": "7931e683f53596042a726b93",
                       "v2_post_outcome": "2b57348ff3ad39960f022a36",
                       "v1_output": "coldfuse_v1_adjudication_v1run_20260723.json",
                       "v2_output": "coldfuse_v1_adjudication_v2run_20260723.json"},
                   "verdicts": verdicts, "tail_margin": TAIL_MARGIN,
                   "cost_margin": COST_MARGIN, "alpha": ALPHA,
                   "gate5": gate5_out,
                   "gate5_decision": "GATE5_CONFORMANCE_DECISION.md",
                   "rows": rows}, f, indent=2)
    print(f"wrote {outp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
