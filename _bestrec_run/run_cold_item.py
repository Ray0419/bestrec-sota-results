"""COLD-ITEM evaluation — addresses reviewer's #1 concern about true held-out entities.

Protocol (item-GroupKFold):
  - Partition items into 5 folds; one fold per round is "cold" (held-out)
  - Train EASE on remaining 80% of items + their interactions
  - Test set = (user, cold_item, rating) — items NOT seen in training
  - For each user with ≥1 test cold item, rank ALL cold items by score(u, cold_j)
  - Cold item j has no training interactions → must score by content prior

NOVEL ALGORITHM: Content-Imputed EASE (CI-EASE)
  Standard EASE: score(u, j) = X[u, :] @ B[:, j]
  For cold j, B[:, j] is undefined. We propose imputing it via content:

      B[k, j_cold] ≈ Σ_{j' ∈ warm} S_content[j_cold, j'] · B[k, j'] / Σ S_content[j_cold, :]

  Equivalently:  score(u, j_cold) = (X[u, :] @ B_warm) @ S_content[warm, j_cold]
                                  = (predicted user-score over warm items) ⨉ (content sim to cold)

Methods compared:
  1. Random                                (control)
  2. Content-direct                        score = X[u, :] @ S[:, j_cold]  (1-hop content)
  3. Imputed-Popularity                    score = avg pop of warm items similar to j_cold
  4. CI-EASE (ours)                        score = (X[u, :] @ B_warm) @ S[warm, j_cold]
  5. Hybrid (Content + CI-EASE)            score = α · Content + (1-α) · CI-EASE
"""
import os, sys, json, pickle, gc
sys.path.insert(0, os.path.dirname(__file__))
from collections import defaultdict
import numpy as np
import torch
from scipy.sparse import csr_matrix

from ease_efficient import ease_fast
from v5_utils import (
    kcore_filter, reindex, build_X_sparse,
    content_sim_matrix, ROOT, NUM_FOLDS, TOP_K, SEED, RANKING_USERS_CAP,
)

DATASET_KCORE = {'beauty': 5, 'fashion': 4, 'instruments': 10, 'books': 20}
HP = {'beauty': (100, 10), 'fashion': (30, 10), 'instruments': (200, 10), 'books': (200, 10)}


def make_item_kfold(interactions, n_items, n_splits=5, seed=SEED):
    """Hold out a 1/n_splits fraction of ITEMS in each fold.
    Returns list of (train_idx, test_idx, cold_item_set) per fold."""
    rng = np.random.RandomState(seed)
    item_perm = rng.permutation(n_items)
    fold_items = np.array_split(item_perm, n_splits)
    splits = []
    for f in range(n_splits):
        cold_items = set(int(x) for x in fold_items[f])
        train_idx, test_idx = [], []
        for idx, inter in enumerate(interactions):
            if inter['item_id'] in cold_items:
                test_idx.append(idx)
            else:
                train_idx.append(idx)
        splits.append((np.array(train_idx), np.array(test_idx), cold_items))
    return splits


def reindex_warm_only(interactions, n_users, n_items, cold_items):
    """Build X_warm: n_users x n_items, with cold-item columns ZEROED.
    Items keep their original indices (so SBERT lookups remain valid)."""
    X = np.zeros((n_users, n_items), dtype=np.float32)
    for i in interactions:
        if i['item_id'] not in cold_items:
            X[i['user_id'], i['item_id']] = 1.0
    return X


