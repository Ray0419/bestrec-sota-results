"""POC: Joint-Augmented EASE (JEASE) — a new closed-form cold-item algorithm
that puts cold items INSIDE the EASE optimisation rather than predicting their
B-column post-hoc.

Diagnosis from prior work: every existing cold method (LC2C Ridge, CWA-B kNN,
kernel ridge, CDR z-cal blend) predicts a B-column for the cold item and then
applies the EASE scoring formula. The cold prediction never lives inside the
EASE structure — it has to be calibrated separately (z-norm trick) to compete
with raw warm EASE scores.

JEASE puts cold items inside the EASE solve directly via SYNTHETIC continuous
interactions derived from content affinity, then runs the standard closed-form
Tikhonov inversion on the augmented user-item matrix. Cold and warm B columns
emerge from the same optimisation, so their scores are automatically on the
same scale.

Algorithm:

  1. Synthetic cold interactions per user:
       X_cold_syn[u, j_cold] = (X_warm[u] · S_content[warm, j_cold]) / Z
     where Z is a per-user normaliser so cold columns have similar mass to
     warm columns (mean per-user warm-interaction count).

  2. Augmented matrix:
       X_aug = [X_warm  X_cold_syn]  ∈ R^(n_users × n_all)

  3. Closed-form EASE on X_aug with the standard SBERT prior:
       G_aug = X_aug^T X_aug + λI + β · S_content[all, all]
       B_aug = -G_aug^{-1} / diag(G_aug^{-1});  diag(B_aug) = 0

  4. Score(u, j) = (X_aug[u] @ B_aug)[j]  for both warm and cold j.

Usage:
    cd _bestrec_run
    uv run python run_jease_poc.py beauty fashion
"""
from __future__ import annotations

import argparse
import gc
import json
import math
import os
import pickle
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import torch
from scipy.sparse import csr_matrix
from scipy.stats import wilcoxon

from ease_efficient import ease_fast
from run_cold_item import DATASET_KCORE, HP, make_item_kfold
from v5_utils import NUM_FOLDS, ROOT, TOP_K, content_sim_matrix, kcore_filter, reindex


SEED = 20260521


def load_dataset(dataset):
    cache_dir = Path(ROOT) / "cache" / dataset
    data = pickle.load(open(cache_dir / "raw_data_dedup.pkl", "rb"))
    filtered = kcore_filter(data["interactions"], DATASET_KCORE[dataset])
    interactions, _, n_users, n_items, _ = reindex(filtered, data["item_metadata"])
    title_path = cache_dir / "v5" / f"item_title_k{DATASET_KCORE[dataset]}_dedup.pt"
    emb = torch.load(title_path, weights_only=True)
    return interactions, n_users, n_items, emb


def build_warm(train_inters, n_users, warm_indices):
    pos = {int(it): i for i, it in enumerate(warm_indices)}
    rows, cols = [], []
    for x in train_inters:
        p = pos.get(int(x["item_id"]))
        if p is None: continue
        rows.append(int(x["user_id"])); cols.append(p)
    X_sparse = csr_matrix((np.ones(len(rows), dtype=np.float32), (rows, cols)),
                           shape=(n_users, len(warm_indices)))
    return X_sparse, X_sparse.toarray().astype(np.float32)


# ---------------------------------------------------------------------------
# JEASE: Joint-Augmented EASE
# ---------------------------------------------------------------------------

