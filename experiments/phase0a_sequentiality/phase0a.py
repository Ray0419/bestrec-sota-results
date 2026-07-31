"""Phase 0a: recompute the TORS shuffle diagnostic on OUR exact splits.

Training-free half (sequential rules / n-gram survival under shuffling), run on:
  - MovieLens1M_R4  (rebuilt bit-identical to the frozen FIR campaign split)
  - Musical_Instruments, Industrial_and_Scientific, CDs_and_Vinyl (AR2023 5-core, LLOO)

Also runs a LENGTH-MATCHED variant, because the n-gram metric is mechanically
sensitive to sequence length and ML-1M sequences are ~20x longer than Amazon's.
"""
from __future__ import annotations

import csv
import gzip
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path

import os

HERE = Path(__file__).resolve().parent
# repo root = two levels up from experiments/phase0a_sequentiality/, overridable
REPO = Path(os.environ.get("BESTREC_REPO", HERE.parent.parent))
ML1M = Path(os.environ.get(
    "ML1M_TRAIN",
    REPO / "_bestrec_run/private_ml1m_v1/splits/MovieLens1M_R4.train.csv"))
# where the AR2023 5-core *.csv.gz live (see README: fetch_amazon.sh)
AMZN = Path(os.environ.get("AMZN_DIR", HERE / "amzn"))
CATS = ["Musical_Instruments", "Industrial_and_Scientific", "CDs_and_Vinyl"]


def _rows(fh):
    for row in csv.DictReader(fh):
        yield row["user_id"], int(row["timestamp"]), row["parent_asin"]


def load_ml1m():
    """ML-1M train file is already the training history (global time-cutoff split)."""
    by_user = defaultdict(list)
    with ML1M.open(newline="", encoding="utf-8") as fh:
        for u, ts, item in _rows(fh):
            by_user[u].append((ts, item))
    return {u: [i for _, i in sorted(v)] for u, v in by_user.items()}


def load_amazon(cat):
    """AR2023 5-core + leave-last-one-out: train history = all but last two."""
    by_user = defaultdict(list)
    with gzip.open(AMZN / f"{cat}.csv.gz", "rt", encoding="utf-8") as fh:
        for u, ts, item in _rows(fh):
            by_user[u].append((ts, item))
    out = {}
    for u, v in by_user.items():
        seq = [i for _, i in sorted(v)]
        if len(seq) >= 3:
            out[u] = seq[:-2]
    return out


def ngrams(seqs, n):
    c = Counter()
    for items in seqs.values():
        for i in range(len(items) - n + 1):
            c[tuple(items[i:i + n])] += 1
    return c


def freq(counter, s):
    return sum(1 for v in counter.values() if v >= s)


def shuffle_all(seqs, rng):
    out = {}
    for u, items in seqs.items():
        cp = list(items)
        rng.shuffle(cp)
        out[u] = cp
    return out


def tail(seqs, L):
    """Length-match: keep only the last L items, drop users with < L."""
    return {u: v[-L:] for u, v in seqs.items() if len(v) >= L}


def report(seqs, label, repeats=5, seed=20260801):
    if not seqs:
        print(f"  {label}: EMPTY")
        return
    lens = [len(v) for v in seqs.values()]
    n_items = len({i for v in seqs.values() for i in v})
    print(f"\n  {label}")
    print(f"    users={len(seqs):>7}  items={n_items:>6}  events={sum(lens):>8}  "
          f"mean_len={statistics.mean(lens):>6.1f}")
    for n in (2, 3):
        for s in (2, 5):
            base = freq(ngrams(seqs, n), s)
            if base == 0:
                print(f"    {n}-gram sup>={s}: original=0 (undefined)")
                continue
            vals = [freq(ngrams(shuffle_all(seqs, random.Random(seed + r)), n), s)
                    for r in range(repeats)]
            m = statistics.mean(vals)
            print(f"    {n}-gram sup>={s}: original={base:>7}  shuffled={m:>9.1f}  "
                  f"rel={((m - base) / base * 100):+7.2f}%")


if __name__ == "__main__":
    data = {"MovieLens1M_R4": load_ml1m()}
    for c in CATS:
        data[c] = load_amazon(c)

    print("=" * 78)
    print("NATIVE (as the FIR campaigns consumed them)")
    print("=" * 78)
    for k, v in data.items():
        report(v, k)

    for L in (5, 10):
        print("\n" + "=" * 78)
        print(f"LENGTH-MATCHED: last {L} items per user, users with >= {L}")
        print("=" * 78)
        for k, v in data.items():
            report(tail(v, L), f"{k} (L={L})")
