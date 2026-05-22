"""LC2C component ablation — does each piece of LC2C actually contribute?

Tests four variants on cold-item evaluation:
  V0. content_direct                       baseline (no LC2C)        score = X[u, warm] @ S[warm, cold]
  V1. lc2c full (SVD + Ridge)              legacy/ablation (k=64)    score = (X[u, warm] @ E_cf) @ E_cf_cold.T
  V2. lc2c (no SVD, direct B-row regression) OURS (HEADLINE)         Ridge SBERT -> B_warm row
  V3. lc2c (no Ridge, nearest-warm in SBERT) ablation                for each cold j: nearest warm i, use E_cf_warm[i]

Plus latent dim sensitivity (V1 only):
  V1a. lc2c k=16
  V1b. lc2c k=64 (default for V1)
  V1c. lc2c k=256

Outputs results_ablation_lc2c.json.
NOTE: This file's internal V1/V2 naming predates round 2 of review, when we
adopted V2 as the canonical headline algorithm. The Table 5.4 / Table 5.4b
"ours" row is V2 (V2_lc2c_no_svd in this file's JSON keys), not V1 as the
docstring on line 5 implied in the original version.
"""
import os, sys, json, pickle, gc
sys.path.insert(0, os.path.dirname(__file__))
from collections import defaultdict
import numpy as np
import torch
from scipy.sparse import csr_matrix
from sklearn.decomposition import TruncatedSVD
from sklearn.linear_model import Ridge
from sklearn.metrics.pairwise import cosine_similarity

from ease_efficient import ease_fast
from v5_utils import (
    kcore_filter, reindex, build_X_sparse, content_sim_matrix,
    ROOT, NUM_FOLDS, TOP_K, SEED, RANKING_USERS_CAP,
)
from run_cold_item import (
    DATASET_KCORE, HP, make_item_kfold, reindex_warm_only, eval_cold_item_ranking,
)


def make_score_content_direct(X_warm, S_content, warm_indices, cold_arr):
    Xw = X_warm[:, warm_indices].astype(np.float32)
    S_wc = S_content[np.ix_(warm_indices, cold_arr)].astype(np.float32)
    score_mat = Xw @ S_wc
    return lambda u_ids, c_arr: score_mat[u_ids]


def make_score_lc2c(X_warm, B_warm, item_title_emb, warm_indices, cold_arr, latent_dim=64):
    """LC2C V1 (legacy ablation): SVD(B_warm) + Ridge(SBERT -> CF latent).

    The current OURS/HEADLINE method is V2 (make_score_lc2c_no_svd below),
    not this one. V1 is retained as an ablation that shows the cost of
    the rank-k truncation.
    """
    n_warm = len(warm_indices)
    B_sym = 0.5 * (B_warm + B_warm.T)
    k = min(latent_dim, n_warm - 1)
    svd = TruncatedSVD(n_components=k, random_state=SEED)
    E_cf_warm = svd.fit_transform(B_sym).astype(np.float32)
    emb = item_title_emb.cpu().numpy() if hasattr(item_title_emb, 'cpu') else np.asarray(item_title_emb)
    emb = emb.astype(np.float32)
    SBERT_warm = emb[warm_indices]; SBERT_cold = emb[cold_arr]
    reg = Ridge(alpha=1.0); reg.fit(SBERT_warm, E_cf_warm)
    E_cf_cold_pred = reg.predict(SBERT_cold).astype(np.float32)
    Xw = X_warm[:, warm_indices].astype(np.float32)
    UE = Xw @ E_cf_warm
    score_mat = UE @ E_cf_cold_pred.T
    return lambda u_ids, c_arr: score_mat[u_ids]


