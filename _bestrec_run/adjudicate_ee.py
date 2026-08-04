# -*- coding: utf-8 -*-
"""E-E mechanical adjudicator (committed BEFORE any real run; see PREREG_EE.md).

REPORTING + INTEGRITY gate only. NOT a hypothesis test: it emits no PASS/FAIL and
no superiority verdict. It loads the per-seed AlphaFuse results, computes the
mean+-sd of the full metric family, reads our stack's comparator number from the
pinned provenance, emits a descriptive (non-inferential) point-estimate
comparison, records the five disclosed deviations, and scans its OWN output for
forbidden superiority/SOTA tokens (failing if any appear). Verdict vocabulary is
limited to REPORTABLE (>=3 seeds, integrity OK) or INCOMPLETE.

  python _bestrec_run/adjudicate_ee.py --category Video_Games
"""
import argparse
import glob
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MIN_SEEDS = 3
FAMILY = [f"{m}@{k}" for m in ("HR", "NDCG", "MRR") for k in (5, 10, 20, 50)]
FORBIDDEN = ("superior", "beat", "sota", "state-of-the-art", "outperform",
             "significantly better", "wins", "dominant")

# Comparator provenance (PREREG_EE.md): our stack's recorded NDCG@10 on the SAME
# split + SAME MiniLM text. VG = mean of the 4 recorded BEST_VG seeds.
OUR_PROVENANCE = {
    "Video_Games": sorted(glob.glob(os.path.join(
        HERE, "results_BEST_VG_seed2026061*.json"))),
    "Office_Products": sorted(glob.glob(os.path.join(
        HERE, "results_BEST_Office_Products*.json"))),
}


def mean_sd(xs):
    n = len(xs)
    m = sum(xs) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1)) if n > 1 else 0.0
    return m, sd


