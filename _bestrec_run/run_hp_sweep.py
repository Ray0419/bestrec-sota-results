"""Hyperparameter sensitivity sweep — heatmap of NDCG@10 across (lambda, beta).

For each dataset, sweep a 2D grid of (lambda, beta) and visualize as a heatmap.
Helps reviewers see that performance is robust around the chosen hyperparameters.
"""
import os, sys, json, pickle, gc
sys.path.insert(0, os.path.dirname(__file__))
from collections import defaultdict
import numpy as np
import torch
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from ease_efficient import ease_fast
from v5_utils import (
    kcore_filter, reindex, make_warm_kfold, build_X_sparse,
    content_sim_matrix, ROOT, NUM_FOLDS, TOP_K, SEED, RANKING_USERS_CAP,
)

DATASET_KCORE = {'beauty': 5, 'fashion': 4, 'instruments': 10, 'books': 20}
LAMBDAS = [10, 30, 100, 300, 1000, 3000]
BETAS   = [0, 1, 3, 10, 30, 100]


def per_user_ndcg(score_fn, train_inters, test_inters, n_items, top_k=TOP_K, max_users=2000):
    user_train = defaultdict(set)
    for i in train_inters: user_train[i['user_id']].add(i['item_id'])
    user_test = defaultdict(set)
    for i in test_inters: user_test[i['user_id']].add(i['item_id'])
    users = [u for u in user_test if user_test[u]]
    if len(users) > max_users:
        rng = np.random.RandomState(SEED)
        users = sorted(rng.choice(users, max_users, replace=False).tolist())
    ndcg = []; BATCH = 512
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
                ndcg.append(1.0 / np.log2(pr + 2) if pr < top_k else 0.0)
    return float(np.mean(ndcg))


def sweep_dataset(dataset, n_folds_use=3):
    K_CORE = DATASET_KCORE[dataset]
    print(f'\n{"#"*70}\n#  HP SWEEP: {dataset.upper()} (k={K_CORE}, {n_folds_use} folds)\n{"#"*70}')
    cache_dir = os.path.join(ROOT, "cache", dataset)
    data = pickle.load(open(os.path.join(cache_dir, "raw_data_dedup.pkl"), 'rb'))
    filtered = kcore_filter(data['interactions'], K_CORE)
    interactions, item_meta, n_users, n_items, _ = reindex(filtered, data['item_metadata'])
    print(f'  {n_users:,} users / {n_items:,} items')

    title_path = os.path.join(cache_dir, "v5", f"item_title_k{K_CORE}_dedup.pt")
    item_title_emb = torch.load(title_path, weights_only=True)
    S_content = content_sim_matrix(item_title_emb, dtype=np.float32)
    warm_splits = make_warm_kfold(interactions)

    grid = np.zeros((len(LAMBDAS), len(BETAS)), dtype=np.float64)
    for i, lam in enumerate(LAMBDAS):
        for j, beta in enumerate(BETAS):
            ndcgs = []
            for fi in range(min(n_folds_use, len(warm_splits))):
                tr, te = warm_splits[fi]
                tr_i = [interactions[k] for k in tr]; te_i = [interactions[k] for k in te]
                X = build_X_sparse(tr_i, n_users, n_items)
                B = ease_fast(X, lam=lam, beta=beta,
                              S_content=S_content if beta > 0 else None,
                              dtype=np.float32)
                fn = lambda uids, B=B: (X[uids] @ B).astype(np.float32)
                ndcgs.append(per_user_ndcg(fn, tr_i, te_i, n_items))
                del B; gc.collect()
            grid[i, j] = float(np.mean(ndcgs))
            print(f'    lam={lam:>5d} beta={beta:>4d} -> NDCG@10={grid[i, j]:.4f}')

    return grid


