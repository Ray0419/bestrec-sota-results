"""Publication-grade LightGCN baseline with multi-seed multi-config tuning.

Implements He et al. (SIGIR 2020) LightGCN under the SAME warm-LOO protocol
as run_warm_loo.py so the strict-confirmatory pipeline can validate the
warm-LOO claims against a properly tuned LightGCN baseline (not the legacy
single-seed round-3 numbers in results_lightgcn.json).

Implementation:
  - Symmetric-normalized user-item bipartite adjacency A_hat = D^{-1/2} A D^{-1/2}
    (A is the (n_users + n_items) x (n_users + n_items) bipartite matrix)
  - Light convolution: E^{l+1} = A_hat @ E^l, no transformation/no activation
  - Final user/item embedding = mean over layers (paper default)
  - score(u, i) = E_u . E_i
  - BPR loss with negative sampling + L2 weight decay on E^{0}

Protocol:
  - Same 5-fold warm-LOO splits via make_warm_kfold (same SEED as warm-LOO)
  - Inner validation: hold out 15% of fold's training interactions on a
    per-user basis (cap at 1 held-out interaction per user, ≥1 train left)
  - Early stop on inner-validation NDCG@10
  - Hyperparameter sweep done once per (dataset, seed=20260521); winning
    config is then re-run on the other seeds with full 5-fold + per-pair
    NDCG saved.

Usage:
  _bestrec_run/.venv/Scripts/python _bestrec_run/run_lightgcn_strict.py \
      beauty fashion instruments books \
      --seeds 20260521,20260522,20260523
"""
from __future__ import annotations

import argparse
import gc
import itertools
import json
import os
import pickle
import sys
import time
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import torch
import torch.nn as nn
from scipy.sparse import coo_matrix, csr_matrix

from v5_utils import (
    NUM_FOLDS, ROOT, SEED, TOP_K,
    kcore_filter, make_warm_kfold, reindex,
)
from run_cold_item import DATASET_KCORE


# -----------------------------------------------------------------------------
# Device + reproducibility
# -----------------------------------------------------------------------------
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')


def set_seed(seed: int) -> None:
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


# -----------------------------------------------------------------------------
# LightGCN model
# -----------------------------------------------------------------------------
def build_sym_adj(train_pairs: np.ndarray, n_users: int, n_items: int,
                  device: torch.device) -> torch.Tensor:
    """Build symmetric-normalized bipartite adjacency A_hat as a torch sparse tensor.

    A is (n_users + n_items) x (n_users + n_items), block off-diagonal user-item
    matrix R. A_hat = D^{-1/2} A D^{-1/2}.
    """
    n = n_users + n_items
    rows = np.concatenate([train_pairs[:, 0], train_pairs[:, 1] + n_users])
    cols = np.concatenate([train_pairs[:, 1] + n_users, train_pairs[:, 0]])
    data = np.ones(len(rows), dtype=np.float32)
    A = coo_matrix((data, (rows, cols)), shape=(n, n))

    # symmetric normalize
    deg = np.asarray(A.sum(axis=1)).flatten()
    deg_inv_sqrt = np.zeros_like(deg, dtype=np.float64)
    nz = deg > 0
    deg_inv_sqrt[nz] = np.power(deg[nz], -0.5)
    A = A.tocsr()
    D_inv_sqrt = csr_matrix((deg_inv_sqrt, (np.arange(n), np.arange(n))),
                            shape=(n, n))
    A_hat = D_inv_sqrt @ A @ D_inv_sqrt
    A_hat = A_hat.tocoo()

    idx = torch.from_numpy(
        np.vstack([A_hat.row, A_hat.col]).astype(np.int64))
    val = torch.from_numpy(A_hat.data.astype(np.float32))
    sp = torch.sparse_coo_tensor(idx, val, size=(n, n)).coalesce().to(device)
    return sp


