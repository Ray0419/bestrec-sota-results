# -*- coding: utf-8 -*-
"""Mechanical adjudicator for PREREG_FIR_CANONICAL_BREADTH.

Frozen and committed BEFORE launch. Reads the 32 declared result files
(2 categories x 2 arms x 8 seeds), enforces integrity gates, and computes the
frozen per-category analysis:

  primary  : paired-by-seed difference d = a1learned - a0ident on test NDCG@10.
             Pairing is LEGITIMATE here because the committed integrity gate
             verifies that, for each (category, seed), both arms share ONE
             backbone init_state_sha256 -- so the seeds are genuinely
             initialization-matched (unlike the legacy same-seed breadth).
  robustness: independent-arm Welch, and an exact two-sided sign test.
  multiplicity: Holm across the two per-category primary paired tests.

Per-category PASS rule (frozen): paired 95% CI excludes 0 AND direction positive
AND Holm-adjusted paired p < 0.05. Family verdict:
  CANON-BREADTH-POS  both categories PASS
  CANON-BREADTH-PARTIAL exactly one PASSes
  CANON-BREADTH-NULL neither PASSes (reported with equal prominence)
Exit 0 = adjudication completed (any direction); 2 = integrity gate failed;
3 = result files missing. The output is scanned for forbidden tokens (no SOTA,
no superiority, no comparator claim) and fails closed on any hit.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CATEGORIES = ("Industrial_and_Scientific", "CDs_and_Vinyl")
ARMS = ("a0ident", "a1learned")
SEEDS = (20260810, 20260811, 20260812, 20260813,
         20260814, 20260815, 20260816, 20260817)
KERNEL = 16
EPOCHS = 20
ALPHA = 0.05
ARM_EXPECT = {
    "a0ident": {"fir_v3": "frozen", "fir_v3_wd": "backbone"},
    "a1learned": {"fir_v3": "learned", "fir_v3_wd": "backbone"},
}
FORBIDDEN = ("sota", "state-of-the-art", "superior", "outperform",
             "beats", "significantly better", "best-in-class", "wins")


def _tdist(t, df):
    try:
        from scipy import stats
        return 2.0 * stats.t.sf(abs(t), df), stats.t.ppf(0.975, df)
    except Exception:
        return 2.0 * 0.5 * math.erfc(abs(t) / math.sqrt(2)), 1.96


def paired(d):
    n = len(d)
    md = sum(d) / n
    sd = math.sqrt(sum((v - md) ** 2 for v in d) / (n - 1)) if n > 1 else 0.0
    se = sd / math.sqrt(n) if sd > 0 else 0.0
    if se == 0:
        return md, float("inf"), (md, md), 0.0 if md != 0 else 1.0
    t = md / se
    p, tc = _tdist(t, n - 1)
    return md, t, (md - tc * se, md + tc * se), p


def welch(x, y):
    nx, ny = len(x), len(y)
    mx, my = sum(x) / nx, sum(y) / ny
    vx = sum((v - mx) ** 2 for v in x) / (nx - 1)
    vy = sum((v - my) ** 2 for v in y) / (ny - 1)
    se = math.sqrt(vx / nx + vy / ny)
    if se == 0:
        return mx - my, 0.0, 1.0
    t = (mx - my) / se
    df = (vx / nx + vy / ny) ** 2 / (
        (vx / nx) ** 2 / (nx - 1) + (vy / ny) ** 2 / (ny - 1))
    p, _ = _tdist(t, df)
    return mx - my, t, p


def sign_test(d):
    pos = sum(1 for v in d if v > 0)
    n = len(d)
    # exact two-sided sign test p (binomial, prob 0.5)
    def comb(a, b):
        return math.comb(a, b)
    k = min(pos, n - pos)
    tail = sum(comb(n, i) for i in range(0, k + 1)) / (2 ** n)
    return pos, min(1.0, 2.0 * tail)


def main():
    vals = {c: {a: {} for a in ARMS} for c in CATEGORIES}
    init_hash = {c: {} for c in CATEGORIES}
    missing = []
    for cat in CATEGORIES:
        for arm in ARMS:
            for seed in SEEDS:
                f = os.path.join(
                    HERE, f"results_{cat}_FIRCANON_{arm}_seed{seed}.json")
                if not os.path.exists(f):
                    missing.append(os.path.basename(f))
                    continue
                d = json.load(open(f, encoding="utf-8"))
                cfg = d["config"]
                for k, v in ARM_EXPECT[arm].items():
                    if cfg.get(k) != v:
                        print(f"INTEGRITY FAIL: {os.path.basename(f)} "
                              f"config {k}={cfg.get(k)!r} != {v!r}")
                        return 2
                if (cfg.get("fir_v3_kernel") != KERNEL
                        or cfg.get("category") != cat
                        or cfg.get("epochs") != EPOCHS
                        or cfg.get("seed") != seed
                        or cfg.get("causal_filter")):
                    print(f"INTEGRITY FAIL: {os.path.basename(f)} frozen-config "
                          "mismatch (kernel/category/epochs/seed/causal_filter)")
                    return 2
                if arm == "a0ident" and d.get("fir_v3_final_l2") not in (0, 0.0):
                    print(f"INTEGRITY FAIL: {os.path.basename(f)} control taps "
                          f"moved: l2={d.get('fir_v3_final_l2')}")
                    return 2
                init_hash[cat].setdefault(seed, {})[arm] = \
                    d.get("init_state_sha256")
                vals[cat][arm][seed] = float(d["best_test"]["NDCG@10"])
    if missing:
        print(f"NOT READY: {len(missing)} of {len(CATEGORIES)*len(ARMS)*len(SEEDS)}"
              " result files missing:")
        for m in missing[:8]:
            print("  -", m)
        if len(missing) > 8:
            print(f"  ... and {len(missing)-8} more")
        return 3
    for cat in CATEGORIES:
        for seed, h in init_hash[cat].items():
            if len(set(h.values())) != 1 or None in h.values():
                print(f"INTEGRITY FAIL: {cat} seed {seed} arms do NOT share one "
                      f"init_state_sha256: {h}")
                return 2

    out_lines = []

    def emit(s):
        out_lines.append(s)
        print(s)

    emit("PREREG_FIR_CANONICAL_BREADTH adjudication (mechanical)")
    per_cat = {}
    primary_p = {}
    for cat in CATEGORIES:
        a0 = [vals[cat]["a0ident"][s] for s in SEEDS]
        a1 = [vals[cat]["a1learned"][s] for s in SEEDS]
        d = [a1[i] - a0[i] for i in range(len(SEEDS))]
        md, t, ci, p = paired(d)
        west, wt, wp = welch(a1, a0)
        pos, sp = sign_test(d)
        m0, m1 = sum(a0) / len(a0), sum(a1) / len(a1)
        emit(f"[{cat}]")
        emit(f"  a0ident   mean NDCG@10 = {m0:.6f}")
        emit(f"  a1learned mean NDCG@10 = {m1:.6f}")
        emit(f"  paired d=a1-a0: mean {md:+.6f}  95% CI [{ci[0]:+.6f}, "
             f"{ci[1]:+.6f}]  t={t:.3f} df={len(SEEDS)-1} p={p:.4f}")
        emit(f"  robustness: Welch est {west:+.6f} t={wt:.3f} p={wp:.4f} | "
             f"sign test {pos}/{len(SEEDS)} positive, exact two-sided p={sp:.4f}")
        per_cat[cat] = {"a0_mean": m0, "a1_mean": m1, "paired_mean": md,
                        "paired_ci": list(ci), "paired_t": t, "paired_p": p,
                        "welch_est": west, "welch_t": wt, "welch_p": wp,
                        "sign_pos": pos, "sign_p": sp,
                        "per_seed_diff": [round(v, 6) for v in d]}
        primary_p[cat] = p

    # Holm across the two per-category primary paired tests
    order = sorted(CATEGORIES, key=lambda c: primary_p[c])
    alive = True
    holm = {}
    for rank, c in enumerate(order):
        thr = ALPHA / (len(CATEGORIES) - rank)
        sig = bool(alive and primary_p[c] <= thr)
        if not sig:
            alive = False
        holm[c] = {"threshold": thr, "significant": sig}

    passed = {}
    for c in CATEGORIES:
        pc = per_cat[c]
        pass_c = bool(pc["paired_ci"][0] > 0 and pc["paired_mean"] > 0
                      and holm[c]["significant"])
        passed[c] = pass_c
        emit(f"  {c}: Holm thr={holm[c]['threshold']:.4f} "
             f"Holm-{'SIG' if holm[c]['significant'] else 'ns'} -> "
             f"{'PASS' if pass_c else 'not-passed'}")

    npass = sum(passed.values())
    if npass == len(CATEGORIES):
        verdict = "CANON-BREADTH-POS"
    elif npass >= 1:
        verdict = "CANON-BREADTH-PARTIAL"
    else:
        verdict = "CANON-BREADTH-NULL"
    emit(f"VERDICT: {verdict} ({npass}/{len(CATEGORIES)} categories PASS; "
         "internal matched-init filter-vs-identity contrast; not a comparator "
         "claim; wording frozen in PREREG_FIR_CANONICAL_BREADTH.md)")

    blob = "\n".join(out_lines).lower()
    hits = [t for t in FORBIDDEN if t in blob]
    if hits:
        print("ADJUDICATOR SELF-CHECK FAILED: forbidden token(s)", hits)
        return 2

    outp = os.path.join(HERE, "fir_canonical_breadth_adjudication.json")
    with open(outp, "w", encoding="utf-8") as f:
        json.dump({"verdict": verdict, "alpha": ALPHA, "kernel": KERNEL,
                   "epochs": EPOCHS, "seeds": list(SEEDS),
                   "per_category": per_cat, "holm": holm, "passed": passed,
                   "n_pass": npass, "init_hash_by_cat_seed": init_hash}, f,
                  indent=2)
    print(f"wrote {outp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
