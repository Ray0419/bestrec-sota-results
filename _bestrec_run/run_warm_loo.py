"""Standalone warm-LOO evaluation for BEST-Rec v4 + closed-form baselines.

Addresses round-4 review F1 + F2 + F5:
  F1 the notebook was the reproduction path, was stale, and was deferred
  F2 the Books NDCG@10 had been manually reconciled rather than re-run
  F5 warm-LOO per-user NDCG vectors were not saved -> Wilcoxon not auditable

This script reproduces the warm leave-one-out evaluation that produces the
NDCG@10 numbers in Tables 5.1 and 5.2 of the paper for these methods:

    - Popularity            (trivial baseline)
    - EASE-pure             (lambda tuned, beta=0)
    - Higher-Order EASE     (B + 0.3 * B^2)
    - EASE+SBERT (ours)     (lambda tuned, beta=10, S_content from SBERT)

It does NOT include the deep baselines (MultiVAE, iALS, LightGCN) -- those
remain in the legacy notebook because they require their own training loops
that we do not reimplement in this round. The deep-baseline NDCG values in
results_FINAL.json continue to be the canonical source for Table 5.2 rows
that reference them; the per-user Wilcoxon comparisons that DO have audit-
grade vectors here are the closed-form ones (Popularity, EASE-pure,
Higher-Order EASE) and the relative comparison between EASE+SBERT and these.

Outputs:
    results_warm_loo.json                  per-method 5-fold means + std
    results_warm_loo_perfold_<dataset>.json   per-(fold, user, ndcg) records
    [Books only] results_FINAL.json's       updated EASE+SBERT warm_mean
                                            with the single-pipeline value

Usage:
    cd _bestrec_run
    uv run python run_warm_loo.py beauty fashion instruments books
    uv run python run_warm_loo.py books    # single-dataset rerun (merges JSON)
"""
import argparse
import gc
import json
import os
import pickle
import sys

sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import torch
from scipy.sparse import csr_matrix

from ease_efficient import ease_fast
from v5_utils import (
    ROOT, SEED, NUM_FOLDS, TOP_K, build_X_sparse, content_sim_matrix,
    kcore_filter, make_warm_kfold, reindex,
)
from run_cold_item import DATASET_KCORE, HP


def warm_ranking_eval(score_fn, train_inters, test_inters, n_users, n_items,
                       top_k: int = TOP_K, max_users: int = 0,
                       seed: int = SEED):
    """Warm leave-one-out ranking against all unseen items.

    For each test (user, held-out item) pair, rank the held-out item against
    every item the user has NOT seen in training. Returns per-pair NDCG with
    user_id metadata so the downstream paired Wilcoxon test can aggregate
    per-user.
    """
    from collections import defaultdict
    user_train = defaultdict(set)
    for i in train_inters:
        user_train[i['user_id']].add(i['item_id'])
    user_test = defaultdict(list)
    for i in test_inters:
        user_test[i['user_id']].append(i['item_id'])

    users = [u for u in user_test if user_test[u] and user_train[u]]
    if max_users and len(users) > max_users:
        rng = np.random.RandomState(seed)
        users = sorted(rng.choice(users, max_users, replace=False).tolist())
    if not users:
        return {'NDCG@10': 0.0, 'HR@10': 0.0, 'MRR': 0.0, 'n_eval': 0,
                'ndcg_per_pair': [], 'user_id_per_pair': [],
                'target_item_id_per_pair': [], 'hr_per_pair': [],
                'rr_per_pair': []}

    BATCH = 256
    ndcg, hr, mrr, uids, target_items = [], [], [], [], []
    all_items = np.arange(n_items, dtype=np.int32)
    for s in range(0, len(users), BATCH):
        u_batch = users[s:s + BATCH]
        scores = score_fn(np.array(u_batch, dtype=np.int32), all_items)
        for k, uid in enumerate(u_batch):
            seen = user_train[uid]
            for pos in user_test[uid]:
                if pos < 0 or pos >= n_items:
                    continue
                sv = scores[k].copy()
                # mask seen items
                for s_item in seen:
                    sv[s_item] = -np.inf
                ps = sv[pos]
                pr = int((sv > ps).sum())
                ndcg.append(1.0 / np.log2(pr + 2) if pr < top_k else 0.0)
                hr.append(1.0 if pr < top_k else 0.0)
                mrr.append(1.0 / (pr + 1))
                uids.append(int(uid))
                target_items.append(int(pos))
    return {'NDCG@10': float(np.mean(ndcg)) if ndcg else 0.0,
            'HR@10':   float(np.mean(hr))   if hr   else 0.0,
            'MRR':     float(np.mean(mrr))  if mrr  else 0.0,
            'n_eval':  len(ndcg),
            'ndcg_per_pair':    [float(x) for x in ndcg],
            'hr_per_pair':      [float(x) for x in hr],
            'rr_per_pair':      [float(x) for x in mrr],
            'user_id_per_pair': uids,
            'target_item_id_per_pair': target_items}