class LightGCN(nn.Module):
    def __init__(self, n_users: int, n_items: int, emb_dim: int,
                 n_layers: int, A_hat_sparse: torch.Tensor):
        super().__init__()
        self.n_users = n_users
        self.n_items = n_items
        self.emb_dim = emb_dim
        self.n_layers = n_layers
        self.A_hat = A_hat_sparse  # already on device
        self.user_emb = nn.Embedding(n_users, emb_dim)
        self.item_emb = nn.Embedding(n_items, emb_dim)
        nn.init.normal_(self.user_emb.weight, std=0.1)
        nn.init.normal_(self.item_emb.weight, std=0.1)

    def propagate(self) -> Tuple[torch.Tensor, torch.Tensor]:
        E0 = torch.cat([self.user_emb.weight, self.item_emb.weight], dim=0)
        embs = [E0]
        E = E0
        for _ in range(self.n_layers):
            E = torch.sparse.mm(self.A_hat, E)
            embs.append(E)
        E_final = torch.stack(embs, dim=0).mean(dim=0)  # mean over layers
        u_final = E_final[:self.n_users]
        i_final = E_final[self.n_users:]
        return u_final, i_final

    def bpr_loss(self, users: torch.Tensor, pos_items: torch.Tensor,
                 neg_items: torch.Tensor, reg_lambda: float
                 ) -> Tuple[torch.Tensor, torch.Tensor]:
        u_e, i_e = self.propagate()
        u_v = u_e[users]
        p_v = i_e[pos_items]
        n_v = i_e[neg_items]
        pos_scores = (u_v * p_v).sum(dim=1)
        neg_scores = (u_v * n_v).sum(dim=1)
        loss_bpr = -torch.log(torch.sigmoid(pos_scores - neg_scores) + 1e-10).mean()
        # L2 on the embeddings actually used in this batch (paper convention)
        u_e0 = self.user_emb(users)
        p_e0 = self.item_emb(pos_items)
        n_e0 = self.item_emb(neg_items)
        reg = (u_e0.pow(2).sum() + p_e0.pow(2).sum() + n_e0.pow(2).sum()
               ) / (2.0 * users.shape[0])
        return loss_bpr + reg_lambda * reg, loss_bpr.detach()


# -----------------------------------------------------------------------------
# Train / eval helpers
# -----------------------------------------------------------------------------
def _make_inner_val(train_inters: List[dict], rng: np.random.RandomState,
                    val_frac: float = 0.15
                    ) -> Tuple[List[dict], List[dict]]:
    """Hold out at most 1 interaction per user (the last after shuffle) into
    inner validation, for users with >= 2 interactions. Cap total held-out at
    val_frac * len(train_inters)."""
    by_u = defaultdict(list)
    for idx, i in enumerate(train_inters):
        by_u[i['user_id']].append(idx)
    candidates = []
    for uid, idxs in by_u.items():
        if len(idxs) >= 2:
            rng.shuffle(idxs)
            candidates.append(idxs[0])
    rng.shuffle(candidates)
    n_target = int(val_frac * len(train_inters))
    val_idx = set(candidates[:n_target])
    val_inters = [train_inters[i] for i in val_idx]
    inner_train = [train_inters[i] for i in range(len(train_inters)) if i not in val_idx]
    return inner_train, val_inters


def _user_train_sets(train_inters: List[dict]) -> Dict[int, set]:
    """user_id -> set of training item_ids (for O(1) negative-sampling lookup)."""
    by_u = defaultdict(set)
    for i in train_inters:
        by_u[i['user_id']].add(i['item_id'])
    return dict(by_u)


def _sample_neg(user_train_set: Dict[int, set], users: np.ndarray,
                n_items: int, rng: np.random.RandomState) -> np.ndarray:
    """Rejection-sample 1 random negative per user (Python sets for O(1) lookup)."""
    neg = rng.randint(0, n_items, size=len(users))
    # resample any collisions (typically <5% of users; converges in 2-3 passes)
    for _ in range(4):
        bad_idx = [k for k in range(len(users)) if neg[k] in user_train_set[users[k]]]
        if not bad_idx:
            break
        neg[bad_idx] = rng.randint(0, n_items, size=len(bad_idx))
    return neg


