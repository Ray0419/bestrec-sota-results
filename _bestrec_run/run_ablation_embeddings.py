"""Critical ablation: does SBERT specifically help, or would ANY embedding work?

Tests three content-prior variants:
  1. SBERT (ours):         actual SBERT title embeddings (our method)
  2. Random Gaussian:      same dim (384), random N(0,1) - control
  3. Bag-of-Words SVD:     TF-IDF + TruncatedSVD(384) - cheap text alternative
  4. No content:           pure EASE (beta=0)

If SBERT >> random and SBERT > BoW-SVD, then the SEMANTIC content matters.
"""
import os, sys, json, pickle, gc, time
sys.path.insert(0, os.path.dirname(__file__))
from collections import defaultdict
import numpy as np
import torch
from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD

from ease_efficient import ease_fast
from v5_utils import (
    kcore_filter, reindex, make_warm_kfold, build_X_sparse,
    content_sim_matrix, ROOT, NUM_FOLDS, TOP_K, SEED, RANKING_USERS_CAP,
)

DATASET_KCORE = {'beauty': 5, 'fashion': 4, 'instruments': 10, 'books': 20}
HP = {'beauty': (100, 10), 'fashion': (30, 10), 'instruments': (200, 10), 'books': (200, 10)}


def random_sim_matrix(n_items, dim=384, dtype=np.float32, seed=SEED):
    """Random Gaussian embeddings -> cosine similarity (zero diagonal)."""
    rng = np.random.RandomState(seed)
    emb = rng.normal(0, 1, (n_items, dim)).astype(dtype)
    norms = np.linalg.norm(emb, axis=1, keepdims=True) + 1e-12
    emb_n = emb / norms
    S = emb_n @ emb_n.T
    np.fill_diagonal(S, 0.0)
    return S


def bow_svd_sim_matrix(item_meta, n_items, dim=384, dtype=np.float32):
    """TF-IDF on titles + TruncatedSVD -> cosine sim. No semantic prior."""
    titles = [item_meta[i].get('title', '') or 'unknown' for i in range(n_items)]
    vec = TfidfVectorizer(max_features=10000, ngram_range=(1, 2))
    X_tfidf = vec.fit_transform(titles)
    if X_tfidf.shape[1] <= dim:
        emb = X_tfidf.toarray().astype(dtype)
        # Pad to dim
        if emb.shape[1] < dim:
            emb = np.hstack([emb, np.zeros((emb.shape[0], dim - emb.shape[1]), dtype=dtype)])
    else:
        svd = TruncatedSVD(n_components=dim, random_state=SEED)
        emb = svd.fit_transform(X_tfidf).astype(dtype)
    norms = np.linalg.norm(emb, axis=1, keepdims=True) + 1e-12
    emb_n = emb / norms
    S = emb_n @ emb_n.T
    np.fill_diagonal(S, 0.0)
    return S


def per_user_ndcg_simple(score_fn, train_inters, test_inters, n_items, top_k=TOP_K, max_users=RANKING_USERS_CAP):
    user_train = defaultdict(set)
    for i in train_inters: user_train[i['user_id']].add(i['item_id'])
    user_test = defaultdict(set)
    for i in test_inters: user_test[i['user_id']].add(i['item_id'])
    users = [u for u in user_test if user_test[u]]
    if len(users) > max_users:
        rng = np.random.RandomState(SEED)
        users = sorted(rng.choice(users, max_users, replace=False).tolist())
    ndcg, hr, mrr = [], [], []
    BATCH = 512
    for s in range(0, len(users), BATCH):
        ub = users[s:s + BATCH]
        scores = score_fn(np.array(ub, dtype=np.int32))
        for k, uid in enumerate(ub):
            seen = user_train[uid]; tp = user_test[uid]
            for pos in tp:
                sv = scores[k].copy()
                for j in seen: sv[j] = -np.inf
                for j in tp:
                    if j != pos: sv[j] = -np.inf
                pr = int((sv > sv[pos]).sum())
                hr.append(1.0 if pr < top_k else 0.0)
                ndcg.append(1.0 / np.log2(pr + 2) if pr < top_k else 0.0)
                mrr.append(1.0 / (pr + 1))
    return {f'NDCG@{top_k}': float(np.mean(ndcg)), f'HR@{top_k}': float(np.mean(hr)),
            'MRR': float(np.mean(mrr))}


