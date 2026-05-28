"""POC: CDR-3way — extend CDR_validated's cold blend to include a third
signal from a CLCRec content encoder. Validate the 2D simplex of weights
(alpha_content, alpha_ridge, alpha_clcrec) on inner validation.

Hypothesis: a prior agent's CDR-CL experiment showed that REPLACING Ridge
with CLCRec hurts (CDR-CL Beauty = 0.1361 vs CDR_validated 0.1483). But that
test only allowed CLCRec as a substitute. CDR-3way keeps both Ridge AND
content_direct AND adds CLCRec as a third orthogonal signal; the inner
validator can choose any blend, including zero-weight on CLCRec if it's
uninformative.

If CLCRec carries any orthogonal signal that Ridge misses (e.g. it picks
up CF patterns Ridge's linear projection cannot), the simplex search should
find a non-trivial blend. If CLCRec is just a weaker Ridge, the validator
will collapse to alpha_clcrec ≈ 0 and we recover CDR_validated.

Foreground execution (fast on Beauty in <5 min). Scale to Fashion/Instr if
the Beauty result shows real improvement.
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
from itertools import product
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import torch
from scipy.sparse import csr_matrix
from scipy.stats import wilcoxon
from sklearn.linear_model import Ridge

from ease_efficient import ease_fast
from run_cold_item import DATASET_KCORE, HP, make_item_kfold
from v5_utils import NUM_FOLDS, ROOT, TOP_K, content_sim_matrix, kcore_filter, reindex

# Reuse CLCRec training utilities
from run_faithful_clcrec import (
    ContentEncoder, NORMALIZE, encode_all, train_bpr, train_clcrec_encoder,
)


SEED = 20260521

# Compact 2D simplex grid: 9 (alpha_cd, alpha_ridge, alpha_clcrec) tuples
# with alpha_cd + alpha_ridge + alpha_clcrec = 1. Sweep 0/0.25/0.5/0.75/1.0
# subject to the simplex constraint.
SIMPLEX_GRID = []
for a_cd in [0.0, 0.1, 0.25, 0.4, 0.5]:
    for a_ridge in [0.0, 0.25, 0.5, 0.75, 1.0]:
        a_cl = 1.0 - a_cd - a_ridge
        if -1e-6 <= a_cl <= 1.0 + 1e-6:
            SIMPLEX_GRID.append((round(a_cd, 3), round(a_ridge, 3), round(max(0.0, a_cl), 3)))

# Reduce to unique tuples
SIMPLEX_GRID = sorted(set(SIMPLEX_GRID))
print(f"# Simplex grid has {len(SIMPLEX_GRID)} (alpha_cd, alpha_ridge, alpha_clcrec) tuples.")


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


def _z_per_user(x):
    m = x.mean(axis=1, keepdims=True)
    s = np.maximum(x.std(axis=1, keepdims=True), 1e-8)
    return (x - m) / s


def make_score_cdr3way(Xw, B_warm, warm_indices, cold_indices, S_content,
                         emb_np, U_cf, V_warm_cf, model_clcrec, n_items,
                         alpha_cd, alpha_ridge, alpha_clcrec):
    """Compute the 3-way blend for cold items. Warm items keep raw EASE scores."""
    n_warm = len(warm_indices); n_cold = len(cold_indices)
    SBERT_w = emb_np[warm_indices].astype(np.float32)
    SBERT_c = emb_np[cold_indices].astype(np.float32)

    # 1) content_direct cold signal
    S_w_c = S_content[np.ix_(warm_indices, cold_indices)].astype(np.float32)

    # 2) LC2C Ridge cold signal
    reg = Ridge(alpha=1.0); reg.fit(SBERT_w, B_warm.T.astype(np.float32))
    B_hat_cold = (SBERT_c @ reg.coef_.T.astype(np.float32)).T.astype(np.float32)

    # 3) CLCRec cold signal: V_cold = encoder(SBERT_cold); score(u, j_cold) = U_cf[u] . V_cold[j]
    with torch.no_grad():
        V_cold_cl = encode_all(model_clcrec, SBERT_c)  # (n_cold, k_cf)
    if NORMALIZE:
        norms = np.linalg.norm(V_cold_cl, axis=1, keepdims=True)
        V_cold_cl = V_cold_cl / np.maximum(norms, 1e-12)
        V_warm_norm = V_warm_cf / np.maximum(np.linalg.norm(V_warm_cf, axis=1, keepdims=True), 1e-12)
    else:
        V_warm_norm = V_warm_cf

    def f(uids):
        warm_scores = Xw[uids] @ B_warm
        # cold raw scores
        cd_cold = Xw[uids] @ S_w_c
        lc_cold = Xw[uids] @ B_hat_cold
        cl_cold = U_cf[uids] @ V_cold_cl.T  # (b, n_cold)
        # z-norm each
        zcd = _z_per_user(cd_cold)
        zlc = _z_per_user(lc_cold)
        zcl = _z_per_user(cl_cold)
        cold_blend = alpha_cd * zcd + alpha_ridge * zlc + alpha_clcrec * zcl

        out = np.empty((len(uids), n_items), dtype=np.float32)
        out[:, warm_indices] = warm_scores
        out[:, cold_indices] = cold_blend
        return out
    return f


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


def select_simplex(dataset, outer_train, outer_cold_items, S_content, emb_np,
                    n_users, n_items, rng, bpr_epochs=40,
                    tau=0.2, lr=1e-3, hidden=128):
    """Inner validation: hold out 20% of warm items as 'inner cold',
    retrain inner EASE + inner CLCRec, pick (alpha_cd, alpha_ridge, alpha_clcrec) maximising inner-val NDCG@10."""
    outer_warm = sorted(set(range(n_items)) - set(outer_cold_items))
    shuf = np.array(outer_warm, dtype=np.int32); rng.shuffle(shuf)
    n_val = max(1, int(0.2 * len(shuf)))
    val_items = set(shuf[:n_val].tolist())
    val_inters = [x for x in outer_train if int(x["item_id"]) in val_items]
    if not val_inters: return (0.25, 0.75, 0.0), {}
    inner_cold = sorted(set(outer_cold_items) | val_items)
    inner_warm = np.array(sorted(set(range(n_items)) - set(inner_cold)), dtype=np.int32)
    inner_train = [x for x in outer_train if int(x["item_id"]) not in val_items]
    X_in, Xw_in = build_warm(inner_train, n_users, inner_warm)
    S_warm_in = S_content[np.ix_(inner_warm, inner_warm)]
    lam, beta = HP[dataset]
    B_in = ease_fast(X_in, lam=lam, beta=beta, S_content=S_warm_in, dtype=np.float32)

    # Train inner BPR + CLCRec
    inner_seed = int(rng.randint(0, 2**31 - 1))
    U_inner, V_warm_inner, _ = train_bpr(inner_train, inner_warm, n_users, inner_seed,
                                          n_epochs=bpr_epochs)
    model_inner, _ = train_clcrec_encoder(emb_np[inner_warm], V_warm_inner, inner_seed,
                                            tau=tau, lr=lr, hidden=hidden)

    cold_arr = np.array(sorted(inner_cold), dtype=np.int32)
    scores = {}
    for (a_cd, a_ridge, a_cl) in SIMPLEX_GRID:
        sf = make_score_cdr3way(Xw_in, B_in, inner_warm, cold_arr, S_content,
                                  emb_np, U_inner, V_warm_inner, model_inner,
                                  n_items, alpha_cd=a_cd, alpha_ridge=a_ridge,
                                  alpha_clcrec=a_cl)
        m, _ = eval_full(sf, inner_train, val_inters, n_items)
        scores[(a_cd, a_ridge, a_cl)] = m
    del X_in, Xw_in, B_in, U_inner, V_warm_inner, model_inner; gc.collect()
    if torch.cuda.is_available(): torch.cuda.empty_cache()
    best = max(scores, key=scores.get)
    return best, scores


def run(dataset, seeds, bpr_epochs=40, tau=0.2, lr=1e-3, hidden=128):
    print(f"\n{'#'*70}\n# CDR-3way POC: {dataset.upper()}\n{'#'*70}")
    interactions, n_users, n_items, item_title_emb = load_dataset(dataset)
    emb_np = item_title_emb.cpu().numpy().astype(np.float32) if hasattr(item_title_emb, "cpu") else np.asarray(item_title_emb, dtype=np.float32)
    S_content = content_sim_matrix(item_title_emb, dtype=np.float32)
    lam, beta = HP[dataset]
    k = DATASET_KCORE[dataset]
    print(f"  n_users={n_users:,}  n_items={n_items:,}  k={k}  lambda={lam}  beta={beta}")
    print(f"  bpr_epochs={bpr_epochs}  tau={tau}  lr={lr}  hidden={hidden}")

    perfold_3way = []
    perfold_cdr = []  # baseline CDR_validated for comparison
    perfold_cdrcl_baseline = []  # pure CLCRec-replacement variant
    per_user_3way = defaultdict(list)
    per_user_cdr = defaultdict(list)
    selected = []

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

            # Outer BPR + CLCRec encoder
            U_out, V_warm_out, _ = train_bpr(train_inters, warm_idx, n_users, seed,
                                                n_epochs=bpr_epochs)
            model_out, _ = train_clcrec_encoder(emb_np[warm_idx], V_warm_out, seed,
                                                  tau=tau, lr=lr, hidden=hidden)

            # Inner-validation selection of simplex weights
            val_rng = np.random.RandomState((seed * 1000 + fold_id + 7) & 0xFFFFFFFF)
            best, _ = select_simplex(dataset, train_inters, set(cold), S_content,
                                      emb_np, n_users, n_items, val_rng,
                                      bpr_epochs=bpr_epochs, tau=tau, lr=lr, hidden=hidden)
            selected.append({"seed": seed, "fold_id": fold_id, "chosen_simplex": best})

            # Final scoring with chosen simplex
            sf_3way = make_score_cdr3way(Xw, B_warm, warm_idx, cold_idx, S_content,
                                           emb_np, U_out, V_warm_out, model_out, n_items,
                                           alpha_cd=best[0], alpha_ridge=best[1], alpha_clcrec=best[2])
            m_3way, pu_3way = eval_full(sf_3way, train_inters, test_inters, n_items)
            perfold_3way.append(m_3way)
            for u, v in pu_3way.items(): per_user_3way[u].append(v)

            # CDR_validated baseline (alpha_cd + alpha_ridge = 1, alpha_clcrec = 0; alpha_cd=0.25 default)
            # Reuse the same blend code with alpha_clcrec=0
            sf_cdr = make_score_cdr3way(Xw, B_warm, warm_idx, cold_idx, S_content,
                                          emb_np, U_out, V_warm_out, model_out, n_items,
                                          alpha_cd=0.25, alpha_ridge=0.75, alpha_clcrec=0.0)
            m_cdr, pu_cdr = eval_full(sf_cdr, train_inters, test_inters, n_items)
            perfold_cdr.append(m_cdr)
            for u, v in pu_cdr.items(): per_user_cdr[u].append(v)

            # Pure CLCRec-replacement (CDR-CL): alpha_cd=0.25, alpha_ridge=0, alpha_clcrec=0.75
            sf_clcl = make_score_cdr3way(Xw, B_warm, warm_idx, cold_idx, S_content,
                                            emb_np, U_out, V_warm_out, model_out, n_items,
                                            alpha_cd=0.25, alpha_ridge=0.0, alpha_clcrec=0.75)
            m_clcl, _ = eval_full(sf_clcl, train_inters, test_inters, n_items)
            perfold_cdrcl_baseline.append(m_clcl)

            print(f"  seed={seed} fold={fold_id}  CDR(0.25,0.75,0)={m_cdr:.4f}  "
                  f"3way({best[0]},{best[1]},{best[2]})={m_3way:.4f}  "
                  f"CDR-CL(0.25,0,0.75)={m_clcl:.4f}  delta_3way_vs_CDR={m_3way-m_cdr:+.4f}  "
                  f"[fold {time.time()-t0:.1f}s]")
            del X_sparse, Xw, B_warm, S_warm, U_out, V_warm_out, model_out; gc.collect()
            if torch.cuda.is_available(): torch.cuda.empty_cache()

    print(f"\n=== {dataset.upper()} fold means (NDCG@10) ===")
    print(f"  CDR_validated baseline:   {np.mean(perfold_cdr):.4f} +/- {np.std(perfold_cdr):.4f}")
    print(f"  CDR-3way (validated):     {np.mean(perfold_3way):.4f} +/- {np.std(perfold_3way):.4f}  delta={np.mean(perfold_3way)-np.mean(perfold_cdr):+.4f}")
    print(f"  CDR-CL (Ridge replaced):  {np.mean(perfold_cdrcl_baseline):.4f} +/- {np.std(perfold_cdrcl_baseline):.4f}")

    # Per-USER Wilcoxon
    print(f"\n=== Per-USER Wilcoxon (CDR-3way vs CDR_validated, one-sided 'greater') ===")
    pu_3 = {u: float(np.mean(vs)) for u, vs in per_user_3way.items()}
    pu_c = {u: float(np.mean(vs)) for u, vs in per_user_cdr.items()}
    common = sorted(set(pu_3) & set(pu_c))
    diffs = np.array([pu_3[u] - pu_c[u] for u in common])
    if np.allclose(diffs, 0): p = 1.0
    else: p = float(wilcoxon(diffs, alternative='greater', zero_method='wilcox').pvalue)
    marker = '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else 'n.s.'
    print(f"  n={len(common)} delta_mean={diffs.mean():+.4f} p={p:.3e} {marker}")

    # Chosen simplex distribution
    print(f"\n=== Chosen simplex per fold ===")
    for s in selected:
        print(f"  seed={s['seed']} fold={s['fold_id']}: (alpha_cd, alpha_ridge, alpha_clcrec) = {s['chosen_simplex']}")

    return {
        "perfold_3way": list(map(float, perfold_3way)),
        "perfold_cdr": list(map(float, perfold_cdr)),
        "perfold_cdrcl": list(map(float, perfold_cdrcl_baseline)),
        "wilcoxon_3way_vs_cdr": {"n_users": len(common), "delta_mean": float(diffs.mean()),
                                    "p_one_sided_greater": p, "marker": marker},
        "selected_simplex": selected,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("datasets", nargs="*", default=["beauty"])
    ap.add_argument("--seeds", default=str(SEED))
    ap.add_argument("--bpr-epochs", type=int, default=40)
    ap.add_argument("--tau", type=float, default=0.2)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--hidden", type=int, default=128)
    ap.add_argument("--out", default="results_cdr3way_poc.json")
    args = ap.parse_args()
    seeds = [int(s) for s in args.seeds.split(",")]
    out_path = Path(__file__).parent / args.out
    payload = {"schema_version": 1, "candidate_scope": "full_catalog",
                "candidate_method": "CDR-3way (content + Ridge + CLCRec, validated simplex)",
                "baseline_method": "CDR_validated (CDR-3way with alpha_clcrec=0)",
                "seeds": seeds, "config": {"bpr_epochs": args.bpr_epochs,
                                              "tau": args.tau, "lr": args.lr,
                                              "hidden": args.hidden},
                "datasets": {}}
    for ds in args.datasets:
        payload["datasets"][ds] = run(ds, seeds, bpr_epochs=args.bpr_epochs,
                                         tau=args.tau, lr=args.lr, hidden=args.hidden)
        with out_path.open("w") as f:
            json.dump(payload, f, indent=2,
                       default=lambda o: float(o) if hasattr(o, "item") else str(o))
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()