def _train_epoch(model: LightGCN, optimizer: torch.optim.Optimizer,
                 train_pairs: np.ndarray, user_train_items: Dict[int, set],
                 n_items: int, batch_size: int, reg_lambda: float,
                 rng: np.random.RandomState) -> float:
    model.train()
    perm = rng.permutation(len(train_pairs))
    pairs = train_pairs[perm]
    total = 0.0
    nb = 0
    for s in range(0, len(pairs), batch_size):
        chunk = pairs[s:s + batch_size]
        u = chunk[:, 0]
        p = chunk[:, 1]
        n = _sample_neg(user_train_items, u, n_items, rng)
        u_t = torch.from_numpy(u.astype(np.int64)).to(DEVICE)
        p_t = torch.from_numpy(p.astype(np.int64)).to(DEVICE)
        n_t = torch.from_numpy(n.astype(np.int64)).to(DEVICE)
        loss, _ = model.bpr_loss(u_t, p_t, n_t, reg_lambda)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        total += float(loss.item())
        nb += 1
    return total / max(1, nb)


def _evaluate_warm_loo(model: LightGCN, train_inters: List[dict],
                        test_inters: List[dict], n_users: int, n_items: int,
                        top_k: int = TOP_K, batch_users: int = 256,
                        return_per_pair: bool = True,
                        eval_user_cap: int = 0,
                        eval_seed: int = SEED) -> dict:
    """Warm-LOO ranking against unseen items (matches run_warm_loo.warm_ranking_eval)."""
    user_train = defaultdict(set)
    for i in train_inters:
        user_train[i['user_id']].add(i['item_id'])
    user_test = defaultdict(list)
    for i in test_inters:
        user_test[i['user_id']].append(i['item_id'])

    users = [u for u in user_test if user_test[u] and user_train[u]]
    if eval_user_cap and len(users) > eval_user_cap:
        rng = np.random.RandomState(eval_seed)
        users = sorted(rng.choice(users, eval_user_cap, replace=False).tolist())
    if not users:
        return {'NDCG@10': 0.0, 'HR@10': 0.0, 'MRR': 0.0, 'n_eval': 0,
                'ndcg_per_pair': [], 'user_id_per_pair': [],
                'target_item_id_per_pair': [], 'hr_per_pair': [],
                'rr_per_pair': []}

    model.eval()
    with torch.no_grad():
        u_e, i_e = model.propagate()
    ndcg, hr, mrr, uids, targets = [], [], [], [], []
    for s in range(0, len(users), batch_users):
        u_batch = users[s:s + batch_users]
        u_idx = torch.tensor(u_batch, dtype=torch.long, device=DEVICE)
        with torch.no_grad():
            sc = (u_e[u_idx] @ i_e.T).cpu().numpy()  # (b, n_items)
        for k, uid in enumerate(u_batch):
            seen = user_train[uid]
            for pos in user_test[uid]:
                if pos < 0 or pos >= n_items:
                    continue
                sv = sc[k].copy()
                for s_item in seen:
                    sv[s_item] = -np.inf
                ps = sv[pos]
                pr = int((sv > ps).sum())
                ndcg.append(1.0 / np.log2(pr + 2) if pr < top_k else 0.0)
                hr.append(1.0 if pr < top_k else 0.0)
                mrr.append(1.0 / (pr + 1))
                uids.append(int(uid))
                targets.append(int(pos))
    out = {'NDCG@10': float(np.mean(ndcg)) if ndcg else 0.0,
           'HR@10':   float(np.mean(hr))   if hr   else 0.0,
           'MRR':     float(np.mean(mrr))  if mrr  else 0.0,
           'n_eval':  len(ndcg)}
    if return_per_pair:
        out['ndcg_per_pair'] = [float(x) for x in ndcg]
        out['hr_per_pair']   = [float(x) for x in hr]
        out['rr_per_pair']   = [float(x) for x in mrr]
        out['user_id_per_pair']        = uids
        out['target_item_id_per_pair'] = targets
    return out