def our_ndcg10(cat):
    files = OUR_PROVENANCE.get(cat, [])
    vals, used = [], []
    for f in files:
        try:
            d = json.load(open(f))
            b = d.get("best_test") or d.get("test") or {}
            if "NDCG@10" in b:
                vals.append(float(b["NDCG@10"]))
                used.append(os.path.basename(f))
        except Exception:
            continue
    if not vals:
        return None, [], None
    m, _ = mean_sd(vals)
    return m, used, vals


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--category", required=True)
    args = ap.parse_args()
    cat = args.category

    seed_files = sorted(glob.glob(os.path.join(
        HERE, f"results_EE_{cat}_alphafuse_seed*.json")))
    per_seed = []
    for f in seed_files:
        try:
            per_seed.append(json.load(open(f)))
        except Exception as e:
            print(f"  WARN unreadable {f}: {e}")

    out = {"experiment": "E-E", "category": cat, "arm_A": "AlphaFuse",
           "arm_B": "our SASRec-SBERT stack", "n_seeds": len(per_seed),
           "min_seeds_required": MIN_SEEDS}

    if len(per_seed) < MIN_SEEDS:
        out["verdict"] = "INCOMPLETE"
        out["reason"] = f"{len(per_seed)}/{MIN_SEEDS} AlphaFuse seeds present"
        _emit(out)
        return 0

    # aggregate the full family (assert finite)
    agg = {}
    for key in FAMILY:
        xs = [float(r["metrics_test"][key]) for r in per_seed
              if key in r.get("metrics_test", {})]
        if not xs or not all(math.isfinite(x) for x in xs):
            out["verdict"] = "INCOMPLETE"
            out["reason"] = f"metric {key} missing/non-finite in a seed"
            _emit(out)
            return 0
        m, sd = mean_sd(xs)
        agg[key] = {"mean": round(m, 6), "sd": round(sd, 6), "n": len(xs)}
    out["alphafuse_family_mean_sd"] = agg

    b_ndcg10, b_src, b_vals = our_ndcg10(cat)
    a_ndcg10 = agg["NDCG@10"]["mean"]
    out["comparator_our_stack"] = {
        "NDCG@10": (round(b_ndcg10, 6) if b_ndcg10 is not None else None),
        "provenance_files": b_src,
        "provenance_values": b_vals,
        "note": "same split, same MiniLM-384 text; recorded, not re-run",
    }
    # DESCRIPTIVE, non-inferential point-estimate difference (sign only).
    if b_ndcg10 is not None:
        diff = a_ndcg10 - b_ndcg10
        out["point_estimate_NDCG10"] = {
            "alphafuse_mean": round(a_ndcg10, 6),
            "our_stack": round(b_ndcg10, 6),
            "difference_A_minus_B": round(diff, 6),
            "label": "DESCRIPTIVE point estimate; NON-INFERENTIAL; no "
                     "significance test; no ranking claim asserted in either "
                     "direction; single environment.",
        }
    else:
        out["point_estimate_NDCG10"] = {
            "alphafuse_mean": round(a_ndcg10, 6),
            "our_stack": None,
            "note": "comparator provenance not found for this category; "
                    "AlphaFuse arm reported alone.",
        }

    out["disclosed_deviations"] = per_seed[0].get("deviations", [])
    # audit 2026-07-24 16:00 countability gates (ERRATUM E2). A cross-evaluator
    # comparison is NOT the same estimand: AlphaFuse's eval ranks the catalogue
    # WITHOUT masking the user's consumed items; our paper evaluator masks the
    # full train+val history (run_sasrec_sbert.py:1626-1630) before ranking.
    # Masking removes distractors and inflates our arm, so a shared exact-rank
    # evaluator is REQUIRED before any countable comparison. Absent it, the run
    # is a protocol-deviated engineering PILOT.
    seeds_present = sorted(int(r.get("seed", -1)) for r in per_seed)
    parity = all(r.get("provenance", {}).get("shared_evaluator") is True
                 for r in per_seed)
    gates = []
    if seeds_present != [22, 23, 24]:
        gates.append(f"seeds {seeds_present} != registered [22,23,24]")
    if not parity:
        gates.append("no shared-evaluator estimand parity (AlphaFuse eval does "
                     "not mask seen items; ours does) -- cross-evaluator")
    if b_ndcg10 is None:
        gates.append("Arm B comparator provenance missing")
    if gates:
        out["verdict"] = "PILOT_NONCOUNTABLE"
        out["quarantine_reasons"] = gates
        out["reporting_class"] = ("protocol-deviated engineering PILOT; NOT "
                                   "countable; values must NOT be integrated; "
                                   "superseded by E-E V2 (one shared exact-rank "
                                   "evaluator, matched factorial, equal tuning, "
                                   "exact provenance, per-user ranks).")
        _emit(out)
        return 0
    out["verdict"] = "REPORTABLE"
    out["reporting_class"] = ("environment-caveated point-estimate comparison; "
                              "descriptive only; NOT confirmatory; no best-system "
                              "or ranking claim is asserted; NOT part of the "
                              "counted set (MI V2, Office V3).")
    _emit(out)
    return 0


def _emit(out):
    txt = json.dumps(out, indent=1)
    low = txt.lower()
    hits = [t for t in FORBIDDEN if t in low]
    if hits:
        # a forbidden token in our OWN output is a coding error -> hard fail.
        print("ADJUDICATOR SELF-CHECK FAILED: forbidden token(s)", hits)
        sys.exit(2)
    path = os.path.join(HERE, "ee_adjudication.json")
    # append-only ledger keyed by category (never clobber other categories)
    ledger = {}
    if os.path.exists(path):
        try:
            ledger = json.load(open(path))
        except Exception:
            ledger = {}
    ledger[out["category"]] = out
    with open(path, "w", encoding="utf-8") as f:
        json.dump(ledger, f, indent=1)
    print(txt)
    print(f"\n[{out['category']}] verdict = {out['verdict']}  -> {path}")


if __name__ == "__main__":
    sys.exit(main())