def make_score_jease(Xw, warm_indices, cold_indices, S_content, n_items, n_users,
                      lam, beta, cold_mass_scale=1.0):
    """JEASE: augment X with synthetic cold-item interactions and run EASE
    on the joint matrix. cold_mass_scale controls how much weight cold columns
    get vs warm columns (1.0 = same per-user mass as warm)."""
    n_warm = len(warm_indices); n_cold = len(cold_indices)
    assert n_warm + n_cold == n_items

    # Synthetic cold interactions: each user's content affinity to each cold item
    S_w_c = S_content[np.ix_(warm_indices, cold_indices)].astype(np.float32)  # (n_warm, n_cold)
    X_cold_syn = Xw @ S_w_c                                                    # (n_users, n_cold)
    # Per-user normalise: each user's cold-side mass = their warm-side mass × cold_mass_scale
    user_warm_mass = Xw.sum(axis=1, keepdims=True)                             # (n_users, 1)
    user_cold_mass = X_cold_syn.sum(axis=1, keepdims=True)                     # (n_users, 1)
    safe_cold = np.maximum(user_cold_mass, 1e-8)
    X_cold_syn = X_cold_syn * (user_warm_mass * cold_mass_scale / safe_cold)   # rescale per user

    # Build augmented X (col order: warm in warm_indices order, then cold in cold_indices order)
    # We need to lay them out so that index j of the FULL catalog maps to the right column.
    # Approach: build X_aug_unordered = [Xw | X_cold_syn], compute B_aug, then permute back to full-item order.

    X_aug_unordered = np.concatenate([Xw, X_cold_syn], axis=1)                 # (n_users, n_all)
    # Permutation: original full-catalog index → augmented column index
    aug_col_for_full = np.empty(n_items, dtype=np.int64)
    for i, w in enumerate(warm_indices): aug_col_for_full[int(w)] = i
    for i, c in enumerate(cold_indices): aug_col_for_full[int(c)] = n_warm + i

    # Augmented content similarity matrix (in unordered layout)
    S_aug = np.empty((n_items, n_items), dtype=np.float32)
    S_aug[:n_warm, :n_warm] = S_content[np.ix_(warm_indices, warm_indices)]
    S_aug[:n_warm, n_warm:] = S_w_c
    S_aug[n_warm:, :n_warm] = S_w_c.T
    S_aug[n_warm:, n_warm:] = S_content[np.ix_(cold_indices, cold_indices)]

    # Standard EASE on augmented matrix
    # We reuse ease_fast which expects a sparse X. Convert dense to sparse.
    X_aug_sparse = csr_matrix(X_aug_unordered.astype(np.float32))
    B_aug = ease_fast(X_aug_sparse, lam=lam, beta=beta, S_content=S_aug, dtype=np.float32)

    # Now scoring: for user u, full-catalog score vector = X_aug_unordered[u] @ B_aug
    # But we need to PERMUTE the output back to full-catalog item order.
    # B_aug is (n_all_unordered × n_all_unordered) in [warm; cold] layout.
    # Permute rows + columns so output[full_idx] aligns.
    inv_perm = np.empty(n_items, dtype=np.int64)
    for full_idx, aug_col in enumerate(aug_col_for_full): inv_perm[aug_col] = full_idx

    # Pre-permute: B_perm[i, j] = B_aug[full→aug[i], full→aug[j]]
    # Equivalent to permuting B_aug rows and columns by inv_perm
    B_aug_full = B_aug[np.ix_(inv_perm.argsort(), inv_perm.argsort())]
    # Actually simpler: build X_aug in FULL-CATALOG ORDER from the start, skipping permutation.

    # Re-do with full-catalog ordering to avoid the permutation bookkeeping:
    X_aug_full = np.zeros((n_users, n_items), dtype=np.float32)
    X_aug_full[:, warm_indices] = Xw
    X_aug_full[:, cold_indices] = X_cold_syn
    # Re-run EASE on full-ordered matrix
    X_aug_full_sparse = csr_matrix(X_aug_full)
    B_full = ease_fast(X_aug_full_sparse, lam=lam, beta=beta, S_content=S_content, dtype=np.float32)

    def f(uids):
        return X_aug_full[uids] @ B_full
    return f


# ---------------------------------------------------------------------------
# Reference: CDR_validated (from run_poc_cdr_books.py)
# ---------------------------------------------------------------------------

CDR_ALPHA_GRID = [0.0, 0.1, 0.2, 0.25, 0.3, 0.4, 0.5, 0.75, 1.0]


def make_score_cdr(Xw, B_warm, warm_indices, cold_indices, S_content, emb, n_items, alpha):
    from sklearn.linear_model import Ridge
    SBERT_w = emb[warm_indices].astype(np.float32)
    SBERT_c = emb[cold_indices].astype(np.float32)
    reg = Ridge(alpha=1.0); reg.fit(SBERT_w, B_warm.T.astype(np.float32))
    B_hat_cold = (SBERT_c @ reg.coef_.T.astype(np.float32)).T.astype(np.float32)
    S_w_c = S_content[np.ix_(warm_indices, cold_indices)].astype(np.float32)
    def _z(x):
        m = x.mean(axis=1, keepdims=True); s = np.maximum(x.std(axis=1, keepdims=True), 1e-8)
        return (x - m) / s
    def f(uids):
        warm_scores = Xw[uids] @ B_warm
        cd_cold = _z(Xw[uids] @ S_w_c)
        lc_cold = _z(Xw[uids] @ B_hat_cold)
        cold_blend = alpha * cd_cold + (1.0 - alpha) * lc_cold
        out = np.empty((len(uids), n_items), dtype=np.float32)
        out[:, warm_indices] = warm_scores
        out[:, cold_indices] = cold_blend
        return out
    return f


