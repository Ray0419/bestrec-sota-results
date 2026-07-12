#!/usr/bin/env python
"""Mechanical adjudicator for PREREG_FIR_BREADTH.md (frozen decision rule).

Per category, over the 5 seed-paired differences
    d_s = best_test NDCG@10(filter, s) - best_test NDCG@10(nofilter, s):
  CONFIRMED iff the two-sided 95% Student-t CI of d excludes 0 AND >=4/5 seeds
            have d_s > 0.
  NULL      otherwise (published with identical prominence).
  VOID      on any mechanical protocol violation: an arm with <5 valid runs,
            non-full-catalog eval (best_test n_eval must equal the category
            user count, cross-checked against the split test.csv row count),
            seed substitution, config drift between arms beyond the filter
            flags, or data hash drift across the category's 10 runs.

Tail/by-popularity readouts are exploratory only and are not adjudicated.

Appends one idempotent dated block per invocation-content to
FIR_BREADTH_RESULTS.md at the repo root (created with a header if absent);
re-running with unchanged inputs appends nothing.

Exit codes: --report (default) always 0. --gate exits 1 if any category is
VOID or incomplete (NULL is a legitimate pre-registered outcome, not a gate
failure). --no-append skips the results-file write (validation use).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SPLIT_DIR = ROOT / "data_5core" / "5core" / "last_out"
RES_MD = ROOT / "FIR_BREADTH_RESULTS.md"

# Frozen in PREREG_FIR_BREADTH.md (categories as prepped -- no substitution;
# CDs_and_Vinyl passed the declared feasibility check).
CATEGORIES = ["Industrial_and_Scientific", "CDs_and_Vinyl"]
SEEDS = [20260713, 20260714, 20260715, 20260716, 20260717]
T975_DF4 = 2.776  # two-sided 95% Student-t critical value, df = 4
# Config keys that legitimately differ between the two arms / across seeds.
ARM_KEYS = {"causal_filter", "filter_kernel"}
PER_RUN_KEYS = {"seed", "out"}

HEADER = """# FIR-BREADTH campaign results (PREREG_FIR_BREADTH.md)

