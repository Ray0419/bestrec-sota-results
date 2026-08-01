#!/usr/bin/env python
"""CRI Pilot V1 adjudicator — mechanically evaluates gates G1-G4 from
PREREG_CRI_PILOT_V1.md against the run artifacts in results/.

Run after all 6 configs complete:  .venv/bin/python adjudicate.py
Prints a verdict block to append to the prereg under ## ADJUDICATION.
"""

import itertools
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
NOISES = ("uniform", "popularity")
SEEDS = (13, 42, 2026)
AUX = ("view", "cart")
ALL_B = ("view", "cart", "buy")
G1_BUDGET_S = 4 * 3600
G2_MIN_RHO = 0.5
G3_MARGIN = 0.03


def spearman(a, b):
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    ra -= ra.mean()
    rb -= rb.mean()
    return float((ra * rb).sum() / np.sqrt((ra**2).sum() * (rb**2).sum()))


def main():
    runs = {}
    for n, s in itertools.product(NOISES, SEEDS):
        p = RES / f"{n}_{s}.json"
        if not p.exists():
            print(f"MISSING {p.name} — adjudication refused (all 6 runs required)")
            return
        runs[(n, s)] = json.loads(p.read_text())

    print("== CRI Pilot V1 adjudication ==\n")

    # G1: total wall time
    total_s = sum(r["wall_s"] for r in runs.values())
    g1 = total_s < G1_BUDGET_S
    print(f"G1 computability: total wall {total_s/3600:.2f} h (< 4 h) -> {'PASS' if g1 else 'FAIL'}")

    # G2: cross-seed Spearman of D on GENUINE edges, per noise type & behavior.
    # Genuine edges are the original (pre-injection) edge list: identical order
    # across seeds because injection appends fakes after them.
    g2_vals = {}
    for n in NOISES:
        for b in ALL_B:
            rhos = []
            for s1, s2 in itertools.combinations(SEEDS, 2):
                z1 = np.load(RES / f"{n}_{s1}_scores.npz")
                z2 = np.load(RES / f"{n}_{s2}_scores.npz")
                m1, m2 = z1[f"mask_{b}"], z2[f"mask_{b}"]
                d1 = z1[f"D_{b}"][m1 == 0]
                d2 = z2[f"D_{b}"][m2 == 0]
                assert len(d1) == len(d2)
                rhos.append(spearman(d1, d2))
            g2_vals[(n, b)] = min(rhos)
    g2 = all(v >= G2_MIN_RHO for v in g2_vals.values())
    print(f"G2 stability (min pairwise Spearman of D, genuine edges >= {G2_MIN_RHO}):")
    for (n, b), v in g2_vals.items():
        print(f"    {n:10s} {b:5s} min rho = {v:.3f}")
    print(f"  -> {'PASS' if g2 else 'FAIL'}")

    # G3: AUC(D) - AUC(SI_pooled) >= +0.03 on >=1 noise type, BOTH aux
    # behaviors, ALL seeds.  G4: same conditions vs Loss.
    g3_by_noise, g4_by_noise = {}, {}
    for n in NOISES:
        ok3, ok4 = True, True
        for b in AUX:
            for s in SEEDS:
                a = runs[(n, s)]["auc"][b]
                if not (a["D"] - a["SI_pooled"] >= G3_MARGIN):
                    ok3 = False
                if not (a["D"] > a["Loss"]):
                    ok4 = False
        g3_by_noise[n] = ok3
        g4_by_noise[n] = ok4
    g3_noises = [n for n in NOISES if g3_by_noise[n]]
    g3 = len(g3_noises) > 0
    # G4 must hold under the same conditions as G3 (i.e. on a noise type where G3 holds)
    g4 = any(g3_by_noise[n] and g4_by_noise[n] for n in NOISES)

    print("G3 signal (AUC(D)-AUC(SI_pooled) >= +0.03, both aux, all seeds, per noise):")
    for n in NOISES:
        for b in AUX:
            deltas = [runs[(n, s)]["auc"][b]["D"] - runs[(n, s)]["auc"][b]["SI_pooled"] for s in SEEDS]
            print(f"    {n:10s} {b:5s} deltas: " + " ".join(f"{d:+.4f}" for d in deltas))
        print(f"    {n:10s} -> {'holds' if g3_by_noise[n] else 'fails'}")
    print(f"  -> {'PASS' if g3 else 'FAIL'}")
    print("G4 non-triviality (AUC(D) > AUC(Loss), same conditions):")
    for n in NOISES:
        for b in AUX:
            deltas = [runs[(n, s)]["auc"][b]["D"] - runs[(n, s)]["auc"][b]["Loss"] for s in SEEDS]
            print(f"    {n:10s} {b:5s} deltas: " + " ".join(f"{d:+.4f}" for d in deltas))
    print(f"  -> {'PASS' if g4 else 'FAIL'}")

    verdict = "ALL GATES PASS — escalate per prereg" if (g1 and g2 and g3 and g4) else "GATE FAILURE — RQ refuted/blocked at pilot scale per prereg"
    print(f"\nVERDICT: {verdict}")

    # full AUC table for the record
    print("\nFull AUC table (behavior / score / per-run):")
    for b in ALL_B:
        for score in ("D", "SI_b", "SI_pooled", "Loss"):
            cells = " ".join(f"{runs[(n,s)]['auc'][b][score]:.4f}" for n in NOISES for s in SEEDS)
            print(f"    {b:5s} {score:10s} {cells}")
    print("  (columns: uniform s13,s42,s2026 | popularity s13,s42,s2026)")


if __name__ == "__main__":
    main()
