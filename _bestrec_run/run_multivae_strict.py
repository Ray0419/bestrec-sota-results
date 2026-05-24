"""Publication-grade MultiVAE (Liang et al., WWW 2018) baseline.

Implements *Variational Autoencoder for Collaborative Filtering* under the
SAME warm-LOO protocol used by run_warm_loo.py / run_lightgcn_strict.py so
the strict-confirmatory pipeline can validate the warm-LOO claims against a
properly tuned MultiVAE baseline (not the legacy single-seed round-3
numbers in results_FINAL.json).

Architecture (paper standard):
  Encoder x -> [600] -> [200 mu, 200 logsigma]
  Decoder z -> [600] -> [n_items] (softmax)
  Tanh activation, dropout 0.5 applied to the L2-normalized encoder input.

Loss = multinomial log-likelihood + beta * KL(q(z|x) || N(0, I))
       (beta is linearly annealed from 0 -> beta_anneal_cap over the first
        total_anneal_steps training iterations, then capped.)

Protocol:
  * Same 5-fold warm-LOO splits as run_warm_loo.py (make_warm_kfold with SEED=42)
  * Hyperparameter sweep on fold-0 inner split (10% of training interactions
    held out per user, capped at 1 per user) for seed[0], single dataset
  * Final eval: chosen config x 3 seeds x 5 folds, per-pair NDCG saved
    for downstream paired Wilcoxon vs EASE+SBERT

Usage:
  _bestrec_run/.venv/Scripts/python _bestrec_run/run_multivae_strict.py \\
      beauty fashion instruments books \\
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
import torch.nn.functional as F
from scipy.sparse import csr_matrix

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
# MultiVAE model (Liang et al., WWW 2018)
# -----------------------------------------------------------------------------
class MultiVAE(nn.Module):
    """Standard MultiVAE: encoder x -> [enc_hidden] -> [2 * latent_dim] (mu, logvar),
    decoder z -> [dec_hidden] -> [n_items] (logits).

    Default hidden width 600, latent dim 200, dropout 0.5, tanh activation.
    Following the original implementation
    (https://github.com/dawenl/vae_cf), we tie:
      - Encoder L2-normalizes input then applies dropout BEFORE the first linear.
      - Encoder applies tanh between hidden layers.
      - Decoder applies tanh between hidden layers (logits are raw, softmax in loss).
    """

    def __init__(self, n_items: int, latent_dim: int = 200,
                 enc_hidden: int = 600, dec_hidden: int = 600,
                 dropout: float = 0.5):
        super().__init__()
        self.n_items = n_items
        self.latent_dim = latent_dim
        self.dropout = dropout

        # Encoder: n_items -> enc_hidden -> 2 * latent_dim
        self.enc_fc1 = nn.Linear(n_items, enc_hidden)
        self.enc_fc2 = nn.Linear(enc_hidden, 2 * latent_dim)

        # Decoder: latent_dim -> dec_hidden -> n_items
        self.dec_fc1 = nn.Linear(latent_dim, dec_hidden)
        self.dec_fc2 = nn.Linear(dec_hidden, n_items)

        self._init_weights()

    def _init_weights(self):
        for m in [self.enc_fc1, self.enc_fc2, self.dec_fc1, self.dec_fc2]:
            nn.init.xavier_uniform_(m.weight)
            nn.init.normal_(m.bias, std=1e-3)

    def encode(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        # L2-normalize each user vector (paper convention)
        x = F.normalize(x, p=2, dim=1)
        x = F.dropout(x, p=self.dropout, training=self.training)
        h = torch.tanh(self.enc_fc1(x))
        h = self.enc_fc2(h)
        mu = h[:, :self.latent_dim]
        logvar = h[:, self.latent_dim:]
        return mu, logvar

    def reparameterize(self, mu: torch.Tensor, logvar: torch.Tensor) -> torch.Tensor:
        if self.training:
            std = torch.exp(0.5 * logvar)
            eps = torch.randn_like(std)
            return mu + eps * std
        return mu

    def decode(self, z: torch.Tensor) -> torch.Tensor:
        h = torch.tanh(self.dec_fc1(z))
        return self.dec_fc2(h)  # raw logits (softmax applied in loss)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        mu, logvar = self.encode(x)
        z = self.reparameterize(mu, logvar)
        logits = self.decode(z)
        return logits, mu, logvar


def multivae_loss(logits: torch.Tensor, x: torch.Tensor,
                  mu: torch.Tensor, logvar: torch.Tensor,
                  beta: float) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Multinomial log-likelihood + beta * KL(q||N(0,I)).

    Per-user loss is then averaged over the batch.
    """
    # Multinomial NLL: -sum_i x_i * log_softmax(logits)_i
    log_probs = F.log_softmax(logits, dim=1)
    nll = -(x * log_probs).sum(dim=1).mean()
    # KL divergence per row
    kl = -0.5 * (1.0 + logvar - mu.pow(2) - logvar.exp()).sum(dim=1).mean()
    return nll + beta * kl, nll.detach(), kl.detach()


# -----------------------------------------------------------------------------
# Data helpers
# -----------------------------------------------------------------------------
def _user_csr(train_inters: List[dict], n_users: int, n_items: int) -> csr_matrix:
    rows = np.array([i['user_id'] for i in train_inters], dtype=np.int32)
    cols = np.array([i['item_id'] for i in train_inters], dtype=np.int32)
    vals = np.ones(len(train_inters), dtype=np.float32)
    return csr_matrix((vals, (rows, cols)), shape=(n_users, n_items))


def _make_inner_val(train_inters: List[dict], rng: np.random.RandomState,
                    val_frac: float = 0.10
                    ) -> Tuple[List[dict], List[dict]]:
    """Hold out ~val_frac of train interactions; cap 1 per user; only users
    with >= 2 interactions are eligible."""
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


# -----------------------------------------------------------------------------
# Train / eval
# -----------------------------------------------------------------------------
def _evaluate_warm_loo(model: MultiVAE, X_train: csr_matrix,
                       train_inters: List[dict], test_inters: List[dict],
                       n_users: int, n_items: int, top_k: int = TOP_K,
                       batch_users: int = 256, return_per_pair: bool = True,
                       eval_user_cap: int = 0, eval_seed: int = SEED) -> dict:
    """Warm-LOO ranking against unseen items (matches run_warm_loo.warm_ranking_eval).

    For each held-out (user, item) pair, score is decoder logits[user, item]
    given the user's training row as encoder input. Items the user trained on
    are masked to -inf before ranking.
    """
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
    ndcg, hr, mrr, uids, targets = [], [], [], [], []
    with torch.no_grad():
        for s in range(0, len(users), batch_users):
            u_batch = users[s:s + batch_users]
            x_dense = np.asarray(X_train[u_batch].todense(), dtype=np.float32)
            x_t = torch.from_numpy(x_dense).to(DEVICE)
            logits, _, _ = model(x_t)
            sc = logits.cpu().numpy()
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


def train_multivae(n_users: int, n_items: int, train_inters: List[dict],
                   val_inters: Optional[List[dict]],
                   config: dict, seed: int, max_epochs: int = 200,
                   patience: int = 10, batch_size: int = 256,
                   verbose: bool = False,
                   eval_user_cap: int = 0,
                   ) -> Tuple[MultiVAE, csr_matrix, dict]:
    """Train MultiVAE with early stopping on inner-validation NDCG@10.

    Returns (model, training_user_csr_used_for_eval_input, info_dict)."""
    set_seed(seed)
    X_train = _user_csr(train_inters, n_users, n_items)

    model = MultiVAE(n_items=n_items,
                     latent_dim=config['latent_dim'],
                     enc_hidden=config.get('enc_hidden', 600),
                     dec_hidden=config.get('dec_hidden', 600),
                     dropout=config.get('dropout', 0.5)).to(DEVICE)
    optimizer = torch.optim.Adam(model.parameters(),
                                  lr=config.get('lr', 1e-3),
                                  weight_decay=config.get('weight_decay', 0.0))

    # Build training matrix indexing: we train on users that have ≥1 interaction
    # in the inner train split. Skip cold users.
    user_has_train = np.asarray(X_train.sum(axis=1)).flatten() > 0
    eligible_users = np.where(user_has_train)[0]

    rng = np.random.RandomState(seed)
    best_ndcg = -1.0
    best_state = None
    best_epoch = -1
    history = []
    no_improve = 0
    eval_every = config.get('eval_every', 5)
    beta_cap = config['beta_anneal_cap']
    total_anneal = max(1, int(config['total_anneal_steps']))
    iter_count = 0

    for epoch in range(1, max_epochs + 1):
        model.train()
        perm = rng.permutation(eligible_users)
        losses = []
        nlls = []
        kls = []
        for s in range(0, len(perm), batch_size):
            u_batch = perm[s:s + batch_size]
            x_dense = np.asarray(X_train[u_batch].todense(), dtype=np.float32)
            x_t = torch.from_numpy(x_dense).to(DEVICE)
            logits, mu, logvar = model(x_t)
            beta = min(beta_cap, beta_cap * (iter_count / total_anneal))
            loss, nll_d, kl_d = multivae_loss(logits, x_t, mu, logvar, beta)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            losses.append(float(loss.item()))
            nlls.append(float(nll_d.item()))
            kls.append(float(kl_d.item()))
            iter_count += 1
        avg_loss = float(np.mean(losses)) if losses else 0.0
        avg_nll  = float(np.mean(nlls))   if nlls   else 0.0
        avg_kl   = float(np.mean(kls))    if kls    else 0.0

        if val_inters is None:
            history.append({'epoch': epoch, 'loss': avg_loss,
                            'nll': avg_nll, 'kl': avg_kl, 'beta': beta})
            if verbose:
                print(f'    epoch {epoch:3d}  loss={avg_loss:.4f} '
                      f'nll={avg_nll:.4f} kl={avg_kl:.4f} beta={beta:.3f}')
            continue
        if epoch % eval_every == 0 or epoch == max_epochs:
            v = _evaluate_warm_loo(model, X_train, train_inters, val_inters,
                                    n_users, n_items, return_per_pair=False,
                                    eval_user_cap=eval_user_cap, eval_seed=seed)
            ndcg_v = v['NDCG@10']
            history.append({'epoch': epoch, 'loss': avg_loss, 'nll': avg_nll,
                            'kl': avg_kl, 'beta': beta, 'val_ndcg10': ndcg_v})
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
                print(f'    epoch {epoch:3d}  loss={avg_loss:.4f} '
                      f'nll={avg_nll:.4f} kl={avg_kl:.4f} beta={beta:.3f} '
                      f'val_ndcg@10={ndcg_v:.4f}{marker}')
            if no_improve >= patience:
                if verbose:
                    print(f'    early stop at epoch {epoch} (best epoch {best_epoch}, ndcg {best_ndcg:.4f})')
                break

    if val_inters is not None and best_state is not None:
        model.load_state_dict(best_state)
    return model, X_train, {'history': history, 'best_epoch': best_epoch,
                             'best_val_ndcg': best_ndcg}


# -----------------------------------------------------------------------------
# Hyperparameter sweep
# -----------------------------------------------------------------------------
def search_best_config(dataset: str, n_users: int, n_items: int,
                       train_inters: List[dict], val_inters: List[dict],
                       sweep_grid: List[dict], seed: int,
                       max_epochs: int, patience: int,
                       batch_size: int, eval_user_cap: int = 0
                       ) -> Tuple[dict, list]:
    """Train each candidate config with inner-val early stopping; pick best."""
    records = []
    best = None
    best_score = -1.0
    for ci, cfg in enumerate(sweep_grid):
        t0 = time.time()
        try:
            _, _, info = train_multivae(n_users, n_items, train_inters, val_inters,
                                         cfg, seed=seed, max_epochs=max_epochs,
                                         patience=patience, batch_size=batch_size,
                                         verbose=False, eval_user_cap=eval_user_cap)
            ndcg = info['best_val_ndcg']
            best_epoch = info['best_epoch']
        except Exception as e:
            print(f'  cfg[{ci+1:02d}] FAIL: {cfg} -> {e}')
            ndcg = -1.0
            best_epoch = -1
        dt = time.time() - t0
        rec = {'config': cfg, 'val_ndcg10': float(ndcg),
               'best_epoch': best_epoch, 'time_s': dt}
        records.append(rec)
        print(f'  cfg[{ci+1:02d}/{len(sweep_grid)}] {cfg} -> val NDCG@10={ndcg:.4f} '
              f'(best epoch {best_epoch}, {dt:.1f}s)')
        if ndcg > best_score:
            best_score = ndcg
            best = cfg
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        gc.collect()
    print(f'  >> best config: {best}  (val NDCG@10={best_score:.4f})')
    return best, records


def make_sweep_grid(dataset: str = '') -> List[dict]:
    """Sweep: latent_dim in {100, 200, 400} x beta_cap in {0.05, 0.2, 0.5} x
    total_anneal in {50, 200, 500} = 27 configs."""
    grid = []
    for lat, bcap, ts in itertools.product(
            [100, 200, 400], [0.05, 0.2, 0.5], [50, 200, 500]):
        grid.append({
            'latent_dim': lat,
            'enc_hidden': 600,
            'dec_hidden': 600,
            'dropout': 0.5,
            'lr': 1e-3,
            'weight_decay': 0.0,
            'beta_anneal_cap': bcap,
            'total_anneal_steps': ts,
            'eval_every': 5,
        })
    return grid


# -----------------------------------------------------------------------------
# Main per-dataset driver
# -----------------------------------------------------------------------------
def run_dataset(dataset: str, seeds: List[int], out_root: str,
                max_epochs_search: int = 80, max_epochs_final: int = 200,
                patience_search: int = 10, patience_final: int = 15,
                batch_size: int = 256,
                sweep_eval_user_cap: int = 0,
                ) -> dict:
    K = DATASET_KCORE[dataset]
    print(f'\n{"#"*70}\n#  MULTIVAE STRICT: {dataset.upper()} (k-core={K})\n{"#"*70}')
    cache_dir = os.path.join(ROOT, 'cache', dataset)
    data = pickle.load(open(os.path.join(cache_dir, 'raw_data_dedup.pkl'), 'rb'))
    filtered = kcore_filter(data['interactions'], K)
    interactions, _, n_users, n_items, _ = reindex(filtered, data['item_metadata'])
    print(f'  {n_users:,} users / {n_items:,} items / {len(interactions):,} interactions')

    # --- hp sweep on fold 0 inner split, seed[0] ---
    sweep_seed = seeds[0]
    splits_for_sweep = make_warm_kfold(interactions, n_splits=NUM_FOLDS, seed=SEED)
    tr_idx, _ = splits_for_sweep[0]
    f0_train = [interactions[i] for i in tr_idx]
    rng = np.random.RandomState(sweep_seed)
    inner_train, inner_val = _make_inner_val(f0_train, rng, val_frac=0.10)
    print(f'  hp sweep on fold-0 inner split: {len(inner_train)} train / {len(inner_val)} val')

    sweep_grid = make_sweep_grid(dataset)
    sweep_epochs = max_epochs_search
    if dataset == 'books':
        sweep_epochs = 50
    elif dataset == 'instruments':
        sweep_epochs = 60

    best_cfg, sweep_recs = search_best_config(
        dataset, n_users, n_items, inner_train, inner_val,
        sweep_grid, seed=sweep_seed,
        max_epochs=sweep_epochs, patience=patience_search,
        batch_size=batch_size, eval_user_cap=sweep_eval_user_cap,
    )

    # --- final eval: best_cfg across all seeds and all folds ---
    per_seed_summary = {}
    perfold_records_all = []  # [dataset, fold_id, seed, method, uid, item, ndcg10, hr10, rr]
    for seed in seeds:
        print(f'\n  >>> dataset={dataset} seed={seed} final 5-fold eval')
        splits = make_warm_kfold(interactions, n_splits=NUM_FOLDS, seed=SEED)
        fold_results = []
        for fi, (tr_idx, te_idx) in enumerate(splits):
            tr = [interactions[i] for i in tr_idx]
            te = [interactions[i] for i in te_idx]
            # inner split per (seed, fold) for final early stopping
            rng2 = np.random.RandomState(seed + fi * 7919)
            it, iv = _make_inner_val(tr, rng2, val_frac=0.10)
            t0 = time.time()
            model, X_inner, info = train_multivae(
                n_users, n_items, it, iv,
                best_cfg, seed=seed,
                max_epochs=max_epochs_final,
                patience=patience_final,
                batch_size=batch_size, verbose=False)
            # IMPORTANT: for the warm-LOO eval, we need to give the model the
            # FULL training row (train fold tr, not the inner-train it) so the
            # encoder sees all the user's training interactions. Build X_full
            # from tr.
            X_full = _user_csr(tr, n_users, n_items)
            r = _evaluate_warm_loo(model, X_full, tr, te, n_users, n_items,
                                    return_per_pair=True)
            dt = time.time() - t0
            fold_results.append(r)
            print(f'    fold {fi}: NDCG@10={r["NDCG@10"]:.4f}  HR@10={r["HR@10"]:.4f}  '
                  f'MRR={r["MRR"]:.4f}  n={r["n_eval"]} '
                  f'(best epoch {info["best_epoch"]}, {dt:.1f}s)')
            for u, it_id, val, h, rr in zip(
                    r['user_id_per_pair'], r['target_item_id_per_pair'],
                    r['ndcg_per_pair'], r['hr_per_pair'], r['rr_per_pair']):
                perfold_records_all.append(
                    [dataset, fi, seed, 'multivae_strict', u, it_id, val, h, rr])
            del model, X_inner
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
        print(f'  seed {seed} 5-fold: NDCG@10={n_mean:.4f}+/-{n_std:.4f}  '
              f'HR@10={h_mean:.4f}  MRR={m_mean:.4f}')

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
    print(f'\n  ===== {dataset.upper()} across-seed: '
          f'NDCG@10={agg["NDCG@10_mean_across_seeds"]:.4f}'
          f'+/-{agg["NDCG@10_std_across_seeds"]:.4f}  best_cfg={best_cfg} =====')

    # per-fold per-pair records
    perfold_path = os.path.join(out_root,
        f'results_multivae_strict_perfold_{dataset}.json')
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
    ap.add_argument('--max-epochs-search', type=int, default=80)
    ap.add_argument('--max-epochs-final',  type=int, default=200)
    ap.add_argument('--patience-search',   type=int, default=10)
    ap.add_argument('--patience-final',    type=int, default=15)
    ap.add_argument('--batch-size',        type=int, default=256)
    ap.add_argument('--sweep-eval-cap',    type=int, default=0,
                    help='Cap users used during sweep validation (0 = full).')
    args = ap.parse_args()

    seeds = [int(x.strip()) for x in str(args.seeds).split(',') if x.strip()]
    out_root = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(out_root, 'results_multivae_strict.json')

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
        'Publication-grade MultiVAE baseline: Liang et al., WWW 2018, '
        '"Variational Autoencoders for Collaborative Filtering". Architecture: '
        '[n_items -> 600 -> 2*latent_dim] encoder, [latent_dim -> 600 -> n_items] '
        'decoder, tanh activations, dropout 0.5 on L2-normalized input. '
        'Multinomial-NLL + beta-annealed KL loss. Same warm-LOO splits as '
        'run_warm_loo.py (SEED=42). Hyperparameter sweep on fold-0 inner split '
        '(latent_dim x beta_cap x total_anneal_steps); final eval is the chosen '
        'config across 3 seeds x 5 folds.')

    for ds in args.datasets:
        agg = run_dataset(ds, seeds, out_root,
                          max_epochs_search=args.max_epochs_search,
                          max_epochs_final=args.max_epochs_final,
                          patience_search=args.patience_search,
                          patience_final=args.patience_final,
                          batch_size=args.batch_size,
                          sweep_eval_user_cap=args.sweep_eval_cap)
        all_results[ds] = agg
        with open(out_path, 'w') as f:
            json.dump(all_results, f, indent=2,
                      default=lambda o: float(o) if hasattr(o, 'item') else str(o))
        print(f'  updated {os.path.basename(out_path)}')

    print('\n\n========= MULTIVAE STRICT SUMMARY =========')
    for ds in args.datasets:
        v = all_results.get(ds, {})
        print(f'  {ds:>13s}: NDCG@10={v.get("NDCG@10_mean_across_seeds", 0):.4f}'
              f'+/-{v.get("NDCG@10_std_across_seeds", 0):.4f}  '
              f'best_cfg={v.get("best_config")}')


if __name__ == '__main__':
    main()