def train_lightgcn(n_users: int, n_items: int, train_inters: List[dict],
                   val_inters: Optional[List[dict]],
                   config: dict, seed: int, max_epochs: int = 200,
                   patience: int = 10, batch_size: int = 4096,
                   verbose: bool = False,
                   eval_user_cap: int = 0) -> Tuple[LightGCN, dict]:
    """Train LightGCN with early stopping on inner-validation NDCG@10.

    If val_inters is None, train to fixed max_epochs and return final model.
    """
    set_seed(seed)
    train_pairs = np.array([[i['user_id'], i['item_id']] for i in train_inters],
                           dtype=np.int64)
    A_hat = build_sym_adj(train_pairs, n_users, n_items, DEVICE)
    user_train_items = _user_train_sets(train_inters)

    model = LightGCN(n_users, n_items, emb_dim=config['emb_dim'],
                     n_layers=config['n_layers'], A_hat_sparse=A_hat).to(DEVICE)
    optimizer = torch.optim.Adam(model.parameters(), lr=config['lr'])

    rng = np.random.RandomState(seed)
    best_ndcg = -1.0
    best_state = None
    best_epoch = -1
    history = []
    no_improve = 0
    eval_every = config.get('eval_every', 5)

    for epoch in range(1, max_epochs + 1):
        loss = _train_epoch(model, optimizer, train_pairs, user_train_items,
                            n_items, batch_size, config['reg_lambda'], rng)
        if val_inters is None:
            history.append({'epoch': epoch, 'loss': loss})
            if verbose:
                print(f'    epoch {epoch:3d}  loss={loss:.4f}')
            continue
        if epoch % eval_every == 0 or epoch == max_epochs:
            v = _evaluate_warm_loo(model, train_inters, val_inters,
                                    n_users, n_items, return_per_pair=False,
                                    eval_user_cap=eval_user_cap, eval_seed=seed)
            ndcg_v = v['NDCG@10']
            history.append({'epoch': epoch, 'loss': loss, 'val_ndcg10': ndcg_v})
            improved = ndcg_v > best_ndcg + 1e-6
            if improved:
                best_ndcg = ndcg_v
                best_state = {k: t.detach().clone() for k, t in model.state_dict().items()}
                best_epoch = epoch
                no_improve = 0
            else:
                no_improve += eval_every
            if verbose:
                marker = ' *' if improved else ''
                print(f'    epoch {epoch:3d}  loss={loss:.4f}  val_ndcg@10={ndcg_v:.4f}{marker}')
            if no_improve >= patience:
                if verbose:
                    print(f'    early stop at epoch {epoch} (best epoch {best_epoch}, ndcg {best_ndcg:.4f})')
                break

    if val_inters is not None and best_state is not None:
        model.load_state_dict(best_state)
    return model, {'history': history, 'best_epoch': best_epoch, 'best_val_ndcg': best_ndcg}


# -----------------------------------------------------------------------------
# Hyperparameter sweep on fold 0
# -----------------------------------------------------------------------------
def search_best_config(dataset: str, n_users: int, n_items: int,
                       train_inters: List[dict], val_inters: List[dict],
                       sweep_grid: List[dict], seed: int,
                       max_epochs: int, patience: int,
                       batch_size: int, eval_user_cap: int = 0
                       ) -> Tuple[dict, list]:
    """Return (best_config, sweep_records).

    Each config is trained with inner validation early stopping.
    """
    records = []
    best = None
    best_score = -1.0
    for ci, cfg in enumerate(sweep_grid):
        t0 = time.time()
        _, info = train_lightgcn(n_users, n_items, train_inters, val_inters,
                                 cfg, seed=seed, max_epochs=max_epochs,
                                 patience=patience, batch_size=batch_size,
                                 verbose=False, eval_user_cap=eval_user_cap)
        dt = time.time() - t0
        ndcg = info['best_val_ndcg']
        rec = {'config': cfg, 'val_ndcg10': float(ndcg),
               'best_epoch': info['best_epoch'], 'time_s': dt}
        records.append(rec)
        print(f'  cfg[{ci+1:02d}/{len(sweep_grid)}] {cfg} -> val NDCG@10={ndcg:.4f} '
              f'(best epoch {info["best_epoch"]}, {dt:.1f}s)')
        if ndcg > best_score:
            best_score = ndcg
            best = cfg
    print(f'  >> best config: {best}  (val NDCG@10={best_score:.4f})')
    return best, records


