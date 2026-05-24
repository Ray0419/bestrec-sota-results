"""Compute Holm-corrected per-USER paired Wilcoxon for MultiVAE-strict vs
EASE+SBERT on the warm-LOO per-user NDCG@10 vectors.

Inputs:
  results_warm_loo_perfold_<ds>.json   - ease_sbert per-user NDCG@10 (3-tuples)
  results_multivae_strict_perfold_<ds>.json - multivae_strict per-(user, seed)

Output:
  results_multivae_strict_wilcoxon.json    - per-dataset paired wilcoxon stats

Per-user aggregation:
  - ease_sbert:        mean across folds for each user_id  (n_users measurements)
  - multivae_strict:   mean across (seed, fold) for each user_id  (n_users measurements)
  - drop users present in only one of the two sources
"""
import argparse
import json
import os
from collections import defaultdict

import numpy as np
from scipy.stats import wilcoxon


def load_ease_per_user(perfold_path, method='ease_sbert'):
    """Return user_id -> mean NDCG@10 over folds for given method."""
    d = json.load(open(perfold_path))
    rows = d['methods'][method]   # list of [fold, user, ndcg]
    by_u = defaultdict(list)
    for fold, uid, ndcg in rows:
        by_u[int(uid)].append(float(ndcg))
    return {u: float(np.mean(v)) for u, v in by_u.items()}


def load_multivae_per_user(perfold_path):
    """Return user_id -> mean NDCG@10 over (seed, fold) for multivae_strict.

    Records schema: [dataset, fold, seed, method, user_id, target_item_id, ndcg10, hr10, rr]
    """
    d = json.load(open(perfold_path))
    rows = d['records']
    by_u = defaultdict(list)
    for r in rows:
        uid = int(r[4]); ndcg = float(r[6])
        by_u[uid].append(ndcg)
    return {u: float(np.mean(v)) for u, v in by_u.items()}


def holm(pvals):
    """Holm-Bonferroni step-down. Returns adjusted p-values, same length."""
    m = len(pvals)
    order = np.argsort(pvals)
    adj = np.zeros(m)
    running_max = 0.0
    for rank, idx in enumerate(order):
        cand = (m - rank) * pvals[idx]
        running_max = max(running_max, min(1.0, cand))
        adj[idx] = running_max
    return adj


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('datasets', nargs='*',
                    default=['beauty', 'fashion', 'instruments', 'books'])
    args = ap.parse_args()
    root = os.path.dirname(os.path.abspath(__file__))

    raw = {}
    for ds in args.datasets:
        ease_path = os.path.join(root, f'results_warm_loo_perfold_{ds}.json')
        vae_path  = os.path.join(root, f'results_multivae_strict_perfold_{ds}.json')
        if not os.path.exists(ease_path):
            print(f'  SKIP {ds}: missing {ease_path}')
            continue
        if not os.path.exists(vae_path):
            print(f'  SKIP {ds}: missing {vae_path}')
            continue
        ease = load_ease_per_user(ease_path, method='ease_sbert')
        vae  = load_multivae_per_user(vae_path)
        common = sorted(set(ease.keys()) & set(vae.keys()))
        ease_v = np.array([ease[u] for u in common])
        vae_v  = np.array([vae[u]  for u in common])
        diff   = vae_v - ease_v   # positive = multivae wins
        n_users = len(common)
        n_pos = int((diff > 0).sum())
        n_neg = int((diff < 0).sum())
        n_zero = int((diff == 0).sum())
        vae_mean  = float(np.mean(vae_v))
        ease_mean = float(np.mean(ease_v))
        if (diff != 0).any():
            stat = wilcoxon(diff[diff != 0], alternative='two-sided')
            stat_g = wilcoxon(diff[diff != 0], alternative='greater')
            stat_l = wilcoxon(diff[diff != 0], alternative='less')
            p_two   = float(stat.pvalue)
            p_gt    = float(stat_g.pvalue)
            p_lt    = float(stat_l.pvalue)
            w_stat  = float(stat.statistic)
        else:
            p_two = p_gt = p_lt = 1.0
            w_stat = 0.0
        raw[ds] = {
            'n_users_paired': n_users,
            'ease_sbert_NDCG@10_per_user_mean': ease_mean,
            'multivae_strict_NDCG@10_per_user_mean': vae_mean,
            'mean_diff_multivae_minus_ease_sbert': float(np.mean(diff)),
            'n_multivae_wins': n_pos,
            'n_ease_sbert_wins': n_neg,
            'n_ties': n_zero,
            'wilcoxon_two_sided_p': p_two,
            'wilcoxon_multivae_greater_p': p_gt,
            'wilcoxon_multivae_less_p': p_lt,
            'wilcoxon_statistic': w_stat,
        }
        print(f'  {ds:>13s}: ease_sbert={ease_mean:.4f}  multivae={vae_mean:.4f}  '
              f'diff={float(np.mean(diff)):+.4f}  wins V/E={n_pos}/{n_neg}  '
              f'p_two={p_two:.3e}  p_gt={p_gt:.3e}  p_lt={p_lt:.3e}  n_users={n_users}')

    # Holm correction across datasets on the two-sided p
    keys = list(raw.keys())
    if keys:
        pvals = np.array([raw[k]['wilcoxon_two_sided_p'] for k in keys])
        adj   = holm(pvals)
        for k, a in zip(keys, adj):
            raw[k]['wilcoxon_two_sided_p_holm'] = float(a)
        pvals_gt = np.array([raw[k]['wilcoxon_multivae_greater_p'] for k in keys])
        adj_gt = holm(pvals_gt)
        for k, a in zip(keys, adj_gt):
            raw[k]['wilcoxon_multivae_greater_p_holm'] = float(a)
        pvals_lt = np.array([raw[k]['wilcoxon_multivae_less_p'] for k in keys])
        adj_lt = holm(pvals_lt)
        for k, a in zip(keys, adj_lt):
            raw[k]['wilcoxon_multivae_less_p_holm'] = float(a)

    out_path = os.path.join(root, 'results_multivae_strict_wilcoxon.json')
    with open(out_path, 'w') as f:
        json.dump({
            'note': ('Per-USER paired Wilcoxon for tuned MultiVAE vs EASE+SBERT '
                     'on warm-LOO. Per-user NDCG@10 is the mean over folds '
                     '(ease_sbert) or over (seed, fold) (multivae_strict). '
                     'Holm-Bonferroni correction is applied ACROSS the per-dataset '
                     'p-values for each of the three alternatives.'),
            'methods_compared': ['multivae_strict (multi-seed multi-config tuned)',
                                 'ease_sbert (warm-LOO, single seed=42 from run_warm_loo.py)'],
            'per_dataset': raw,
        }, f, indent=2)
    print(f'\nwrote {os.path.basename(out_path)}')


if __name__ == '__main__':
    main()
