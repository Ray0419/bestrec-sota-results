"""Publication-grade iALS baseline via block-coordinate descent (paper-faithful, OOM-free).

Implements Hu, Koren, Volinsky (ICDM 2008) "Collaborative Filtering for Implicit
Feedback Datasets" with the standard ALS coordinate-descent updates, but uses a
block-coordinate trick to avoid materializing the n_items x n_items Gram matrix
Y^T Y at every iteration:

    For each user u, the optimal user factor is
        U_u = (V^T C^u V + lambda I)^{-1} V^T C^u p_u
    where C^u = diag(c_{u,i}) and c_{u,i} = 1 + alpha * X_{u,i}.
    We split this as
        V^T C^u V = V^T V + V^T (C^u - I) V
                  = (V^T V)        # cached, k x k
                  + sum_{i in obs(u)} (c_{u,i} - 1) * V_i V_i^T   # tiny
        V^T C^u p_u = sum_{i in obs(u)} c_{u,i} * V_i

    So each per-user update only needs V_i for i in obs(u) (which is small
    because the data is sparse), plus the shared k x k Gram V^T V.  We never
    materialize the n_items x n_items dense Gram, so Books fits in memory.

Per-iteration cost: O((nnz(X) + (n_users + n_items)) * k^2 + k^3 * (n_users + n_items))
Memory: O((n_users + n_items) * k + k^2)  -- linear in users+items, NOT items^2.

Strict protocol (matches run_lightgcn_strict.py / run_warm_loo.py):
  - Same 5-fold warm-LOO splits via make_warm_kfold(SEED=42).
  - Inner validation: hold out 15% of fold's training interactions on a
    per-user basis (cap at 1 held-out interaction per user, >=1 train left).
  - Early stop on inner-validation NDCG@10.
  - Hyperparameter sweep on fold 0, seeds[0]. Sweep grid:
        k       in {32, 64, 128}
        alpha   in {10, 40}
        lambda  in {0.1, 1.0, 10.0}
  - Final 5-fold eval per seed (3 seeds: 20260521,20260522,20260523).

Usage:
  _bestrec_run/.venv/Scripts/python _bestrec_run/run_ials_strict.py \
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
from scipy.sparse import csr_matrix

from v5_utils import (
    NUM_FOLDS, ROOT, SEED, TOP_K,
    build_X_sparse, kcore_filter, make_warm_kfold, reindex,
)
from run_cold_item import DATASET_KCORE


# -----------------------------------------------------------------------------
# Reproducibility
# -----------------------------------------------------------------------------
def set_seed(seed: int) -> None:
    np.random.seed(seed)


# -----------------------------------------------------------------------------
# iALS via block-coordinate descent (OOM-free)
# -----------------------------------------------------------------------------
class IALS:
    """Hu-Koren-Volinsky iALS with per-user / per-item updates that avoid the
    n_items x n_items Gram matrix.

    Fit:
      - One pass over users updating U_u, then one pass over items updating V_i.
      - Cache the small k x k Grams (V^T V) and (U^T U) once per iteration.
      - Per-user/item linear solve is k x k (k <= 128) -> milliseconds.
    """

    def __init__(self, n_users: int, n_items: int, n_factors: int = 64,
                 alpha: float = 40.0, reg: float = 10.0,
                 seed: int = 0, dtype=np.float32):
        self.n_users = n_users
        self.n_items = n_items
        self.k = n_factors
        self.alpha = float(alpha)
        self.reg = float(reg)
        self.dtype = dtype
        rng = np.random.RandomState(seed)
        # Standard small-Gaussian init (matches implicit/Spark/etc.)
        scale = 1.0 / np.sqrt(self.k)
        self.U = rng.normal(0, scale, size=(n_users, self.k)).astype(dtype)
        self.V = rng.normal(0, scale, size=(n_items, self.k)).astype(dtype)

    @staticmethod
    def _als_block_update(F_other: np.ndarray, FtF: np.ndarray,
                          indptr: np.ndarray, indices: np.ndarray,
                          alpha: float, reg: float) -> np.ndarray:
        """Block-coordinate update for ONE side of factors.

        Updates X[u] = (F_other^T C^u F_other + reg I)^-1 F_other^T C^u p_u
        for each u, given that c_{u,i} = 1 + alpha * X_{u,i} (binary p_u).

          F_other     : (n_other, k) frozen factors (V if updating U, U if updating V)
          FtF         : (k, k)  precomputed F_other.T @ F_other  (cached for all u)
          indptr,
          indices     : CSR pointers for u -> observed items i (or i -> observed u)
          alpha, reg  : iALS hyperparameters

        Returns updated factor matrix (n_self, k) where n_self = len(indptr) - 1.
        """
        k = FtF.shape[0]
        n_self = indptr.shape[0] - 1
        out = np.zeros((n_self, k), dtype=F_other.dtype)
        reg_eye = (reg * np.eye(k, dtype=F_other.dtype))
        for u in range(n_self):
            s, e = indptr[u], indptr[u + 1]
            if s == e:
                # cold user (no observations) -> minimum-norm solution is 0
                continue
            obs = indices[s:e]
            Fi = F_other[obs]            # (n_obs, k)
            # rhs = F^T C^u p_u = sum_i c_{u,i} * V_i  (since p_u is binary)
            # Equivalent: rhs = (1 + alpha) * sum_i V_i (each observed i has c=1+alpha)
            rhs = (1.0 + alpha) * Fi.sum(axis=0)  # (k,)
            # A = F^T V + F^T (C^u - I) V = FtF + alpha * sum_i V_i V_i^T
            #   = FtF + alpha * Fi^T @ Fi
            A = FtF + alpha * (Fi.T @ Fi) + reg_eye
            # Solve A x = rhs  (k x k linear system; k is small, e.g. 64)
            try:
                out[u] = np.linalg.solve(A, rhs)
            except np.linalg.LinAlgError:
                out[u] = np.linalg.lstsq(A, rhs, rcond=None)[0]
        return out

    def fit_one_pass(self, X_csr: csr_matrix, X_csc: csr_matrix) -> None:
        """Run one ALS iteration: update U then V."""
        # update U with V frozen
        VtV = (self.V.T @ self.V).astype(self.dtype)
        self.U = self._als_block_update(
            self.V, VtV, X_csr.indptr.astype(np.int64),
            X_csr.indices.astype(np.int64), self.alpha, self.reg)
        # update V with U frozen
        UtU = (self.U.T @ self.U).astype(self.dtype)
        self.V = self._als_block_update(
            self.U, UtU, X_csc.indptr.astype(np.int64),
            X_csc.indices.astype(np.int64), self.alpha, self.reg)

    def score(self, user_ids: np.ndarray) -> np.ndarray:
        """Return (len(user_ids), n_items) score matrix = U[users] @ V.T."""
        return self.U[user_ids] @ self.V.T


# -----------------------------------------------------------------------------
# Train / eval helpers (mirrors run_lightgcn_strict.py patterns)
# -----------------------------------------------------------------------------
def _make_inner_val(train_inters: List[dict], rng: np.random.RandomState,
                    val_frac: float = 0.15
                    ) -> Tuple[List[dict], List[dict]]:
    """Hold out at most 1 interaction per user into inner validation."""
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


def _warm_loo_eval(model: IALS, train_inters: List[dict],
                   test_inters: List[dict], n_users: int, n_items: int,
                   top_k: int = TOP_K, batch_users: int = 256,
                   return_per_pair: bool = True,
                   eval_user_cap: int = 0,
                   eval_seed: int = SEED) -> dict:
    """Warm-LOO ranking (matches run_warm_loo.warm_ranking_eval semantics)."""
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

    ndcg, hr, mrr, uids, targets = [], [], [], [], []
    for s in range(0, len(users), batch_users):
        u_batch = users[s:s + batch_users]
        sc = model.score(np.array(u_batch, dtype=np.int64))
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


def train_ials(n_users: int, n_items: int, train_inters: List[dict],
               val_inters: Optional[List[dict]],
               config: dict, seed: int, max_iters: int = 30,
               patience: int = 4, verbose: bool = False,
               eval_user_cap: int = 0) -> Tuple[IALS, dict]:
    """Train iALS with optional early stopping on inner-validation NDCG@10."""
    set_seed(seed)
    X_csr = build_X_sparse(train_inters, n_users, n_items).tocsr()
    X_csc = X_csr.tocsc()  # for per-item updates

    model = IALS(n_users=n_users, n_items=n_items,
                 n_factors=config['k'], alpha=config['alpha'],
                 reg=config['reg'], seed=seed, dtype=np.float32)

    best_ndcg = -1.0
    best_factors: Optional[Tuple[np.ndarray, np.ndarray]] = None
    best_iter = -1
    history = []
    no_improve = 0
    eval_every = max(1, int(config.get('eval_every', 2)))

    for it in range(1, max_iters + 1):
        t0 = time.time()
        model.fit_one_pass(X_csr, X_csc)
        dt = time.time() - t0
        if val_inters is None:
            history.append({'iter': it, 'time_s': dt})
            if verbose:
                print(f'    iter {it:3d}  ({dt:.1f}s)')
            continue
        if it % eval_every == 0 or it == max_iters:
            v = _warm_loo_eval(model, train_inters, val_inters,
                                n_users, n_items, return_per_pair=False,
                                eval_user_cap=eval_user_cap, eval_seed=seed)
            ndcg_v = v['NDCG@10']
            history.append({'iter': it, 'val_ndcg10': ndcg_v, 'time_s': dt})
            improved = ndcg_v > best_ndcg + 1e-6
            if improved:
                best_ndcg = ndcg_v
                best_factors = (model.U.copy(), model.V.copy())
                best_iter = it
                no_improve = 0
            else:
                no_improve += eval_every
            if verbose:
                marker = ' *' if improved else ''
                print(f'    iter {it:3d}  val_ndcg@10={ndcg_v:.4f}  ({dt:.1f}s){marker}')
            if no_improve >= patience:
                if verbose:
                    print(f'    early stop at iter {it} (best iter {best_iter}, '
                          f'ndcg {best_ndcg:.4f})')
                break

    if val_inters is not None and best_factors is not None:
        model.U, model.V = best_factors
    return model, {'history': history, 'best_iter': best_iter,
                    'best_val_ndcg': best_ndcg}


# -----------------------------------------------------------------------------
# Hyperparameter sweep
# -----------------------------------------------------------------------------
def make_sweep_grid(dataset: str = '') -> List[dict]:
    """Default sweep: k in {32, 64, 128} x alpha in {10, 40} x reg in
    {0.1, 1.0, 10.0} = 18 configs.

    For Books we narrow to k in {64, 128} x alpha in {10, 40} x reg in
    {1.0, 10.0} = 8 configs because each ALS iteration is the most expensive
    of any dataset.
    """
    if dataset == 'books':
        grid = []
        for k, alpha, reg in itertools.product(
                [64, 128], [10.0, 40.0], [1.0, 10.0]):
            grid.append({'k': k, 'alpha': alpha, 'reg': reg, 'eval_every': 2})
        return grid
    grid = []
    for k, alpha, reg in itertools.product(
            [32, 64, 128], [10.0, 40.0], [0.1, 1.0, 10.0]):
        grid.append({'k': k, 'alpha': alpha, 'reg': reg, 'eval_every': 2})
    return grid


def search_best_config(dataset: str, n_users: int, n_items: int,
                       train_inters: List[dict], val_inters: List[dict],
                       sweep_grid: List[dict], seed: int,
                       max_iters: int, patience: int,
                       eval_user_cap: int = 0) -> Tuple[dict, list]:
    records = []
    best = None
    best_score = -1.0
    for ci, cfg in enumerate(sweep_grid):
        t0 = time.time()
        _, info = train_ials(n_users, n_items, train_inters, val_inters,
                             cfg, seed=seed, max_iters=max_iters,
                             patience=patience, verbose=False,
                             eval_user_cap=eval_user_cap)
        dt = time.time() - t0
        ndcg = info['best_val_ndcg']
        rec = {'config': cfg, 'val_ndcg10': float(ndcg),
               'best_iter': info['best_iter'], 'time_s': dt}
        records.append(rec)
        print(f'  cfg[{ci+1:02d}/{len(sweep_grid)}] {cfg} -> val NDCG@10={ndcg:.4f} '
              f'(best iter {info["best_iter"]}, {dt:.1f}s)')
        if ndcg > best_score:
            best_score = ndcg
            best = cfg
    print(f'  >> best config: {best}  (val NDCG@10={best_score:.4f})')
    return best, records


# -----------------------------------------------------------------------------
# Main per-dataset driver
# -----------------------------------------------------------------------------
def run_dataset(dataset: str, seeds: List[int], out_root: str,
                max_iters_search: int = 20, max_iters_final: int = 40,
                patience_search: int = 4, patience_final: int = 6) -> dict:
    K = DATASET_KCORE[dataset]
    print(f'\n{"#"*70}\n#  IALS STRICT: {dataset.upper()} (k-core={K})\n{"#"*70}')
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
    sweep_iters = max_iters_search
    sweep_eval_cap = 0
    if dataset == 'books':
        sweep_iters = 15
        sweep_eval_cap = 3000

    best_cfg, sweep_recs = search_best_config(
        dataset, n_users, n_items, inner_train, inner_val,
        sweep_grid, seed=sweep_seed,
        max_iters=sweep_iters, patience=patience_search,
        eval_user_cap=sweep_eval_cap,
    )

    # final 5-fold eval across all seeds with best_cfg
    per_seed_summary = {}
    perfold_records_all = []
    for seed in seeds:
        print(f'\n  >>> dataset={dataset} seed={seed} final 5-fold eval')
        splits = make_warm_kfold(interactions, n_splits=NUM_FOLDS, seed=SEED)
        fold_results = []
        for fi, (tr_idx, te_idx) in enumerate(splits):
            tr = [interactions[i] for i in tr_idx]
            te = [interactions[i] for i in te_idx]
            rng2 = np.random.RandomState(seed + fi * 7919)
            it_inter, iv_inter = _make_inner_val(tr, rng2, val_frac=0.10)
            t0 = time.time()
            model, info = train_ials(n_users, n_items, it_inter, iv_inter,
                                     best_cfg, seed=seed,
                                     max_iters=max_iters_final,
                                     patience=patience_final,
                                     verbose=False)
            r = _warm_loo_eval(model, tr, te, n_users, n_items,
                                return_per_pair=True)
            dt = time.time() - t0
            fold_results.append(r)
            print(f'    fold {fi}: NDCG@10={r["NDCG@10"]:.4f}  HR@10={r["HR@10"]:.4f}  '
                  f'MRR={r["MRR"]:.4f}  n={r["n_eval"]} (best iter {info["best_iter"]}, {dt:.1f}s)')
            for u, it_id, val, h, rr in zip(
                    r['user_id_per_pair'], r['target_item_id_per_pair'],
                    r['ndcg_per_pair'], r['hr_per_pair'], r['rr_per_pair']):
                perfold_records_all.append(
                    [dataset, fi, seed, 'ials_strict', u, it_id, val, h, rr])
            del model
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
        print(f'  seed {seed} 5-fold: NDCG@10={n_mean:.4f}+/-{n_std:.4f}  '
              f'HR@10={h_mean:.4f}  MRR={m_mean:.4f}')

    ndcgs = [v['NDCG@10'] for v in per_seed_summary.values()]
    hrs   = [v['HR@10']   for v in per_seed_summary.values()]
    mrrs  = [v['MRR']     for v in per_seed_summary.values()]
    agg = {
        'NDCG@10_mean_across_seeds': float(np.mean(ndcgs)),
        'NDCG@10_std_across_seeds':  float(np.std(ndcgs)),
        # alias used by some validation scripts
        'mean_NDCG@10_over_seeds':   float(np.mean(ndcgs)),
        'HR@10_mean_across_seeds':   float(np.mean(hrs)),
        'MRR_mean_across_seeds':     float(np.mean(mrrs)),
        'seeds': seeds,
        'best_config': best_cfg,
        'per_seed': {str(k): v for k, v in per_seed_summary.items()},
        'n_users': n_users, 'n_items': n_items, 'n_interactions': len(interactions),
    }
    print(f'\n  ===== {dataset.upper()} across-seed: '
          f'NDCG@10={agg["NDCG@10_mean_across_seeds"]:.4f}'
          f'+/-{agg["NDCG@10_std_across_seeds"]:.4f}  best_cfg={best_cfg} =====')

    perfold_path = os.path.join(out_root,
        f'results_ials_strict_perfold_{dataset}.json')
    with open(perfold_path, 'w') as f:
        json.dump({'schema': '[dataset, fold_id, seed, method, user_id, target_item_id, ndcg10, hr10, rr]',
                    'records': perfold_records_all,
                    'best_config': best_cfg,
                    'seeds': seeds}, f)
    print(f'  wrote per-pair records -> {os.path.basename(perfold_path)} '
          f'({len(perfold_records_all)} rows)')
    agg['sweep_records'] = sweep_recs
    return agg


def main():
    ap = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('datasets', nargs='*',
                    default=['beauty', 'fashion', 'instruments', 'books'])
    ap.add_argument('--seeds', default='20260521,20260522,20260523',
                    help='Comma-separated seeds for final eval (sweep uses seeds[0]).')
    ap.add_argument('--max-iters-search', type=int, default=20)
    ap.add_argument('--max-iters-final',  type=int, default=40)
    ap.add_argument('--patience-search',  type=int, default=4)
    ap.add_argument('--patience-final',   type=int, default=6)
    args = ap.parse_args()

    seeds = [int(x.strip()) for x in str(args.seeds).split(',') if x.strip()]
    out_root = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(out_root, 'results_ials_strict.json')

    all_results = {}
    if os.path.exists(out_path):
        try:
            all_results = json.load(open(out_path))
        except Exception:
            all_results = {}

    all_results.setdefault('_meta', {})
    all_results['_meta']['seeds'] = seeds
    all_results['_meta']['note'] = (
        'Publication-grade iALS baseline: Hu/Koren/Volinsky ICDM 2008. '
        'Block-coordinate ALS update that avoids materializing the n_items x '
        'n_items Gram matrix; per-user/per-item update is k x k linear solve '
        'where k <= 128. Memory is O((n_users + n_items) * k + k^2). Same '
        'warm-LOO splits as run_warm_loo.py. Hyperparameter sweep on fold 0 '
        'inner validation (15% per-user held-out, target NDCG@10). Final fit '
        'uses 10% inner val for early stopping per fold/seed.')

    for ds in args.datasets:
        agg = run_dataset(ds, seeds, out_root,
                          max_iters_search=args.max_iters_search,
                          max_iters_final=args.max_iters_final,
                          patience_search=args.patience_search,
                          patience_final=args.patience_final)
        all_results[ds] = agg
        with open(out_path, 'w') as f:
            json.dump(all_results, f, indent=2,
                      default=lambda o: float(o) if hasattr(o, 'item') else str(o))
        print(f'  updated {os.path.basename(out_path)}')

    print('\n\n========= IALS STRICT SUMMARY =========')
    for ds in args.datasets:
        v = all_results.get(ds, {})
        if 'NDCG@10_mean_across_seeds' in v:
            print(f'  {ds:>13s}: NDCG@10={v.get("NDCG@10_mean_across_seeds", 0):.4f}'
                  f'+/-{v.get("NDCG@10_std_across_seeds", 0):.4f}  '
                  f'best_cfg={v.get("best_config")}')


if __name__ == '__main__':
    main()