def eval_cold_item_ranking(score_fn, train_inters, test_inters, n_items,
                            cold_items, top_k=TOP_K, max_users=RANKING_USERS_CAP):
    """Cold-item ranking: for each (user, cold_item) test pair, rank that
    cold item against all OTHER cold items the user hasn't seen.

    score_fn(user_ids, cold_item_ids) -> (n_users, n_cold_items) score array.
    """
    cold_arr = np.array(sorted(cold_items), dtype=np.int32)

    # Build user_train_items (warm items in user's history)
    user_train_warm = defaultdict(set)
    for i in train_inters:
        user_train_warm[i['user_id']].add(i['item_id'])

    # User's COLD test items
    user_test_cold = defaultdict(set)
    for i in test_inters:
        user_test_cold[i['user_id']].add(i['item_id'])

    # Eligible users: have ≥1 test cold item AND ≥1 warm training item
    users = [u for u in user_test_cold
             if user_test_cold[u] and user_train_warm[u]]
    if len(users) > max_users:
        rng = np.random.RandomState(SEED)
        users = sorted(rng.choice(users, max_users, replace=False).tolist())

    if not users:
        return {f'NDCG@{top_k}': 0.0, f'HR@{top_k}': 0.0, 'MRR': 0.0, 'n_eval': 0}

    # Score in batches; record (user_id, item_id, NDCG) for each test pair so
    # downstream significance tests can aggregate properly (per-user mean
    # rather than the previously pseudo-replicated per-pair pooling).
    ndcg, hr, mrr = [], [], []
    user_ids_out, item_ids_out = [], []
    BATCH = 256
    for s in range(0, len(users), BATCH):
        u_batch = users[s:s + BATCH]
        # scores: (batch, len(cold_arr))
        scores = score_fn(np.array(u_batch, dtype=np.int32), cold_arr)
        # Map cold_item_id -> position in cold_arr
        cold_to_idx = {int(c): i for i, c in enumerate(cold_arr)}
        for k, uid in enumerate(u_batch):
            test_pos = user_test_cold[uid]
            for pos in test_pos:
                if pos not in cold_to_idx:
                    continue
                pos_idx = cold_to_idx[pos]
                sv = scores[k].copy()
                # Mask other test cold items (so we rank against unseen cold items + the target)
                for other in test_pos:
                    if other != pos and other in cold_to_idx:
                        sv[cold_to_idx[other]] = -np.inf
                ps = sv[pos_idx]
                pr = int((sv > ps).sum())  # 0-indexed rank
                hr.append(1.0 if pr < top_k else 0.0)
                ndcg.append(1.0 / np.log2(pr + 2) if pr < top_k else 0.0)
                mrr.append(1.0 / (pr + 1))
                user_ids_out.append(int(uid))
                item_ids_out.append(int(pos))
    return {f'NDCG@{top_k}': float(np.mean(ndcg)) if ndcg else 0.0,
            f'HR@{top_k}': float(np.mean(hr)) if hr else 0.0,
            'MRR': float(np.mean(mrr)) if mrr else 0.0,
            'n_eval': len(hr),
            # AUDITABLE per-test-pair record for cold-item significance tests.
            # We store user_id and item_id alongside the NDCG value so a reviewer
            # can independently aggregate by user, by fold, by item, or do a
            # clustered bootstrap, rather than (mistakenly) treating per-pair
            # observations as independent samples.
            'ndcg_per_pair': [float(x) for x in ndcg],
            'user_id_per_pair': user_ids_out,
            'item_id_per_pair': item_ids_out}


# ============================================================
# Cold-item methods
# ============================================================

def make_score_random(n_items_cold, seed=SEED):
    rng = np.random.RandomState(seed)
    def fn(user_ids, cold_arr):
        return rng.uniform(0, 1, size=(len(user_ids), len(cold_arr))).astype(np.float32)
    return fn


def make_score_imputed_popularity(X_warm, S_content, cold_arr, warm_indices):
    """Cold item j's "popularity" = weighted avg of warm items' popularity
    by content similarity to cold j."""
    pop_warm = X_warm[:, warm_indices].sum(axis=0)  # (n_warm,)
    # S_content[warm, cold] is (n_warm, n_cold)
    S_wc = S_content[np.ix_(warm_indices, cold_arr)]  # (n_warm, n_cold)
    norm = S_wc.sum(axis=0) + 1e-12
    pop_cold_imputed = (pop_warm @ S_wc) / norm
    pop_cold_imputed = pop_cold_imputed / (pop_cold_imputed.sum() + 1e-12)
    def fn(user_ids, cold_arr):
        return np.tile(pop_cold_imputed, (len(user_ids), 1)).astype(np.float32)
    return fn


def make_score_content_direct(X_warm, S_content, cold_arr, warm_indices):
    """Direct content scoring: score(u, cold_j) = X[u, warm] @ S_content[warm, cold_j]."""
    S_wc = S_content[np.ix_(warm_indices, cold_arr)].astype(np.float32)  # (n_warm, n_cold)
    Xw = X_warm[:, warm_indices].astype(np.float32)  # (n_users, n_warm)
    def fn(user_ids, cold_arr):
        return Xw[user_ids] @ S_wc
    return fn


