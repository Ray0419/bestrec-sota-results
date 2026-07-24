# -*- coding: utf-8 -*-
"""E-E V2 — ONE shared exact-rank evaluator, used UNCHANGED by both arms.

Root fix for the audit-2026-07-24-16:00 finding: the E-E pilot compared two
different evaluators (AlphaFuse ranks the catalogue unmasked; our paper evaluator
masks the user's consumed history), so it was not the same estimand. E-E V2 feeds
BOTH arms' per-user full-catalogue scores through this single module, so the
candidate set, masking, tie policy, and cutoffs are identical by construction.

FROZEN POLICY (frozen before any E-E V2 number; both arms obey it verbatim):
  - Eligibility     : the full item catalogue, ids 0..n_items-1.
  - Seen-item mask  : mask_seen=True -> every item in the user's train+val history
                      is removed from the candidate set (score -> -inf), matching
                      our paper's counted convention (do not re-rank consumed
                      items). The held-out TARGET is NEVER masked, even if it also
                      appears earlier in the history.
  - Tie policy      : rank0 = number of ELIGIBLE items scoring STRICTLY GREATER
                      than the target (deterministic; ties do not count against
                      the target). This matches run_sasrec_sbert.py's
                      (scores > target).sum().
  - Metrics         : HR/NDCG/MRR@{5,10,20,50} via metrics_family.family_from_rank0
                      (exact functions of rank0).

This module holds NO model and reads NO trained weights; it is a pure scoring
policy + its tests. Arm wrappers (AlphaFuse checkpoint -> scores; our stack ->
pre-mask scores) feed it and are separate, per PREREG_EE ERRATUM E2.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "_bestrec_run"))
from metrics_family import family_from_rank0, CUTOFFS  # noqa: E402

FROZEN_POLICY = {
    "eligibility": "full catalogue 0..n_items-1",
    "mask_seen": True,
    "target_never_masked": True,
    "tie_policy": "strict-greater (rank0 = #{eligible : score > target_score})",
    "metrics": f"HR/NDCG/MRR@{list(CUTOFFS)} from rank0",
    "frozen": "2026-07-24 (PREREG_EE ERRATUM E2, E-E V2)",
}


def target_rank0(scores, target, seen=None, mask_seen=True):
    """scores: 1-D array of length n_items (a model's full-catalogue scores for
    ONE user). Returns rank0 (0-indexed position of `target`) under the frozen
    policy. Both E-E arms call THIS, unchanged."""
    s = np.asarray(scores, dtype=np.float64).copy()
    n = s.size
    if not (0 <= target < n):
        raise ValueError(f"target {target} out of range [0,{n})")
    if mask_seen and seen:
        idx = [int(i) for i in seen if 0 <= int(i) < n and int(i) != target]
        if idx:
            s[idx] = -np.inf
    ts = s[target]
    if not np.isfinite(ts):
        raise ValueError("target score is not finite (target masked?)")
    # strict-greater over eligible items; the target never outranks itself.
    return int((s > ts).sum())


def family_from_score_records(records, mask_seen=True):
    """records: iterable of (scores, target, seen). Returns the metric family
    computed from per-user rank0 under the frozen policy."""
    ranks = [target_rank0(sc, tg, se, mask_seen) for (sc, tg, se) in records]
    fam = family_from_rank0(ranks)
    fam["_ranks"] = ranks
    return fam


def _selftest():
    # (a) masking changes the rank: a SEEN item outranks the target.
    # scores: item0=5 (seen), item1(target)=3, item2=1, item3=4
    sc = np.array([5.0, 3.0, 1.0, 4.0])
    # unmasked: items scoring > 3 are {0(5),3(4)} -> rank0=2
    assert target_rank0(sc, 1, seen={0}, mask_seen=False) == 2
    # masked (item0 removed): only {3(4)} > 3 -> rank0=1
    assert target_rank0(sc, 1, seen={0}, mask_seen=True) == 1

    # (b) ties: three items equal the target's score -> they do NOT count.
    sc2 = np.array([2.0, 2.0, 2.0, 2.0, 9.0])  # target=1 (score 2); one item (9) > 2
    assert target_rank0(sc2, 1, seen=set(), mask_seen=True) == 1

    # (c) target is NEVER masked even if it appears in `seen`.
    sc3 = np.array([1.0, 5.0, 1.0])  # target=1 (top score); seen includes target
    assert target_rank0(sc3, 1, seen={1, 0}, mask_seen=True) == 0

    # (d) rank0 -> cutoff metrics are exact (rank0=0 => HR@5..50 all 1).
    fam = family_from_score_records(
        [(np.array([9.0, 1.0, 1.0]), 0, set())], mask_seen=True)
    assert fam["HR@5"] == 1.0 and fam["NDCG@10"] == 1.0 and fam["_ranks"] == [0]

    # (e) determinism: repeat (a) many times, identical.
    r = {target_rank0(sc, 1, seen={0}, mask_seen=True) for _ in range(50)}
    assert r == {1}
    print("ee_shared_eval selftest PASS; frozen policy:",
          {k: FROZEN_POLICY[k] for k in ("mask_seen", "tie_policy")})


if __name__ == "__main__":
    _selftest()