def run_ablation(dataset):
    K_CORE = DATASET_KCORE[dataset]
    LAM, BETA = HP[dataset]
    print(f'\n{"#"*70}\n#  EMBEDDING ABLATION: {dataset.upper()} (k={K_CORE})\n{"#"*70}')
    cache_dir = os.path.join(ROOT, "cache", dataset)
    data = pickle.load(open(os.path.join(cache_dir, "raw_data_dedup.pkl"), 'rb'))
    filtered = kcore_filter(data['interactions'], K_CORE)
    interactions, item_meta, n_users, n_items, _ = reindex(filtered, data['item_metadata'])
    print(f'  {n_users:,} users / {n_items:,} items / {len(interactions):,} inters')

    title_path = os.path.join(cache_dir, "v5", f"item_title_k{K_CORE}_dedup.pt")
    item_title_emb = torch.load(title_path, weights_only=True)

    print('  Building 4 content priors...')
    S_sbert  = content_sim_matrix(item_title_emb, dtype=np.float32)
    S_random = random_sim_matrix(n_items, dim=384)
    S_bow    = bow_svd_sim_matrix(item_meta, n_items, dim=384)
    print(f'    SBERT:  {S_sbert.shape}, sample sim values: {S_sbert[0, 1:5]}')
    print(f'    Random: {S_random.shape}, sample sim values: {S_random[0, 1:5]}')
    print(f'    BoW:    {S_bow.shape}, sample sim values: {S_bow[0, 1:5]}')

    warm_splits = make_warm_kfold(interactions)

    methods = ['no_content (beta=0)', 'random_emb', 'bow_svd', 'sbert (ours)']
    results = {m: [] for m in methods}

    for fi, (tr, te) in enumerate(warm_splits):
        tr_i = [interactions[i] for i in tr]; te_i = [interactions[i] for i in te]
        X = build_X_sparse(tr_i, n_users, n_items)

        # No content
        B = ease_fast(X, lam=LAM, dtype=np.float32)
        fn = lambda uids, B=B: (X[uids] @ B).astype(np.float32)
        results['no_content (beta=0)'].append(per_user_ndcg_simple(fn, tr_i, te_i, n_items))
        del B; gc.collect()

        # Random embeddings
        B = ease_fast(X, lam=LAM, beta=BETA, S_content=S_random, dtype=np.float32)
        fn = lambda uids, B=B: (X[uids] @ B).astype(np.float32)
        results['random_emb'].append(per_user_ndcg_simple(fn, tr_i, te_i, n_items))
        del B; gc.collect()

        # BoW SVD
        B = ease_fast(X, lam=LAM, beta=BETA, S_content=S_bow, dtype=np.float32)
        fn = lambda uids, B=B: (X[uids] @ B).astype(np.float32)
        results['bow_svd'].append(per_user_ndcg_simple(fn, tr_i, te_i, n_items))
        del B; gc.collect()

        # SBERT (ours)
        B = ease_fast(X, lam=LAM, beta=BETA, S_content=S_sbert, dtype=np.float32)
        fn = lambda uids, B=B: (X[uids] @ B).astype(np.float32)
        results['sbert (ours)'].append(per_user_ndcg_simple(fn, tr_i, te_i, n_items))
        del B; gc.collect()

        line = f'  fold {fi}: '
        for m in methods:
            line += f'{m[:14]:<14}={results[m][-1]["NDCG@10"]:.4f}  '
        print(line)

    print(f'\n  === {dataset.upper()} ablation 5-fold means ===')
    summary = {}
    for m in methods:
        ndcg = float(np.mean([r['NDCG@10'] for r in results[m]]))
        nstd = float(np.std([r['NDCG@10'] for r in results[m]]))
        hr   = float(np.mean([r['HR@10']   for r in results[m]]))
        summary[m] = {'NDCG@10': ndcg, 'NDCG@10_std': nstd, 'HR@10': hr}
        print(f'    {m:>22s}: NDCG@10={ndcg:.4f}±{nstd:.4f}  HR@10={hr:.4f}')

    return summary


def main():
    if len(sys.argv) > 1:
        datasets = sys.argv[1:]
    else:
        datasets = ['beauty', 'fashion', 'instruments', 'books']
    all_results = {}
    for ds in datasets:
        all_results[ds] = run_ablation(ds)
        json.dump(all_results, open(os.path.join(os.path.dirname(__file__),
                  "results_ablation_embeddings.json"), "w"), indent=2,
                  default=lambda o: float(o) if hasattr(o, 'item') else str(o))

    print('\n' + '=' * 90)
    print('ABLATION SUMMARY: NDCG@10 — does SBERT specifically help?')
    print('=' * 90)
    methods = ['no_content (beta=0)', 'random_emb', 'bow_svd', 'sbert (ours)']
    print(f'\n{"Method":<22}', end='')
    for ds in datasets: print(f' {ds:>14}', end='')
    print()
    print('-' * (22 + 15 * len(datasets)))
    for m in methods:
        print(f'{m:<22}', end='')
        for ds in datasets:
            if m in all_results.get(ds, {}):
                v = all_results[ds][m]
                print(f' {v["NDCG@10"]:.4f}±{v["NDCG@10_std"]:.3f}'.rjust(15), end='')
            else:
                print(f' {"---":>14}', end='')
        print()


if __name__ == "__main__":
    main()