# -----------------------------------------------------------------------------
# Main per-dataset driver
# -----------------------------------------------------------------------------
def make_sweep_grid(dataset: str = '') -> List[dict]:
    """Default sweep: n_layers in {1,2,3,4} x emb_dim in {32,64,128} x lr in
    {1e-3,5e-3} x reg in {1e-4,1e-5} = 48 configs (paper-canonical grid).

    For Books we use a narrower curated grid because the per-config training
    cost is ~4 min on GPU and the full 48-grid would exceed the 2-hour budget.
    The narrower books grid still covers all 4 axes but at fewer points
    informed by the smaller datasets.
    """
    if dataset == 'books':
        # Curated 6-config grid (covers main axes; drops 1-layer + emb=32 + 5e-3
        # + reg=1e-5 which have all been weak on the smaller-dataset pilots).
        # Books per-config train is ~4 min on GPU; 6 configs * 40 epochs ~ 24 min sweep.
        grid = []
        for n_layers, emb_dim, lr, reg in itertools.product(
                [2, 3, 4], [64, 128], [1e-3], [1e-4]):
            grid.append({'n_layers': n_layers, 'emb_dim': emb_dim,
                         'lr': lr, 'reg_lambda': reg, 'eval_every': 5})
        return grid
    if dataset == 'instruments':
        # 24-config grid: drop the extreme combos that are usually weak.
        grid = []
        for n_layers, emb_dim, lr, reg in itertools.product(
                [2, 3, 4], [64, 128], [1e-3, 5e-3], [1e-4, 1e-5]):
            grid.append({'n_layers': n_layers, 'emb_dim': emb_dim,
                         'lr': lr, 'reg_lambda': reg, 'eval_every': 5})
        return grid
    # Default = full canonical 48-config grid (beauty, fashion)
    grid = []
    for n_layers, emb_dim, lr, reg in itertools.product(
            [1, 2, 3, 4], [32, 64, 128], [1e-3, 5e-3], [1e-4, 1e-5]):
        grid.append({'n_layers': n_layers, 'emb_dim': emb_dim,
                     'lr': lr, 'reg_lambda': reg, 'eval_every': 5})
    return grid