def make_score_lc2c_no_svd(X_warm, B_warm, item_title_emb, warm_indices, cold_arr):
    """Variant: no SVD; learn ridge from SBERT directly to B_warm rows.
    Predicts (n_warm)-dim vectors for cold items, score(u, j) = X[u, warm] @ B_pred[j].
    Equivalent to learning the full B-row regression - tests if SVD's denoising helps."""
    n_warm = len(warm_indices)
    emb = item_title_emb.cpu().numpy() if hasattr(item_title_emb, 'cpu') else np.asarray(item_title_emb)
    emb = emb.astype(np.float32)
    SBERT_warm = emb[warm_indices]; SBERT_cold = emb[cold_arr]
    # Predict each WARM item's column of B_warm (n_warm-dim) directly.
    # B_warm[k, j] for j in warm_indices: ridge from SBERT -> B_warm column
    # Shape: SBERT_warm (n_warm, 384) -> B_warm.T (n_warm, n_warm) using each row as target column
    # This directly regresses content -> behaviour vector
    reg = Ridge(alpha=1.0); reg.fit(SBERT_warm, B_warm.T)  # predicts (n_warm,) per item
    B_cold_pred_T = reg.predict(SBERT_cold).astype(np.float32)  # (n_cold, n_warm)
    Xw = X_warm[:, warm_indices].astype(np.float32)
    score_mat = Xw @ B_cold_pred_T.T  # (n_users, n_cold)
    return lambda u_ids, c_arr: score_mat[u_ids]


def make_score_lc2c_no_ridge(X_warm, B_warm, item_title_emb, warm_indices, cold_arr, latent_dim=64):
    """Variant: SVD + nearest-warm-in-SBERT (no learned mapping).
    For each cold item, find its nearest warm item by SBERT cosine, use that warm
    item's E_cf row. This tests if learning the SBERT->E_cf map matters vs. just
    using it as a similarity measure."""
    n_warm = len(warm_indices)
    B_sym = 0.5 * (B_warm + B_warm.T)
    k = min(latent_dim, n_warm - 1)
    svd = TruncatedSVD(n_components=k, random_state=SEED)
    E_cf_warm = svd.fit_transform(B_sym).astype(np.float32)
    emb = item_title_emb.cpu().numpy() if hasattr(item_title_emb, 'cpu') else np.asarray(item_title_emb)
    emb = emb.astype(np.float32)
    SBERT_warm = emb[warm_indices]
    # Normalize for cosine
    SBERT_warm_n = SBERT_warm / (np.linalg.norm(SBERT_warm, axis=1, keepdims=True) + 1e-12)
    SBERT_cold_n = emb[cold_arr] / (np.linalg.norm(emb[cold_arr], axis=1, keepdims=True) + 1e-12)
    # For each cold item, find top-1 nearest warm item
    sim_cw = SBERT_cold_n @ SBERT_warm_n.T  # (n_cold, n_warm)
    nearest = np.argmax(sim_cw, axis=1)  # (n_cold,) indices into warm_indices
    E_cf_cold_pred = E_cf_warm[nearest]
    Xw = X_warm[:, warm_indices].astype(np.float32)
    UE = Xw @ E_cf_warm
    score_mat = UE @ E_cf_cold_pred.T
    return lambda u_ids, c_arr: score_mat[u_ids]