def make_score_ci_ease(X_warm, B_warm, S_content, cold_arr, warm_indices):
    """Content-Imputed EASE (CI-EASE):
       score(u, cold_j) = (X[u, warm] @ B_warm) @ S_content[warm, cold_j]"""
    S_wc = S_content[np.ix_(warm_indices, cold_arr)].astype(np.float32)
    Xw = X_warm[:, warm_indices].astype(np.float32)
    # Pre-compute X @ B_warm for warm users (fixed during eval)
    XB = Xw @ B_warm  # (n_users, n_warm)
    score_full = XB @ S_wc  # (n_users, n_cold)
    def fn(user_ids, cold_arr):
        return score_full[user_ids]
    return fn


def make_score_hybrid(X_warm, B_warm, S_content, cold_arr, warm_indices, alpha=0.5):
    """Hybrid: alpha * content + (1-alpha) * CI-EASE."""
    S_wc = S_content[np.ix_(warm_indices, cold_arr)].astype(np.float32)
    Xw = X_warm[:, warm_indices].astype(np.float32)
    content_full = Xw @ S_wc
    XB = Xw @ B_warm
    ci_full = XB @ S_wc
    # rank-normalize each per row to combine
    from scipy.stats import rankdata
    content_ranks = np.apply_along_axis(rankdata, 1, content_full).astype(np.float32)
    ci_ranks      = np.apply_along_axis(rankdata, 1, ci_full).astype(np.float32)
    combined = alpha * content_ranks + (1 - alpha) * ci_ranks
    def fn(user_ids, cold_arr):
        return combined[user_ids]
    return fn


# ============================================================
# Per-dataset runner
# ============================================================

def run_cold_item(dataset, n_splits=5):
    K_CORE = DATASET_KCORE[dataset]
    LAM, BETA = HP[dataset]
    print(f'\n{"#"*70}\n#  COLD-ITEM EVALUATION: {dataset.upper()} (k={K_CORE})\n{"#"*70}')
    cache_dir = os.path.join(ROOT, "cache", dataset)
    data = pickle.load(open(os.path.join(cache_dir, "raw_data_dedup.pkl"), 'rb'))
    filtered = kcore_filter(data['interactions'], K_CORE)
    interactions, item_meta, n_users, n_items, _ = reindex(filtered, data['item_metadata'])
    print(f'  {n_users:,} users / {n_items:,} items / {len(interactions):,} inters')

    title_path = os.path.join(cache_dir, "v5", f"item_title_k{K_CORE}_dedup.pt")
    item_title_emb = torch.load(title_path, weights_only=True)
    S_content = content_sim_matrix(item_title_emb, dtype=np.float32)
    # Add diagonal back so cold-vs-self has high sim (we'll only use off-block anyway)
    print(f'  Item content sim matrix: {S_content.shape} ({S_content.nbytes/1e9:.2f} GB)')

    splits = make_item_kfold(interactions, n_items, n_splits=n_splits)
    methods = ['random', 'imputed_pop', 'content_direct', 'ci_ease', 'hybrid_50_50']
    results = {m: [] for m in methods}

    for fi, (tr_idx, te_idx, cold_items) in enumerate(splits):
        train_inters = [interactions[i] for i in tr_idx]
        test_inters  = [interactions[i] for i in te_idx]
        warm_items   = sorted(set(range(n_items)) - cold_items)
        warm_indices = np.array(warm_items, dtype=np.int32)
        cold_arr     = np.array(sorted(cold_items), dtype=np.int32)
        print(f'  fold {fi}: |warm items|={len(warm_items):,}  |cold items|={len(cold_items):,}  '
              f'|train inters|={len(train_inters):,}  |test inters|={len(test_inters):,}')

        # Build warm-only X (full size, cold cols zero)
        X_warm = reindex_warm_only(train_inters, n_users, n_items, cold_items)

        # Train EASE on warm sub-block (n_warm × n_warm)
        X_warm_only = X_warm[:, warm_indices]  # (n_users, n_warm)
        # Need a sparse matrix
        X_sparse = csr_matrix(X_warm_only)
        # Trim S_content to warm × warm for EASE training
        S_warm = S_content[np.ix_(warm_indices, warm_indices)]
        B_warm = ease_fast(X_sparse, lam=LAM, beta=BETA, S_content=S_warm, dtype=np.float32)
        print(f'    EASE_warm: {B_warm.shape}')

        # Score functions
        sf_random = make_score_random(len(cold_arr))
        sf_imp_pop = make_score_imputed_popularity(X_warm, S_content, cold_arr, warm_indices)
        sf_content = make_score_content_direct(X_warm, S_content, cold_arr, warm_indices)
        sf_ci_ease = make_score_ci_ease(X_warm, B_warm, S_content, cold_arr, warm_indices)
        sf_hybrid  = make_score_hybrid(X_warm, B_warm, S_content, cold_arr, warm_indices, alpha=0.5)

        # Evaluate
        for name, sf in zip(methods, [sf_random, sf_imp_pop, sf_content, sf_ci_ease, sf_hybrid]):
            r = eval_cold_item_ranking(sf, train_inters, test_inters, n_items, cold_items)
            results[name].append(r)

        print(f'    fold {fi} NDCG@10: ' +
              ' '.join(f'{m[:8]}={results[m][-1]["NDCG@10"]:.4f}' for m in methods))
        del B_warm, X_warm, X_warm_only, S_warm
        gc.collect()

    # Aggregate
    summary = {}
    print(f'\n  === {dataset.upper()} cold-ITEM 5-fold means ===')
    for m in methods:
        if not results[m]: continue
        ndcg = float(np.mean([r['NDCG@10'] for r in results[m]]))
        nstd = float(np.std([r['NDCG@10'] for r in results[m]]))
        hr = float(np.mean([r['HR@10']   for r in results[m]]))
        mrr = float(np.mean([r['MRR']    for r in results[m]]))
        n_eval = int(np.mean([r['n_eval'] for r in results[m]]))
        summary[m] = {'NDCG@10': ndcg, 'NDCG@10_std': nstd, 'HR@10': hr, 'MRR': mrr,
                       'n_eval_per_fold': n_eval}
        print(f'    {m:>16s}: NDCG@10={ndcg:.4f}±{nstd:.4f}  HR@10={hr:.4f}  MRR={mrr:.4f}  '
              f'(n_eval/fold={n_eval})')
    return summary