Mechanical adjudication blocks appended by `_bestrec_run/adjudicate_fir_breadth.py`.
Decision rule (frozen before any run): per category, paired 5-seed
d_s = filter - nofilter on best-by-val FULL-catalog NDCG@10; CONFIRMED iff the
two-sided 95% Student-t CI excludes 0 AND >=4/5 seeds are positive; NULL
otherwise; VOID on protocol violation. Nulls are published with the same
prominence as confirmations.
"""


def load_run(path: Path):
    """Return (record dict) or (None, reason)."""
    if not path.exists():
        return None, "missing"
    try:
        d = json.load(open(path, encoding="utf-8"))
    except Exception as e:
        return None, f"unparseable ({e.__class__.__name__})"
    bt = d.get("best_test")
    if not isinstance(bt, dict) or "NDCG@10" not in bt:
        return None, "no best_test"
    return d, None


def test_csv_rows(cat: str) -> int:
    p = SPLIT_DIR / f"{cat}.test.csv"
    if not p.exists():
        return -1
    with open(p, encoding="utf-8", newline="") as f:
        return sum(1 for _ in f) - 1


def adjudicate_category(cat: str):
    """Return (verdict, lines, payload) for one category."""
    lines = []
    problems = []
    runs = {}  # (arm, seed) -> json dict
    for arm in ("filter", "nofilter"):
        for s in SEEDS:
            p = HERE / f"results_FIRB_{cat}_{arm}_seed{s}.json"
            d, why = load_run(p)
            if d is None:
                problems.append(f"{arm} seed {s}: {why}")
            else:
                runs[(arm, s)] = d
    n_expected = 2 * len(SEEDS)
    if len(runs) < n_expected:
        lines.append(f"- runs present: {len(runs)}/{n_expected}; "
                     + "; ".join(problems))
        return "VOID(incomplete)", lines, {"present": len(runs)}

    # --- mechanical protocol checks -------------------------------------
    tcsv = test_csv_rows(cat)
    n_users_set = {d["n_users"] for d in runs.values()}
    if len(n_users_set) != 1:
        problems.append(f"n_users differs across runs: {sorted(n_users_set)}")
    n_users = runs[("filter", SEEDS[0])]["n_users"]
    if tcsv not in (-1, n_users):
        problems.append(f"n_users {n_users} != test.csv rows {tcsv}")
    for (arm, s), d in sorted(runs.items()):
        ne = d["best_test"].get("n_eval")
        if ne != n_users:
            problems.append(f"{arm} seed {s}: best_test n_eval {ne} != user count {n_users} "
                            "(non-full-catalog eval)")
        if d.get("category") != cat:
            problems.append(f"{arm} seed {s}: category field {d.get('category')!r}")
        if d.get("config", {}).get("seed") != s:
            problems.append(f"{arm} seed {s}: config seed {d.get('config', {}).get('seed')} "
                            "(seed substitution)")
    # config drift: within arm (modulo per-run keys) and between arms
    # (additionally modulo the filter flags) -- prereg: "argv diff beyond the
    # filter flags" voids. Compared on the parsed config for order-robustness.
    def cfg(d, drop):
        return {k: v for k, v in d.get("config", {}).items() if k not in drop}
    ref_f = cfg(runs[("filter", SEEDS[0])], PER_RUN_KEYS)
    ref_n = cfg(runs[("nofilter", SEEDS[0])], PER_RUN_KEYS)
    for s in SEEDS:
        if cfg(runs[("filter", s)], PER_RUN_KEYS) != ref_f:
            problems.append(f"filter seed {s}: config drift within arm")
        if cfg(runs[("nofilter", s)], PER_RUN_KEYS) != ref_n:
            problems.append(f"nofilter seed {s}: config drift within arm")
    if ({k: v for k, v in ref_f.items() if k not in ARM_KEYS}
            != {k: v for k, v in ref_n.items() if k not in ARM_KEYS}):
        diff = {k for k in set(ref_f) | set(ref_n)
                if k not in ARM_KEYS and ref_f.get(k) != ref_n.get(k)}
        problems.append(f"config drift BETWEEN arms beyond filter flags: {sorted(diff)}")
    if not (ref_f.get("causal_filter") is True and ref_f.get("filter_kernel") == 8):
        problems.append(f"filter arm flags wrong: causal_filter={ref_f.get('causal_filter')} "
                        f"kernel={ref_f.get('filter_kernel')}")
    if ref_n.get("causal_filter") is not False:
        problems.append(f"nofilter arm has causal_filter={ref_n.get('causal_filter')}")
    # data identity across the category's 10 runs
    ds = {json.dumps(d["provenance"].get("data_sha256"), sort_keys=True)
          for d in runs.values()}
    if len(ds) != 1:
        problems.append("data_sha256 differs across the category's runs")

    # --- per-seed values --------------------------------------------------
    per_seed = []
    for s in SEEDS:
        f = runs[("filter", s)]["best_test"]["NDCG@10"]
        n = runs[("nofilter", s)]["best_test"]["NDCG@10"]
        per_seed.append((s, f, n, f - n))
    d_vals = [d for (_, _, _, d) in per_seed]
    mean = sum(d_vals) / 5
    sd = math.sqrt(sum((x - mean) ** 2 for x in d_vals) / 4)
    half = T975_DF4 * sd / math.sqrt(5)
    lo, hi = mean - half, mean + half
    npos = sum(1 for x in d_vals if x > 0)

    lines.append(f"- n_users (full-catalog n_eval, all 10 runs) = {n_users:,}"
                 + (f"; test.csv rows = {tcsv:,}" if tcsv != -1 else ""))
    for s, f, n, dd in per_seed:
        lines.append(f"- seed {s}: filter {f:.5f}  nofilter {n:.5f}  d = {dd:+.5f}")
    lines.append(f"- paired d: mean {mean:+.5f}  sd {sd:.5f}  "
                 f"95% t-CI [{lo:+.5f}, {hi:+.5f}]  positive seeds {npos}/5")

    if problems:
        for p in problems:
            lines.append(f"- PROTOCOL VIOLATION: {p}")
        return "VOID", lines, {"per_seed": per_seed, "problems": problems}

    ci_excludes_0 = (lo > 0) or (hi < 0)
    verdict = "CONFIRMED" if (ci_excludes_0 and npos >= 4) else "NULL"
    lines.append(f"- rule: CI excludes 0 -> {ci_excludes_0}; >=4/5 positive -> {npos >= 4}")
    payload = {"per_seed": per_seed, "mean": mean, "sd": sd, "ci": [lo, hi],
               "npos": npos}
    return verdict, lines, payload


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gate", action="store_true",
                    help="exit 1 on any VOID/incomplete category (default --report: always exit 0)")
    ap.add_argument("--report", action="store_true", help="report mode (default)")
    ap.add_argument("--no-append", action="store_true",
                    help="print only; do not touch FIR_BREADTH_RESULTS.md")
    args = ap.parse_args()

    out_lines = []
    verdicts = {}
    for cat in CATEGORIES:
        v, lines, _ = adjudicate_category(cat)
        verdicts[cat] = v
        out_lines.append(f"\n### {cat} -- **{v}**\n")
        out_lines.extend(l + "\n" for l in lines)
        if v == "CONFIRMED":
            out_lines.append(f"- frozen claim wording applies: \"the causal FIR filter's paired "
                             f"5-seed improvement on {cat} (transplanted with zero per-category "
                             f"tuning) is positive with a 95% CI excluding zero.\" Nothing broader; "
                             f"no SOTA language; no comparator statement.\n")

    body = "".join(out_lines)
    block_id = hashlib.sha256(body.encode()).hexdigest()[:12]
    date = time.strftime("%Y-%m-%d %H:%M:%S")
    block = (f"\n---\n\n## Adjudication {date} (block-id {block_id})\n"
             f"Seeds {SEEDS}; rule frozen in PREREG_FIR_BREADTH.md.\n"
             + body
             + "\n**Campaign verdicts:** "
             + "; ".join(f"{c}: {v}" for c, v in verdicts.items()) + "\n")
    print(block)

    if not args.no_append:
        if not RES_MD.exists():
            RES_MD.write_text(HEADER, encoding="utf-8")
        existing = RES_MD.read_text(encoding="utf-8")
        if f"block-id {block_id}" in existing:
            print(f"(identical adjudication block {block_id} already recorded; append skipped)")
        else:
            with RES_MD.open("a", encoding="utf-8") as f:
                f.write(block)
            print(f"appended block {block_id} to {RES_MD}")

    if args.gate:
        bad = [c for c, v in verdicts.items() if v.startswith("VOID")]
        return 1 if bad else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
