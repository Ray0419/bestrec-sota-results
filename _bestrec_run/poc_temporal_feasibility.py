# -*- coding: utf-8 -*-
"""Loop 3 scoping: is a global-time protocol feasible on MI/VG?

Ports the parallel session's protocol semantics (run_poc_temporal_lc2c_v1.py):
  cutoff        = pooled interaction-time quantile
  item is COLD  = first observed interaction later than the cutoff
  availability  = an item may only be a candidate at time t if first(item) <= t

and asks the decisive sizing questions for OUR stack:
  - how many interactions/users/items survive as TRAIN before the cutoff?
  - how many eval events fall in the post-cutoff window?
  - how many of those events target a COLD item (the natural prevalence pi_t)?
  - how many distinct cold items are actually reachable?

Read-only against the main checkout. No GPU.
"""
import csv
import os
import sys
from collections import defaultdict

import numpy as np

MAIN = r"C:\Users\rayxc\Documents\R"
SPLIT = os.path.join(MAIN, "data_5core", "5core", "last_out")
CUTS = (0.60, 0.75, 0.85)


def load(cat):
    """All interactions across the three LLOO files, as (user, item, ts)."""
    ev = []
    for part in ("train", "valid", "test"):
        p = os.path.join(SPLIT, f"{cat}.{part}.csv")
        with open(p, encoding="utf-8", newline="") as f:
            r = csv.reader(f)
            h = next(r)
            ui, ii, ti = h.index("user_id"), h.index("parent_asin"), h.index("timestamp")
            for row in r:
                ev.append((row[ui], row[ii], int(row[ti])))
    return ev


def report(cat):
    ev = load(cat)
    ts = np.array([e[2] for e in ev], dtype=np.int64)
    first = {}
    for u, i, t in ev:
        if i not in first or t < first[i]:
            first[i] = t
    n_items = len(first)
    n_users = len({e[0] for e in ev})
    print(f"\n=== {cat} ===")
    print(f"  interactions {len(ev):,}  users {n_users:,}  items {n_items:,}")
    yrs = np.array([1970 + t / 1000 / 31557600 for t in ts])
    print(f"  time span: {yrs.min():.1f} .. {yrs.max():.1f}  "
          f"(median {np.median(yrs):.1f})")

    for q in CUTS:
        cut = int(np.quantile(ts, q, method="nearest"))
        cold_items = {i for i, t in first.items() if t > cut}
        # events after the cutoff = the evaluable window
        post = [e for e in ev if e[2] > cut]
        # a post-cutoff event is a COLD target if its item first appeared after cut
        cold_ev = [e for e in post if e[1] in cold_items]
        # users with at least one pre-cutoff interaction (needed for a history)
        pre_users = {e[0] for e in ev if e[2] <= cut}
        evaluable = [e for e in post if e[0] in pre_users]
        evaluable_cold = [e for e in evaluable if e[1] in cold_items]
        # distinct cold items actually hit in the window
        hit_cold = {e[1] for e in evaluable_cold}
        n_pre = sum(1 for e in ev if e[2] <= cut)
        print(f"  q={q:.2f}: train {n_pre:,} inters ({100*n_pre/len(ev):.0f}%) | "
              f"post-window {len(post):,} events")
        print(f"          cold items {len(cold_items):,} "
              f"({100*len(cold_items)/n_items:.1f}% of catalog) | "
              f"evaluable events {len(evaluable):,} "
              f"(users with history)")
        pi = 100 * len(evaluable_cold) / max(len(evaluable), 1)
        print(f"          COLD targets {len(evaluable_cold):,} => "
              f"natural prevalence pi_t = {pi:.2f}%  | "
              f"distinct cold items hit {len(hit_cold):,}")


if __name__ == "__main__":
    for cat in (sys.argv[1:] or ["Musical_Instruments", "Video_Games"]):
        report(cat)
