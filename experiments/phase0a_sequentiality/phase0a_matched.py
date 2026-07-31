"""Phase 0a, matched: same #users AND same sequence length across all four corpora,
so n-gram support counts are comparable. Bootstrapped over user draws.

Also computes the rank correlation between each diagnostic variant and the
measured FIR effect, which is the actual RQ1 quantity.
"""
from __future__ import annotations

import random
import statistics
from itertools import combinations

from phase0a import load_ml1m, load_amazon, ngrams, freq, shuffle_all, CATS

# Measured learned-FIR minus identity, from the committed adjudications.
FIR_EFFECT = {
    "MovieLens1M_R4": 2.0248200248689646e-07,
    "Musical_Instruments": 0.0021156738685499136,
    "Industrial_and_Scientific": 0.002110,
    "CDs_and_Vinyl": 0.006150,
}

N_USERS = 1000     # ML-1M caps us at ~1000 users with >=10 events
L = 10
DRAWS = 20
SHUF_REPEATS = 3


def matched_sample(seqs, rng):
    pool = [v[-L:] for v in seqs.values() if len(v) >= L]
    if len(pool) < N_USERS:
        return None
    return {i: s for i, s in enumerate(rng.sample(pool, N_USERS))}


def spearman(xs, ys):
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        for pos, i in enumerate(order):
            r[i] = pos + 1.0
        return r
    rx, ry = rank(xs), rank(ys)
    n = len(xs)
    d2 = sum((a - b) ** 2 for a, b in zip(rx, ry))
    return 1 - 6 * d2 / (n * (n * n - 1))


def kendall(xs, ys):
    c = d = 0
    for i, j in combinations(range(len(xs)), 2):
        s = (xs[i] - xs[j]) * (ys[i] - ys[j])
        if s > 0:
            c += 1
        elif s < 0:
            d += 1
    return (c - d) / (c + d) if c + d else float("nan")


if __name__ == "__main__":
    data = {"MovieLens1M_R4": load_ml1m()}
    for c in CATS:
        data[c] = load_amazon(c)

    print(f"MATCHED: {N_USERS} users x last {L} items, {DRAWS} independent draws\n")

    results = {}
    for name, seqs in data.items():
        per_draw = {(n, s): [] for n in (2, 3) for s in (2,)}
        for d in range(DRAWS):
            rng = random.Random(9000 + d)
            samp = matched_sample(seqs, rng)
            if samp is None:
                break
            for n in (2, 3):
                base = freq(ngrams(samp, n), 2)
                if base == 0:
                    continue
                vals = [freq(ngrams(shuffle_all(samp, random.Random(500 + d * 17 + r)), n), 2)
                        for r in range(SHUF_REPEATS)]
                per_draw[(n, 2)].append((statistics.mean(vals) - base) / base * 100)
        results[name] = per_draw
        print(f"  {name}")
        for k, v in per_draw.items():
            if v:
                lo, hi = min(v), max(v)
                print(f"    {k[0]}-gram sup>=2: rel={statistics.mean(v):+7.2f}% "
                      f"(sd {statistics.stdev(v):.2f}, range [{lo:+.2f},{hi:+.2f}], n={len(v)})")

    print("\n" + "=" * 74)
    print("RQ1: does the diagnostic predict the measured FIR effect?")
    print("=" * 74)
    names = list(data)
    fir = [FIR_EFFECT[n] for n in names]
    for n_gram in (2, 3):
        diag = [statistics.mean(results[nm][(n_gram, 2)]) for nm in names]
        # more negative == stronger sequential structure
        strength = [-d for d in diag]
        print(f"\n  {n_gram}-gram sup>=2 (matched)")
        for nm, d, f in zip(names, diag, fir):
            print(f"    {nm:<28} diagnostic={d:+7.2f}%   FIR={f:+.6f}")
        print(f"    Spearman(sequentiality strength, FIR effect) = {spearman(strength, fir):+.3f}")
        print(f"    Kendall  (sequentiality strength, FIR effect) = {kendall(strength, fir):+.3f}")