def _score_popularity(train_inters, n_items):
    cnt = np.zeros(n_items, dtype=np.float32)
    for i in train_inters:
        cnt[i['item_id']] += 1
    def fn(user_ids, all_items):
        return np.tile(cnt, (len(user_ids), 1))
    return fn


def _score_ease(X_sparse, lam, beta, S_content):
    B = ease_fast(X_sparse, lam=lam, beta=beta, S_content=S_content,
                  dtype=np.float32)
    # score(u) = X[u] @ B
    Xd = X_sparse.toarray().astype(np.float32)
    score_mat = Xd @ B
    def fn(user_ids, all_items):
        return score_mat[user_ids]
    return fn, B


def _score_higher_order_ease(X_sparse, lam, beta, S_content, alpha: float = 0.3):
    """Higher-Order EASE: B + alpha * B^2, where B is computed with the SBERT
    content prior (matching the paper's implementation in the notebook;
    Steck 2020's higher-order term is composed on the SBERT-augmented EASE B,
    not the pure EASE B, so the warm-LOO numbers match Table 5.2)."""
    B = ease_fast(X_sparse, lam=lam, beta=beta, S_content=S_content,
                  dtype=np.float32)
    B_ho = B + alpha * (B @ B)
    np.fill_diagonal(B_ho, 0.0)
    Xd = X_sparse.toarray().astype(np.float32)
    score_mat = Xd @ B_ho
    def fn(user_ids, all_items):
        return score_mat[user_ids]
    return fn


