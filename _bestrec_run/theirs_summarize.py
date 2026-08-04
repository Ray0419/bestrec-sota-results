#!/usr/bin/env python
"""Summarize a theirs_train run: last / best full-corpus eval from metrics.jsonl.

Usage: theirs_summarize.py <run_dir> [run_dir ...]

Their trainer does a FULL eval (whole eval set, full item corpus) every
`full_eval_every_n` epochs (5 in all shipped gins) and a partial eval
(64x128 users) otherwise. The rows tee'd with prefix "eval_epoch_full" are
the full ones; the published tables correspond to the final-epoch full eval
(num_epochs=101 -> last epoch index 100, 100 % 5 == 0 -> full).
"""
from __future__ import annotations

import json
import os
import sys

KEYS = ["hr@10", "hr@50", "hr@100", "hr@200", "ndcg@10", "ndcg@50",
        "ndcg@100", "ndcg@200", "mrr"]


def load(run_dir: str):
    path = os.path.join(run_dir, "metrics.jsonl")
    rows = []
    with open(path) as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return rows


def fmt(rec, keys=KEYS):
    return "  ".join(f"{k}={rec.get(k, float('nan')):.4f}" for k in keys if k in rec)


def main() -> int:
    for run_dir in sys.argv[1:]:
        rows = load(run_dir)
        full = [r for r in rows if r.get("prefix") == "eval_epoch_full"]
        epoch = [r for r in rows if r.get("prefix") == "eval_epoch"]
        print(f"== {run_dir}")
        print(f"   rows: {len(rows)} total, {len(full)} full-eval epochs, "
              f"{len(epoch)} epoch evals")
        if full:
            last = full[-1]
            best = max(full, key=lambda r: r.get("ndcg@10", -1))
            print(f"   LAST full eval (epoch {last['batch_id']}): {fmt(last)}")
            print(f"   BEST full eval by ndcg@10 (epoch {best['batch_id']}): {fmt(best)}")
        elif epoch:
            last = epoch[-1]
            print(f"   LAST epoch eval (partial eval possible!) "
                  f"(epoch {last['batch_id']}): {fmt(last)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
