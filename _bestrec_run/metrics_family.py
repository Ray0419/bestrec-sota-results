# -*- coding: utf-8 -*-
"""Exact top-k ranking metric family from per-user target ranks (rank0).

Our task is implicit-feedback, leave-last-out NEXT-ITEM ranking over the full
item catalog. The correct evaluation family is therefore ranking metrics, all of
which are EXACT deterministic functions of one number per user: rank0, the
0-indexed position of the held-out true target in the model's full-catalog
ranking (rank0=0 => the target was ranked first).

  HR@k      = mean( rank0 < k )                      # = Recall@k for 1 target
  NDCG@k    = mean( 1/log2(rank0+2)  if rank0<k else 0 )
  MRR       = mean( 1/(rank0+1) )                    # full-rank, always resolves
  MRR@k     = mean( 1/(rank0+1)      if rank0<k else 0 )
  Precision@k = HR@k / k                             # trivial for 1 target

Deliberately NOT computed: MSE / RMSE / MAE. Those are rating-prediction
(explicit-feedback) error metrics; this protocol has no held-out numeric rating
to compute squared error against, so they are undefined here and reporting them
would be a task/metric mismatch. See PAPER_PUSH_PLAN.md.

This module ADDS reporting cutoffs to already-run models; it introduces no new
model and no new counted claim. The two counted comparisons stay frozen at
NDCG@10 (which this reproduces bit-for-bit from the same ranks).
"""
import json
import math

import numpy as np

CUTOFFS = (5, 10, 20, 50)


def family_from_rank0(rank0, cutoffs=CUTOFFS):
    """rank0: 1-D int array/list of 0-indexed target ranks. Returns metric dict."""
    r = np.asarray(rank0, dtype=np.int64)
    n = int(r.size)
    if n == 0:
        return {"n_eval": 0}
    out = {"n_eval": n}
    inv_log = 1.0 / np.log2(r + 2.0)          # DCG gain per user (single target)
    rr = 1.0 / (r + 1.0)                        # reciprocal rank per user
    for k in cutoffs:
        within = r < k
        out[f"HR@{k}"] = float(within.mean())            # = Recall@{k}
        out[f"NDCG@{k}"] = float(np.where(within, inv_log, 0.0).mean())
        out[f"MRR@{k}"] = float(np.where(within, rr, 0.0).mean())
    out["MRR"] = float(rr.mean())              # unrestricted (always resolves)
    return out


def load_rank0(path, key="rank0"):
    """Load a rank0 vector from a JSON sidecar (dict with `key`, or nested
    _user_records) or an .npz with a rank0/rank0-like array."""
    if path.endswith(".npz"):
        d = np.load(path)
        for k in (key, "rank0", "rank", "ranks"):
            if k in d:
                return np.asarray(d[k], dtype=np.int64)
        raise KeyError(f"no rank0-like key in {path}: {list(d.keys())}")
    with open(path, encoding="utf-8") as f:
        j = json.load(f)
    if isinstance(j, dict):
        if key in j:
            return np.asarray(j[key], dtype=np.int64)
        if "_user_records" in j and key in j["_user_records"]:
            return np.asarray(j["_user_records"][key], dtype=np.int64)
    raise KeyError(f"no `{key}` in {path}")


def _selftest():
    r = [0, 4, 9, 19, 100]
    m = family_from_rank0(r)
    exp = {
        "HR@5": 2 / 5, "HR@10": 3 / 5, "HR@20": 4 / 5, "HR@50": 4 / 5,
        "NDCG@10": (1.0 + 1/math.log2(6) + 1/math.log2(11)) / 5,
        "MRR": (1 + 1/5 + 1/10 + 1/20 + 1/101) / 5,
    }
    for k, v in exp.items():
        assert abs(m[k] - v) < 1e-9, (k, m[k], v)
    # NDCG monotonic in k; HR monotonic in k
    assert m["NDCG@5"] <= m["NDCG@10"] <= m["NDCG@20"] <= m["NDCG@50"]
    assert m["HR@5"] <= m["HR@10"] <= m["HR@20"] <= m["HR@50"]
    print("metrics_family selftest PASS:",
          {k: round(v, 5) for k, v in m.items() if k != "n_eval"})


if __name__ == "__main__":
    _selftest()