def run_warm_loo(dataset: str, max_users: int = 0, seed: int = SEED):
    K = DATASET_KCORE[dataset]
    LAM, BETA = HP[dataset]
    print(f'\n{"#"*70}\n#  WARM-LOO: {dataset.upper()} (k={K})\n{"#"*70}')
    cache_dir = os.path.join(ROOT, "cache", dataset)
    data = pickle.load(open(os.path.join(cache_dir, "raw_data_dedup.pkl"), 'rb'))
    filtered = kcore_filter(data['interactions'], K)
    interactions, item_meta, n_users, n_items, _ = reindex(filtered, data['item_metadata'])
    print(f'  {n_users:,} users / {n_items:,} items / {len(interactions):,} inters')

    title_path = os.path.join(cache_dir, "v5", f"item_title_k{K}_dedup.pt")
    item_title_emb = torch.load(title_path, weights_only=True)
    S_content = content_sim_matrix(item_title_emb, dtype=np.float32)

    splits = make_warm_kfold(interactions, n_splits=NUM_FOLDS, seed=seed)
    methods = ['popularity', 'ease_pure', 'higher_order_ease', 'ease_sbert']
    results = {m: [] for m in methods}

    for fi, (tr_idx, te_idx) in enumerate(splits):
        train_inters = [interactions[i] for i in tr_idx]
        test_inters  = [interactions[i] for i in te_idx]
        X_sparse = build_X_sparse(train_inters, n_users, n_items)

        # popularity
        sf = _score_popularity(train_inters, n_items)
        results['popularity'].append(
            warm_ranking_eval(sf, train_inters, test_inters, n_users, n_items,
                              max_users=max_users, seed=seed))

        # EASE-pure (lambda only, beta = 0)
        sf, _ = _score_ease(X_sparse, lam=LAM, beta=0.0, S_content=None)
        results['ease_pure'].append(
            warm_ranking_eval(sf, train_inters, test_inters, n_users, n_items,
                              max_users=max_users, seed=seed))

        # Higher-Order EASE: B + 0.3*B^2 on the SBERT-augmented EASE B
        sf = _score_higher_order_ease(X_sparse, lam=LAM, beta=BETA,
                                       S_content=S_content, alpha=0.3)
        results['higher_order_ease'].append(
            warm_ranking_eval(sf, train_inters, test_inters, n_users, n_items,
                              max_users=max_users, seed=seed))

        # EASE+SBERT (ours)
        sf, _ = _score_ease(X_sparse, lam=LAM, beta=BETA, S_content=S_content)
        results['ease_sbert'].append(
            warm_ranking_eval(sf, train_inters, test_inters, n_users, n_items,
                              max_users=max_users, seed=seed))

        print(f'  fold {fi}: ' +
              '  '.join(f'{m[:6]}={results[m][-1]["NDCG@10"]:.4f}'
                         for m in methods))
        del X_sparse; gc.collect()

    summary = {}
    print(f'\n  === {dataset.upper()} warm-LOO 5-fold means (single-pipeline) ===')
    for m in methods:
        ndcg = float(np.mean([r['NDCG@10'] for r in results[m]]))
        nstd = float(np.std([r['NDCG@10'] for r in results[m]]))
        hr   = float(np.mean([r['HR@10']  for r in results[m]]))
        mrr  = float(np.mean([r['MRR']    for r in results[m]]))
        summary[m] = {'NDCG@10': ndcg, 'NDCG@10_std': nstd,
                       'HR@10': hr, 'MRR': mrr,
                       'n_pairs_per_fold': [r['n_eval'] for r in results[m]],
                       'seed': seed,
                       'max_users_cap': max_users or None}
        print(f'    {m:>20s}: NDCG@10={ndcg:.4f}±{nstd:.4f}  HR@10={hr:.4f}  MRR={mrr:.4f}')

    # Save per-(fold, user, NDCG) records for downstream paired Wilcoxon
    perfold_records = {}
    for m in methods:
        records = []
        for fi, fold_res in enumerate(results[m]):
            for u, item, val, h, rr in zip(
                    fold_res['user_id_per_pair'],
                    fold_res['target_item_id_per_pair'],
                    fold_res['ndcg_per_pair'],
                    fold_res['hr_per_pair'],
                    fold_res['rr_per_pair']):
                records.append([dataset, fi, seed, m, u, item, val, h, rr])
        perfold_records[m] = records

    perfold_path = os.path.join(
        os.path.dirname(__file__),
        f"results_warm_loo_perfold_{dataset}.json")
    with open(perfold_path, 'w') as f:
        json.dump({'schema': '[dataset, fold_id, seed, method, user_id, target_item_id, ndcg10, hr10, rr]',
                    'methods': perfold_records}, f)
    print(f'  saved per-(fold, user, ndcg) records to '
          f'{os.path.basename(perfold_path)}')
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('datasets', nargs='*',
                     default=['beauty', 'fashion', 'instruments', 'books'])
    ap.add_argument('--max-users', type=int, default=0,
                    help='Optional per-fold user cap; 0 means full warm-user evaluation.')
    ap.add_argument('--seeds', default=str(SEED),
                    help='Comma-separated seeds. Current script writes one canonical summary per dataset using the first seed.')
    args = ap.parse_args()

    out_path = os.path.join(os.path.dirname(__file__), "results_warm_loo.json")
    all_results = {}
    if os.path.exists(out_path):
        try:
            all_results = json.load(open(out_path))
        except Exception:
            all_results = {}

    seed = int(str(args.seeds).split(',')[0])
    if ',' in str(args.seeds):
        print('WARNING: run_warm_loo currently emits one canonical summary per dataset; '
              f'using first seed only ({seed}) and leaving multi-seed deep audit to run_all/SOTA scripts.')

    for ds in args.datasets:
        all_results[ds] = run_warm_loo(ds, max_users=args.max_users, seed=seed)
        with open(out_path, 'w') as f:
            json.dump(all_results, f, indent=2,
                       default=lambda o: float(o) if hasattr(o, 'item') else str(o))
        print(f'  updated {os.path.basename(out_path)}')

    print('\n=== SUMMARY ===')
    print(f'{"Method":<20}', end='')
    for ds in args.datasets:
        print(f' {ds:>14}', end='')
    print()
    print('-' * (20 + 15 * len(args.datasets)))
    for m in ['popularity', 'ease_pure', 'higher_order_ease', 'ease_sbert']:
        print(f'{m:<20}', end='')
        for ds in args.datasets:
            v = all_results.get(ds, {}).get(m, {})
            ndcg = v.get('NDCG@10')
            std  = v.get('NDCG@10_std', 0.0)
            if ndcg is None:
                print(f' {"---":>14}', end='')
            else:
                print(f' {ndcg:.4f}±{std:.3f}'.rjust(15), end='')
        print()


if __name__ == "__main__":
    main()