def main():
    import argparse
    ap = argparse.ArgumentParser(
        description="Run BEST-Rec v4 LEGACY cold-item evaluation (random, imputed_pop, "
                    "content_direct, ci_ease, hybrid_50_50). Writes results_cold_item.json. "
                    "NOTE: this is NOT the script that populates Table 5.4 of the paper. "
                    "Table 5.4 uses run_cold_item_v2.py, which adds the headline LC2C V2 "
                    "method, the DropoutNet baseline, and saves per-(user, cold-pair) NDCG "
                    "vectors for paired-Wilcoxon downstream. The warm leave-one-out (Tables "
                    "5.1, 5.2) and cold-user few-shot (Table 5.3) experiments live in the "
                    "BEST_Rec_v4.ipynb notebook, NOT in any standalone script. See "
                    "RUNNING.md §3 for the full reproduction path.")
    ap.add_argument("datasets", nargs='*', default=['beauty', 'fashion', 'instruments', 'books'],
                    help="Datasets to run on (default: all four)")
    args = ap.parse_args()

    datasets = args.datasets

    # default: cold-item
    all_results = {}
    for ds in datasets:
        all_results[ds] = run_cold_item(ds)
        json.dump(all_results, open(os.path.join(os.path.dirname(__file__),
                  "results_cold_item.json"), "w"), indent=2,
                  default=lambda o: float(o) if hasattr(o, 'item') else str(o))

    print('\n' + '=' * 90)
    print('COLD-ITEM SUMMARY: NDCG@10 — predicting unseen items via content')
    print('=' * 90)
    methods = ['random', 'imputed_pop', 'content_direct', 'ci_ease', 'hybrid_50_50']
    print(f'\n{"Method":<22}', end='')
    for ds in datasets: print(f' {ds:>15}', end='')
    print()
    print('-' * (22 + 16 * len(datasets)))
    for m in methods:
        print(f'{m:<22}', end='')
        for ds in datasets:
            if m in all_results.get(ds, {}):
                v = all_results[ds][m]
                print(f' {v["NDCG@10"]:.4f}±{v.get("NDCG@10_std", 0):.3f}'.rjust(16), end='')
            else:
                print(f' {"---":>15}', end='')
        print()


if __name__ == "__main__":
    main()