def select_alpha(dataset, outer_train, outer_cold_items, S_content, emb,
                  n_users, n_items, rng):
    outer_warm = sorted(set(range(n_items)) - set(outer_cold_items))
    shuf = np.array(outer_warm, dtype=np.int32); rng.shuffle(shuf)
    n_val = max(1, int(0.2 * len(shuf)))
    val_items = set(shuf[:n_val].tolist())
    val_inters = [x for x in outer_train if int(x["item_id"]) in val_items]
    if not val_inters: return 0.25
    inner_cold = sorted(set(outer_cold_items) | val_items)
    inner_warm = np.array(sorted(set(range(n_items)) - set(inner_cold)), dtype=np.int32)
    inner_train = [x for x in outer_train if int(x["item_id"]) not in val_items]
    X_in, Xw_in = build_warm(inner_train, n_users, inner_warm)
    S_warm_in = S_content[np.ix_(inner_warm, inner_warm)]
    lam, beta = HP[dataset]
    B_in = ease_fast(X_in, lam=lam, beta=beta, S_content=S_warm_in, dtype=np.float32)
    cold_arr = np.array(sorted(inner_cold), dtype=np.int32)
    scores = {}
    for a in CDR_ALPHA_GRID:
        sf = make_score_cdr(Xw_in, B_in, inner_warm, cold_arr, S_content,
                              emb if isinstance(emb, np.ndarray) else emb.cpu().numpy().astype(np.float32),
                              n_items, alpha=a)
        m, _ = eval_full(sf, inner_train, val_inters, n_items)
        scores[float(a)] = m
    del X_in, Xw_in, B_in; gc.collect()
    return max(scores, key=scores.get)


# ---------------------------------------------------------------------------
# Evaluation (same as run_poc_cdr_books.eval_full)
# ---------------------------------------------------------------------------