def run_dataset(dataset: str, seeds: List[int], out_root: str,
                max_epochs_search: int = 80, max_epochs_final: int = 200,
                patience_search: int = 10, patience_final: int = 15,
                batch_size: int = 4096) -> dict:
    K = DATASET_KCORE[dataset]
    print(f'\n{"#"*70}\n#  LIGHTGCN STRICT: {dataset.upper()} (k-core={K})\n{"#"*70}')
    cache_dir = os.path.join(ROOT, 'cache', dataset)
    data = pickle.load(open(os.path.join(cache_dir, 'raw_data_dedup.pkl'), 'rb'))
    filtered = kcore_filter(data['interactions'], K)
    interactions, _, n_users, n_items, _ = reindex(filtered, data['item_metadata'])
    print(f'  {n_users:,} users / {n_items:,} items / {len(interactions):,} interactions')

    sweep_seed = seeds[0]
    splits_for_sweep = make_warm_kfold(interactions, n_splits=NUM_FOLDS, seed=SEED)
    tr_idx, te_idx = splits_for_sweep[0]
    f0_train = [interactions[i] for i in tr_idx]
    f0_test  = [interactions[i] for i in te_idx]
    rng = np.random.RandomState(sweep_seed)
    inner_train, inner_val = _make_inner_val(f0_train, rng, val_frac=0.15)
    print(f'  hp sweep on fold-0 inner split: {len(inner_train)} train / {len(inner_val)} val')

    sweep_grid = make_sweep_grid(dataset)
    # For small datasets, full grid; for large datasets, use shorter sweep budget.
    sweep_epochs = max_epochs_search
    sweep_eval_cap = 0
    if dataset in ('books',):
        sweep_epochs = 40    # books is the largest -> shorter sweep
        sweep_eval_cap = 3000
    elif dataset in ('instruments',):
        sweep_epochs = 60
        sweep_eval_cap = 0    # instruments small enough

    best_cfg, sweep_recs = search_best_config(
        dataset, n_users, n_items, inner_train, inner_val,
        sweep_grid, seed=sweep_seed,
        max_epochs=sweep_epochs, patience=patience_search,
        batch_size=batch_size, eval_user_cap=sweep_eval_cap,
    )

    # final eval: best_cfg across all seeds and all folds
    per_seed_summary = {}
    perfold_records_all = []  # list of [dataset, fold_id, seed, method, uid, item, ndcg10, hr10, rr]
    for seed in seeds:
        print(f'\n  >>> dataset={dataset} seed={seed} final 5-fold eval')
        splits = make_warm_kfold(interactions, n_splits=NUM_FOLDS, seed=SEED)
        fold_results = []
        for fi, (tr_idx, te_idx) in enumerate(splits):
            tr = [interactions[i] for i in tr_idx]
            te = [interactions[i] for i in te_idx]
            # Inner split for early stopping in final fit
            rng2 = np.random.RandomState(seed + fi * 7919)
            it, iv = _make_inner_val(tr, rng2, val_frac=0.10)
            t0 = time.time()
            model, info = train_lightgcn(n_users, n_items, it, iv,
                                         best_cfg, seed=seed,
                                         max_epochs=max_epochs_final,
                                         patience=patience_final,
                                         batch_size=batch_size, verbose=False)
            r = _evaluate_warm_loo(model, tr, te, n_users, n_items,
                                    return_per_pair=True)
            dt = time.time() - t0
            fold_results.append(r)
            print(f'    fold {fi}: NDCG@10={r["NDCG@10"]:.4f}  HR@10={r["HR@10"]:.4f}  '
                  f'MRR={r["MRR"]:.4f}  n={r["n_eval"]} (best epoch {info["best_epoch"]}, {dt:.1f}s)')
            for u, it_id, val, h, rr in zip(
                    r['user_id_per_pair'], r['target_item_id_per_pair'],
                    r['ndcg_per_pair'], r['hr_per_pair'], r['rr_per_pair']):
                perfold_records_all.append(
                    [dataset, fi, seed, 'lightgcn_strict', u, it_id, val, h, rr])
            del model
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            gc.collect()
        n_mean = float(np.mean([r['NDCG@10'] for r in fold_results]))
        n_std  = float(np.std([r['NDCG@10'] for r in fold_results]))
        h_mean = float(np.mean([r['HR@10']   for r in fold_results]))
        m_mean = float(np.mean([r['MRR']     for r in fold_results]))
        per_seed_summary[seed] = {
            'NDCG@10': n_mean, 'NDCG@10_std': n_std,
            'HR@10':   h_mean, 'MRR': m_mean,
            'per_fold_ndcg': [r['NDCG@10'] for r in fold_results],
            'per_fold_n_eval': [r['n_eval'] for r in fold_results],
        }
        print(f'  seed {seed} 5-fold: NDCG@10={n_mean:.4f}+/-{n_std:.4f}  HR@10={h_mean:.4f}  MRR={m_mean:.4f}')

    # across-seed aggregate
    ndcgs = [v['NDCG@10'] for v in per_seed_summary.values()]
    hrs   = [v['HR@10']   for v in per_seed_summary.values()]
    mrrs  = [v['MRR']     for v in per_seed_summary.values()]
    agg = {
        'NDCG@10_mean_across_seeds': float(np.mean(ndcgs)),
        'NDCG@10_std_across_seeds':  float(np.std(ndcgs)),
        'HR@10_mean_across_seeds':   float(np.mean(hrs)),
        'MRR_mean_across_seeds':     float(np.mean(mrrs)),
        'seeds': seeds,
        'best_config': best_cfg,
        'per_seed': {str(k): v for k, v in per_seed_summary.items()},
        'n_users': n_users, 'n_items': n_items, 'n_interactions': len(interactions),
    }
    print(f'\n  ===== {dataset.upper()} across-seed: NDCG@10={agg["NDCG@10_mean_across_seeds"]:.4f}'
          f'+/-{agg["NDCG@10_std_across_seeds"]:.4f}  best_cfg={best_cfg} =====')

    # Save per-fold records
    perfold_path = os.path.join(out_root,
        f'results_lightgcn_strict_perfold_{dataset}.json')
    with open(perfold_path, 'w') as f:
        json.dump({'schema': '[dataset, fold_id, seed, method, user_id, target_item_id, ndcg10, hr10, rr]',
                    'records': perfold_records_all,
                    'best_config': best_cfg,
                    'seeds': seeds}, f)
    print(f'  wrote per-pair records -> {os.path.basename(perfold_path)} '
          f'({len(perfold_records_all)} rows)')

    # also save sweep audit
    agg['sweep_records'] = sweep_recs
    return agg


