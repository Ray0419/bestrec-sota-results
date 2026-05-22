"""Shared utilities for v5 experiments (extracted from former run_v5_dedup.py)."""
import os
from collections import defaultdict
import numpy as np
from scipy.sparse import csr_matrix

ROOT = "C:/Users/rayxc/Documents/R"
NUM_FOLDS = 5
TOP_K = 10
SEED = 42
RANKING_USERS_CAP = 5000


def kcore_filter(interactions, k):
    inters = list(interactions); prev = -1
    while len(inters) != prev:
        prev = len(inters)
        uc = defaultdict(int); ic = defaultdict(int)
        for i in inters: uc[i['user_id']] += 1; ic[i['item_id']] += 1
        inters = [i for i in inters if uc[i['user_id']] >= k and ic[i['item_id']] >= k]
    return inters


def reindex(interactions, item_meta_orig):
    users = sorted(set(i['user_id'] for i in interactions))
    items = sorted(set(i['item_id'] for i in interactions))
    u2n = {o: n for n, o in enumerate(users)}
    i2n = {o: n for n, o in enumerate(items)}
    new_inters = [{'user_id': u2n[i['user_id']], 'item_id': i2n[i['item_id']],
                   'rating': i['rating'], 'review': i['review']} for i in interactions]
    new_meta = {n: item_meta_orig.get(o, {'title':'unknown','price':0.0,
                                          'avg_rating':0.0,'rating_num':0})
                for n, o in enumerate(items)}
    return new_inters, new_meta, len(users), len(items), {o: n for n, o in enumerate(items)}


def make_warm_kfold(interactions, n_splits=NUM_FOLDS, seed=SEED):
    rng = np.random.RandomState(seed)
    user_inters = defaultdict(list)
    for idx, inter in enumerate(interactions):
        user_inters[inter['user_id']].append(idx)
    always_train = []; foldable = defaultdict(list)
    for uid, indices in user_inters.items():
        if len(indices) == 1: always_train.extend(indices)
        else:
            rng.shuffle(indices)
            foldable[uid] = indices
    fold_test = [[] for _ in range(n_splits)]
    for uid, indices in foldable.items():
        for f in range(n_splits):
            if f < len(indices):
                fold_test[f].append(indices[f])
    splits = []
    for f in range(n_splits):
        te = np.array(fold_test[f]); te_set = set(fold_test[f])
        tr = list(always_train)
        for uid, indices in foldable.items():
            for idx in indices:
                if idx not in te_set: tr.append(idx)
        splits.append((np.array(tr), te))
    return splits


def build_X_sparse(train_inters, n_users, n_items):
    rows = np.array([i['user_id'] for i in train_inters], dtype=np.int32)
    cols = np.array([i['item_id'] for i in train_inters], dtype=np.int32)
    vals = np.ones(len(train_inters), dtype=np.float32)
    return csr_matrix((vals, (rows, cols)), shape=(n_users, n_items))


def content_sim_matrix(item_title_emb, dtype=np.float32):
    emb = item_title_emb.cpu().numpy() if hasattr(item_title_emb, 'cpu') else np.asarray(item_title_emb)
    emb = emb.astype(dtype)
    norms = np.linalg.norm(emb, axis=1, keepdims=True) + 1e-12
    emb_n = emb / norms
    S = emb_n @ emb_n.T
    np.fill_diagonal(S, 0.0)
    return S