def plot_heatmap(grid, dataset, save_path):
    fig, ax = plt.subplots(figsize=(7, 5))
    im = ax.imshow(grid, cmap='YlGnBu', aspect='auto', interpolation='nearest')
    ax.set_xticks(np.arange(len(BETAS))); ax.set_xticklabels(BETAS)
    ax.set_yticks(np.arange(len(LAMBDAS))); ax.set_yticklabels(LAMBDAS)
    ax.set_xlabel(r'$\beta$ (content prior weight)')
    ax.set_ylabel(r'$\lambda$ (L2 regularization)')
    ax.set_title(f'NDCG@10 sensitivity — {dataset.capitalize()}')
    # Annotate
    for i in range(len(LAMBDAS)):
        for j in range(len(BETAS)):
            color = 'white' if grid[i, j] > 0.5 * grid.max() + 0.5 * grid.min() else 'black'
            ax.text(j, i, f'{grid[i, j]:.3f}', ha='center', va='center',
                     color=color, fontsize=9)
    # Mark best
    bi, bj = np.unravel_index(np.argmax(grid), grid.shape)
    ax.add_patch(plt.Rectangle((bj-0.5, bi-0.5), 1, 1, fill=False,
                                edgecolor='red', linewidth=2.5))
    plt.colorbar(im, ax=ax, label='NDCG@10')
    plt.tight_layout()
    plt.savefig(save_path)
    plt.savefig(save_path.replace('.png', '.pdf'))
    plt.close(fig)
    print(f'  Best: lam={LAMBDAS[bi]}, beta={BETAS[bj]}, NDCG@10={grid[bi, bj]:.4f}')
    print(f'  Saved -> {save_path}')


def main():
    if len(sys.argv) > 1:
        datasets = sys.argv[1:]
    else:
        datasets = ['beauty', 'fashion', 'instruments']  # skip books (slow)

    fig_dir = os.path.join(os.path.dirname(__file__), "figures")
    os.makedirs(fig_dir, exist_ok=True)

    all_grids = {}
    for ds in datasets:
        grid = sweep_dataset(ds, n_folds_use=3)
        all_grids[ds] = grid.tolist()
        plot_heatmap(grid, ds, os.path.join(fig_dir, f"fig6_hp_sensitivity_{ds}.png"))

    # Combined figure (3 subplots)
    fig, axes = plt.subplots(1, len(datasets), figsize=(7 * len(datasets), 5))
    if len(datasets) == 1: axes = [axes]
    for ax, ds in zip(axes, datasets):
        grid = np.array(all_grids[ds])
        im = ax.imshow(grid, cmap='YlGnBu', aspect='auto', interpolation='nearest')
        ax.set_xticks(np.arange(len(BETAS))); ax.set_xticklabels(BETAS)
        ax.set_yticks(np.arange(len(LAMBDAS))); ax.set_yticklabels(LAMBDAS)
        ax.set_xlabel(r'$\beta$')
        ax.set_ylabel(r'$\lambda$')
        ax.set_title(ds.capitalize())
        for i in range(len(LAMBDAS)):
            for j in range(len(BETAS)):
                color = 'white' if grid[i, j] > 0.5 * grid.max() + 0.5 * grid.min() else 'black'
                ax.text(j, i, f'{grid[i, j]:.3f}', ha='center', va='center',
                         color=color, fontsize=8)
        bi, bj = np.unravel_index(np.argmax(grid), grid.shape)
        ax.add_patch(plt.Rectangle((bj-0.5, bi-0.5), 1, 1, fill=False,
                                    edgecolor='red', linewidth=2.5))
        plt.colorbar(im, ax=ax)
    plt.suptitle('Hyperparameter Sensitivity (NDCG@10, 3-fold)', fontsize=14)
    plt.tight_layout()
    plt.savefig(os.path.join(fig_dir, "fig6_hp_sensitivity_combined.png"))
    plt.savefig(os.path.join(fig_dir, "fig6_hp_sensitivity_combined.pdf"))
    plt.close(fig)
    print(f'\nSaved combined heatmap to {fig_dir}/fig6_hp_sensitivity_combined.{{png,pdf}}')

    json.dump(all_grids, open(os.path.join(os.path.dirname(__file__),
              "results_hp_sweep.json"), "w"), indent=2,
              default=lambda o: float(o) if hasattr(o, 'item') else str(o))


if __name__ == "__main__":
    main()