def run_ablation(dataset, n_splits=5, latent_dims=(16, 64, 256)):
    K_CORE = DATASET_KCORE[dataset]
    LAM, BETA = HP[dataset]
    print(f'\n{"#"*70}\n#  LC2C ABLATION: {dataset.upper()} (k={K_CORE})\n{"#"*70}')
    cache_dir = os.path.join(ROOT, "cache", dataset)
    data = pickle.load(open(os.path.join(cache_dir, "raw_data_dedup.pkl"), 'rb'))
    filtered = kcore_filter(data['interactions'], K_CORE)
    interactions, item_meta, n_users, n_items, _ = reindex(filtered, data['item_metadata'])
    print(f'  {n_users:,} users / {n_items:,} items / {len(interactions):,} inters')

    title_path = os.path.join(cache_dir, "v5", f"item_title_k{K_CORE}_dedup.pt")
    item_title_emb = torch.load(title_path, weights_only=True)
    S_content = content_sim_matrix(item_title_emb, dtype=np.float32)

    splits = make_item_kfold(interactions, n_items, n_splits=n_splits)

    methods = {
        'V0_content_direct':       'baseline: no LC2C',
        'V1_lc2c_full_k64':        'ablation: SVD k=64 + Ridge (legacy LC2C variant)',
        'V2_lc2c_no_svd':          'ours/headline: no SVD (direct B-row regression)',
        'V3_lc2c_no_ridge_k64':    'ablation: no Ridge (nearest-warm in SBERT)',
    }
    for k in latent_dims:
        methods[f'V1_lc2c_full_k{k}'] = f'sensitivity: SVD k={k}'

    results = {m: [] for m in methods}

    for fi, (tr_idx, te_idx, cold_items) in enumerate(splits):
        train_inters = [interactions[i] for i in tr_idx]
        test_inters  = [interactions[i] for i in te_idx]
        warm_items   = sorted(set(range(n_items)) - cold_items)
        warm_indices = np.array(warm_items, dtype=np.int32)
        cold_arr     = np.array(sorted(cold_items), dtype=np.int32)

        X_warm = reindex_warm_only(train_inters, n_users, n_items, cold_items)
        X_warm_only = X_warm[:, warm_indices]
        X_sparse = csr_matrix(X_warm_only)
        S_warm = S_content[np.ix_(warm_indices, warm_indices)]
        B_warm = ease_fast(X_sparse, lam=LAM, beta=BETA, S_content=S_warm, dtype=np.float32)

        # Methods
        scoring_fns = {
            'V0_content_direct':    make_score_content_direct(X_warm, S_content, warm_indices, cold_arr),
            'V1_lc2c_full_k64':     make_score_lc2c(X_warm, B_warm, item_title_emb, warm_indices, cold_arr, latent_dim=64),
            'V2_lc2c_no_svd':       make_score_lc2c_no_svd(X_warm, B_warm, item_title_emb, warm_indices, cold_arr),
            'V3_lc2c_no_ridge_k64': make_score_lc2c_no_ridge(X_warm, B_warm, item_title_emb, warm_indices, cold_arr, latent_dim=64),
        }
        for k in latent_dims:
            if k == 64: continue  # already in V1_lc2c_full_k64
            scoring_fns[f'V1_lc2c_full_k{k}'] = make_score_lc2c(
                X_warm, B_warm, item_title_emb, warm_indices, cold_arr, latent_dim=k)

        for name, sf in scoring_fns.items():
            r = eval_cold_item_ranking(sf, train_inters, test_inters, n_items, cold_items)
            results[name].append(r)

        line = f'  fold {fi}: '
        for name in methods:
            if results[name]:
                line += f'{name[:18]:>18}={results[name][-1]["NDCG@10"]:.4f}  '
        print(line)
        del B_warm, X_warm, X_warm_only, S_warm; gc.collect()

    summary = {}
    print(f'\n  === {dataset.upper()} LC2C ablation 5-fold means ===')
    for name in methods:
        if not results[name]: continue
        ndcg = float(np.mean([r['NDCG@10'] for r in results[name]]))
        nstd = float(np.std([r['NDCG@10'] for r in results[name]]))
        hr = float(np.mean([r['HR@10'] for r in results[name]]))
        summary[name] = {'NDCG@10': ndcg, 'NDCG@10_std': nstd, 'HR@10': hr,
                          'description': methods[name]}
        print(f'    {name:<24}: NDCG@10={ndcg:.4f}+/-{nstd:.4f}  HR@10={hr:.4f}  ({methods[name]})')
    return summary


def main():
    if len(sys.argv) > 1:
        datasets = sys.argv[1:]
    else:
        datasets = ['beauty', 'fashion', 'instruments']  # skip books for speed

    all_results = {}
    for ds in datasets:
        all_results[ds] = run_ablation(ds)
        json.dump(all_results, open(os.path.join(os.path.dirname(__file__),
                  "results_ablation_lc2c.json"), "w"), indent=2,
                  default=lambda o: float(o) if hasattr(o, 'item') else str(o))

    print('\n' + '=' * 100)
    print('LC2C ABLATION SUMMARY: NDCG@10 — does each piece of LC2C help?')
    print('=' * 100)
    methods = ['V0_content_direct', 'V1_lc2c_full_k64', 'V2_lc2c_no_svd',
                'V3_lc2c_no_ridge_k64', 'V1_lc2c_full_k16', 'V1_lc2c_full_k256']
    print(f'\n{"Method":<28}', end='')
    for ds in datasets: print(f' {ds:>14}', end='')
    print()
    print('-' * (28 + 15 * len(datasets)))
    for m in methods:
        print(f'{m:<28}', end='')
        for ds in datasets:
            if m in all_results.get(ds, {}):
                v = all_results[ds][m]
                print(f' {v["NDCG@10"]:.4f}+/-{v.get("NDCG@10_std",0):.3f}'.rjust(15), end='')
            else:
                print(f' {"---":>14}', end='')
        print()


if __name__ == "__main__":
    main()
