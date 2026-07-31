"""Training-free half of the TORS shuffle diagnostic (Klimashevskaia et al. 2025).

Sequential-rules metric: count n-grams surviving a support threshold in the
original user sequences vs. in order-shuffled sequences. Their stated reading:
a relative change *above* -90% indicates weak sequential structure.

Pure stdlib. Reads the frozen split CSVs.
"""
from __future__ import annotations

import csv
import random
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path


def load_sequences(path: Path):
    """Return {user: [items in timestamp order]} from a split CSV."""
    by_user = defaultdict(list)
    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            by_user[row["user_id"]].append(
                (int(row["timestamp"]), row["parent_asin"]))
    return {u: [i for _, i in sorted(rows)] for u, rows in by_user.items()}


def ngram_counts(seqs, n):
    c = Counter()
    for items in seqs.values():
        for i in range(len(items) - n + 1):
            c[tuple(items[i:i + n])] += 1
    return c


def frequent(counter, min_support):
    return sum(1 for v in counter.values() if v >= min_support)


def shuffled(seqs, rng):
    out = {}
    for u, items in seqs.items():
        cp = list(items)
        rng.shuffle(cp)
        out[u] = cp
    return out


def diagnose(seqs, label, n_repeats=5, seed=20260801):
    print(f"\n=== {label} ===")
    n_users = len(seqs)
    lengths = [len(v) for v in seqs.values()]
    n_items = len({i for v in seqs.values() for i in v})
    print(f"users={n_users}  items={n_items}  events={sum(lengths)}  "
          f"mean_len={statistics.mean(lengths):.1f}  median_len={statistics.median(lengths):.0f}")

    rows = []
    for n in (2, 3):
        orig = ngram_counts(seqs, n)
        for min_support in (2, 5):
            base = frequent(orig, min_support)
            shuf_vals = []
            for r in range(n_repeats):
                rng = random.Random(seed + r)
                shuf_vals.append(frequent(ngram_counts(shuffled(seqs, rng), n),
                                          min_support))
            mean_shuf = statistics.mean(shuf_vals)
            rel = (mean_shuf - base) / base * 100 if base else float("nan")
            rows.append((n, min_support, base, mean_shuf, rel))
            print(f"  {n}-gram support>={min_support}: "
                  f"original={base:>7}  shuffled={mean_shuf:>9.1f}  "
                  f"relative change={rel:+7.2f}%")
    return rows


if __name__ == "__main__":
    for path in sys.argv[1:]:
        p = Path(path)
        diagnose(load_sequences(p), p.name)