def eval_full(score_fn, train_inters, test_inters, n_items, batch_size=192):
    ut = defaultdict(set); uts = defaultdict(list)
    for x in train_inters: ut[int(x["user_id"])].add(int(x["item_id"]))
    for x in test_inters: uts[int(x["user_id"])].append(int(x["item_id"]))
    users = sorted(u for u in uts if uts[u] and ut[u])
    ndcg, per_user_ndcg = [], defaultdict(list)
    for s in range(0, len(users), batch_size):
        batch = users[s:s + batch_size]
        scores = score_fn(np.array(batch, dtype=np.int32)).astype(np.float32, copy=True)
        for k, u in enumerate(batch):
            if ut[u]:
                scores[k, list(ut[u])] = -np.inf
            for tgt in uts[u]:
                ts = scores[k, tgt]
                r0 = int((scores[k] > ts).sum())
                n_ = 1.0 / math.log2(r0 + 2) if r0 < TOP_K else 0.0
                ndcg.append(n_); per_user_ndcg[int(u)].append(n_)
    return float(np.mean(ndcg)) if ndcg else 0.0, {u: float(np.mean(vs)) for u, vs in per_user_ndcg.items()}


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def run(dataset, seeds, cold_mass_scales=(0.5, 1.0, 2.0)):
    print(f"\n{'#'*70}\n# JEASE POC: {dataset.upper()}\n{'#'*70}")
    interactions, n_users, n_items, item_title_emb = load_dataset(dataset)
    emb_np = item_title_emb.cpu().numpy().astype(np.float32) if hasattr(item_title_emb, "cpu") else np.asarray(item_title_emb, dtype=np.float32)
    S_content = content_sim_matrix(item_title_emb, dtype=np.float32)
    lam, beta = HP[dataset]
    k = DATASET_KCORE[dataset]
    print(f"  n_users={n_users:,}  n_items={n_items:,}  k={k}  lambda={lam}  beta={beta}")

    rows = []
    for seed in seeds:
        splits = make_item_kfold(interactions, n_items, n_splits=NUM_FOLDS, seed=seed)
        for fold_id, (tr, te, cold) in enumerate(splits):
            t0 = time.time()
            train_inters = [interactions[i] for i in tr]
            test_inters = [interactions[i] for i in te]
            warm_idx = np.array(sorted(set(range(n_items)) - set(cold)), dtype=np.int32)
            cold_idx = np.array(sorted(cold), dtype=np.int32)
            X_sparse, Xw = build_warm(train_inters, n_users, warm_idx)
            S_warm = S_content[np.ix_(warm_idx, warm_idx)]
            B_warm = ease_fast(X_sparse, lam=lam, beta=beta, S_content=S_warm, dtype=np.float32)

            # Baseline: CDR_validated (the current SOTA on this protocol)
            val_rng = np.random.RandomState((seed * 1000 + fold_id + 7) & 0xFFFFFFFF)
            a = select_alpha(dataset, train_inters, set(cold), S_content, emb_np,
                              n_users, n_items, val_rng)
            sf_cdr = make_score_cdr(Xw, B_warm, warm_idx, cold_idx, S_content, emb_np, n_items, alpha=a)
            m_cdr, pu_cdr = eval_full(sf_cdr, train_inters, test_inters, n_items)

            row = {"seed": seed, "fold": fold_id, "alpha": a,
                    "CDR_validated_ndcg10": m_cdr, "CDR_validated_per_user": pu_cdr}

            # JEASE candidates with different cold-mass scales
            for cms in cold_mass_scales:
                sf_jease = make_score_jease(Xw, warm_idx, cold_idx, S_content, n_items,
                                              n_users, lam=lam, beta=beta,
                                              cold_mass_scale=cms)
                m_jease, pu_jease = eval_full(sf_jease, train_inters, test_inters, n_items)
                row[f"JEASE_cms={cms}_ndcg10"] = m_jease
                row[f"JEASE_cms={cms}_per_user"] = pu_jease
                print(f"  seed={seed} fold={fold_id} cms={cms:.1f}  "
                      f"CDR={m_cdr:.4f}  JEASE={m_jease:.4f}  delta={m_jease-m_cdr:+.4f}")
            rows.append(row)
            del X_sparse, Xw, B_warm, S_warm; gc.collect()
            print(f"  [fold {fold_id} done in {time.time()-t0:.1f}s]")

    # Aggregate
    print(f"\n=== {dataset.upper()} fold means (NDCG@10) ===")
    cdr_vals = [r["CDR_validated_ndcg10"] for r in rows]
    print(f"  CDR_validated:  {np.mean(cdr_vals):.4f} +/- {np.std(cdr_vals):.4f}")
    for cms in cold_mass_scales:
        vs = [r[f"JEASE_cms={cms}_ndcg10"] for r in rows]
        print(f"  JEASE cms={cms}:  {np.mean(vs):.4f} +/- {np.std(vs):.4f}  delta={np.mean(vs)-np.mean(cdr_vals):+.4f}")

    # Per-USER Wilcoxon
    print(f"\n=== Per-USER Wilcoxon (JEASE vs CDR_validated, one-sided 'greater') ===")
    pu_cdr_agg = defaultdict(list)
    for r in rows:
        for u, v in r["CDR_validated_per_user"].items(): pu_cdr_agg[u].append(v)
    pu_cdr_mean = {u: float(np.mean(vs)) for u, vs in pu_cdr_agg.items()}
    for cms in cold_mass_scales:
        pu_je_agg = defaultdict(list)
        for r in rows:
            for u, v in r[f"JEASE_cms={cms}_per_user"].items(): pu_je_agg[u].append(v)
        pu_je_mean = {u: float(np.mean(vs)) for u, vs in pu_je_agg.items()}
        common = sorted(set(pu_cdr_mean) & set(pu_je_mean))
        diffs = np.array([pu_je_mean[u] - pu_cdr_mean[u] for u in common])
        if np.allclose(diffs, 0): p = 1.0
        else: p = float(wilcoxon(diffs, alternative='greater', zero_method='wilcox').pvalue)
        marker = '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else 'n.s.'
        print(f"  JEASE cms={cms}: n={len(common)} delta_mean={diffs.mean():+.4f} p={p:.3e} {marker}")
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("datasets", nargs="*", default=["beauty"])
    ap.add_argument("--seeds", default=str(SEED))
    ap.add_argument("--cold-mass-scales", default="0.5,1.0,2.0")
    ap.add_argument("--out", default="results_jease_poc.json")
    args = ap.parse_args()
    seeds = [int(s) for s in args.seeds.split(",")]
    cms_list = [float(s) for s in args.cold_mass_scales.split(",")]
    out_path = Path(__file__).parent / args.out
    payload = {"schema_version": 1, "candidate_scope": "full_catalog",
                "candidate_method": "JEASE",
                "baseline_method": "CDR_validated",
                "seeds": seeds, "cold_mass_scales": cms_list,
                "datasets": {}}
    for ds in args.datasets:
        rows = run(ds, seeds, cms_list)
        payload["datasets"][ds] = {"rows": [{k: v for k, v in r.items()
                                              if not k.endswith("_per_user")}
                                             for r in rows]}
        with out_path.open("w") as f:
            json.dump(payload, f, indent=2,
                       default=lambda o: float(o) if hasattr(o, "item") else str(o))
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()