def main():
    ap = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('datasets', nargs='*',
                    default=['beauty', 'fashion', 'instruments', 'books'])
    ap.add_argument('--seeds', default='20260521,20260522,20260523',
                    help='Comma-separated seeds for final eval (sweep uses seeds[0]).')
    ap.add_argument('--max-epochs-search', type=int, default=80)
    ap.add_argument('--max-epochs-final',  type=int, default=200)
    ap.add_argument('--patience-search',   type=int, default=10)
    ap.add_argument('--patience-final',    type=int, default=15)
    ap.add_argument('--batch-size',        type=int, default=4096)
    args = ap.parse_args()

    seeds = [int(x.strip()) for x in str(args.seeds).split(',') if x.strip()]
    out_root = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(out_root, 'results_lightgcn_strict.json')

    all_results = {}
    if os.path.exists(out_path):
        try:
            all_results = json.load(open(out_path))
        except Exception:
            all_results = {}

    all_results.setdefault('_meta', {})
    all_results['_meta']['seeds'] = seeds
    all_results['_meta']['device'] = str(DEVICE)
    all_results['_meta']['note'] = (
        'Publication-grade LightGCN baseline: He et al. SIGIR 2020. '
        'Symmetric-normalized A_hat = D^{-1/2}(A+A^T)D^{-1/2} on the bipartite '
        'user-item graph. Final emb = mean over layers. BPR loss. Same warm-LOO '
        'splits as run_warm_loo.py. Hyperparameter sweep on fold 0 with inner '
        'validation (15% per-user held-out). Final fit uses 10% inner val for '
        'early stopping per fold/seed.')

    for ds in args.datasets:
        agg = run_dataset(ds, seeds, out_root,
                          max_epochs_search=args.max_epochs_search,
                          max_epochs_final=args.max_epochs_final,
                          patience_search=args.patience_search,
                          patience_final=args.patience_final,
                          batch_size=args.batch_size)
        all_results[ds] = agg
        with open(out_path, 'w') as f:
            json.dump(all_results, f, indent=2,
                      default=lambda o: float(o) if hasattr(o, 'item') else str(o))
        print(f'  updated {os.path.basename(out_path)}')

    # Final summary printout
    print('\n\n========= LIGHTGCN STRICT SUMMARY =========')
    for ds in args.datasets:
        v = all_results.get(ds, {})
        print(f'  {ds:>13s}: NDCG@10={v.get("NDCG@10_mean_across_seeds", 0):.4f}'
              f'+/-{v.get("NDCG@10_std_across_seeds", 0):.4f}  '
              f'best_cfg={v.get("best_config")}')


if __name__ == '__main__':
    main()
