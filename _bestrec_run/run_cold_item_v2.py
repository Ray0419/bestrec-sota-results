"""Cold-item v2: novel algorithms beyond content-direct.

Adds three new methods that try to capture collaborative signal in
content-only cold-item prediction:

  6. lc2c (Learned Content-to-CF mapping):
       Train ridge regression W: SBERT_warm -> E_cf_warm where E_cf_warm = SVD(B_warm)
       For cold items: E_cf_cold = SBERT_cold @ W
       score(u, cold_j) = X[u, warm] @ E_cf_warm @ E_cf_cold[j].T

  7. content_rating_weighted:
       Use centered ratings (rating - global_mean) as weights instead of binary X
       score(u, cold_j) = sum over rated_i of (r_ui - gm) * S_content[i, j]

  8. content_topk:
       Only use user's TOP-rated items (rating 4+) as content anchors
       score(u, cold_j) = avg over user's high-rated i of S_content[i, j]

  9. cf_hybrid:
       LC2C + content_direct, rank-fused
       Captures both: collaborative refinement of content + raw content match

  10. lc2cpp_fusion:
       LC2C++ predeclared rank fusion over LC2C V2, content-direct, and
       content-topK scores.

  11. lc2cpp_kernel:
       LC2C++ kernel/rich-feature variant using normalized SBERT, whitening,
       random Fourier features, and ridge mapping into the EASE behaviour vector.
"""
import os, sys, json, pickle, gc
sys.path.insert(0, os.path.dirname(__file__))
from collections import defaultdict
import numpy as np
import torch
from scipy.sparse import csr_matrix
from scipy.stats import rankdata
from sklearn.decomposition import TruncatedSVD
from sklearn.linear_model import Ridge

from ease_efficient import ease_fast
from v5_utils import (
    kcore_filter, reindex, build_X_sparse, content_sim_matrix,
    ROOT, NUM_FOLDS, TOP_K, SEED, RANKING_USERS_CAP,
)
from run_cold_item import (
    DATASET_KCORE, HP, make_item_kfold, reindex_warm_only, eval_cold_item_ranking,
)


def make_score_lc2c_v1(X_warm, B_warm, item_title_emb, warm_indices, cold_arr, latent_dim=64):
    """LC2C V1 (legacy, SVD-compressed):
    1. Compute warm item CF embeddings: E_cf_warm = TruncatedSVD(B_warm, k=latent_dim)
    2. Learn ridge regression: SBERT_warm @ W ≈ E_cf_warm
    3. Predict E_cf_cold = SBERT_cold @ W
    4. score(u, cold_j) = X[u, warm] @ E_cf_warm @ E_cf_cold[j].T

    This is the older "lc2c" used as the LC2C-V1 ablation in the paper.
    The headline LC2C method is V2 (lc2c_direct) below.
    """
    n_warm = len(warm_indices); n_cold = len(cold_arr)
    B_sym = 0.5 * (B_warm + B_warm.T)
    k = min(latent_dim, n_warm - 1)
    svd = TruncatedSVD(n_components=k, random_state=SEED)
    E_cf_warm = svd.fit_transform(B_sym).astype(np.float32)
    emb = item_title_emb.cpu().numpy() if hasattr(item_title_emb, 'cpu') else np.asarray(item_title_emb)
    emb = emb.astype(np.float32)
    SBERT_warm = emb[warm_indices]
    SBERT_cold = emb[cold_arr]
    reg = Ridge(alpha=1.0)
    reg.fit(SBERT_warm, E_cf_warm)
    E_cf_cold_pred = reg.predict(SBERT_cold).astype(np.float32)
    Xw = X_warm[:, warm_indices].astype(np.float32)
    UE = Xw @ E_cf_warm
    score_mat = UE @ E_cf_cold_pred.T
    def fn(user_ids, cold_arr):
        return score_mat[user_ids]
    return fn


# Backward-compatibility alias (the paper's text and results JSON keys use
# `lc2c` for what we now call `lc2c_v1`; we keep the alias so existing
# downstream callers do not break).
def make_score_lc2c(*args, **kwargs):
    return make_score_lc2c_v1(*args, **kwargs)


def make_score_dropoutnet(X_warm, B_warm, item_title_emb, warm_indices, cold_arr,
                            latent_dim: int = 64, epochs: int = 100, lr: float = 1e-3,
                            dropout_p: float = 0.5, batch_size: int = 256,
                            seed: int = SEED):
    """DropoutNet (Volkovs, Yu, Poutanen, NeurIPS 2017) — cold-start baseline.

    Standard DropoutNet recipe, faithfully implemented for our cold-item-only
    protocol:

      1. Compute pretrained WMF/SVD reference embeddings (U_ref, V_ref) from the
         warm interaction matrix X_warm. These play the role of the WMF latent
         factors in the original DropoutNet paper.
      2. Train an *item tower* MLP whose input is the concatenation of the item's
         CF latent (V_ref) and content feature (SBERT title embedding) and whose
         output is a k-dimensional item embedding. The training target is the
         WMF item factor V_ref itself.
      3. During training, randomly zero the CF input branch with probability
         dropout_p so that the model learns to predict the item factor from
         content alone. This is the dropout mechanism that gives DropoutNet
         its name and the property of working on cold items.
      4. At inference for a cold item, the CF input is zero (no observed
         interactions) and the content input is the cold item's SBERT vector;
         the trained item tower predicts the item embedding from content.
      5. Score(u, cold_j) = U_ref[u] @ V_cold_predicted[j].

    This is a faithful, simplified-but-correct instantiation. Differences from
    the original paper: (a) we use SVD instead of WMF for the reference factors
    (closed-form, deterministic); (b) we do not train a user tower because our
    cold-item protocol has only warm users, so the user-cold-start mechanism is
    irrelevant; (c) we use only content features (SBERT) for items, since
    Amazon Reviews 2023 does not include other curated item attributes in our
    preprocessing.
    """
    import torch
    import torch.nn as nn
    import torch.optim as optim
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    n_warm = len(warm_indices)
    n_cold = len(cold_arr)
    n_users = X_warm.shape[0]

    # 1. Pretrained WMF/SVD reference factors from warm interactions
    Xw = X_warm[:, warm_indices].astype(np.float32)
    k = min(latent_dim, n_warm - 1, n_users - 1)
    svd = TruncatedSVD(n_components=k, random_state=seed)
    U_ref = svd.fit_transform(Xw)                        # (n_users, k)
    V_ref = svd.components_.T.astype(np.float32)         # (n_warm, k)
    U_ref = U_ref.astype(np.float32)

    # 2. Content features
    emb = item_title_emb.cpu().numpy() if hasattr(item_title_emb, 'cpu') else np.asarray(item_title_emb)
    emb = emb.astype(np.float32)
    SBERT_warm = emb[warm_indices]
    SBERT_cold = emb[cold_arr]
    ds = SBERT_warm.shape[1]

    # 3. Item tower: [CF latent ; SBERT] -> k-dim embedding
    class ItemTower(nn.Module):
        def __init__(self, cf_dim, content_dim, out_dim, hidden=128):
            super().__init__()
            self.f = nn.Sequential(
                nn.Linear(cf_dim + content_dim, hidden), nn.ReLU(),
                nn.Linear(hidden, hidden), nn.ReLU(),
                nn.Linear(hidden, out_dim),
            )
        def forward(self, cf, content):
            return self.f(torch.cat([cf, content], dim=-1))

    item_net = ItemTower(cf_dim=k, content_dim=ds, out_dim=k).to(device)
    opt = optim.Adam(item_net.parameters(), lr=lr)

    V_ref_t = torch.from_numpy(V_ref).to(device)
    SBERT_warm_t = torch.from_numpy(SBERT_warm).to(device)

    # 4. Train with CF-input dropout. Target = V_ref (the WMF item factor).
    rng_t = np.random.RandomState(seed)
    n_iter_per_epoch = max(1, n_warm // batch_size)
    for ep in range(epochs):
        idx_perm = rng_t.permutation(n_warm)
        for b in range(n_iter_per_epoch):
            sl = idx_perm[b * batch_size : (b + 1) * batch_size]
            if len(sl) == 0:
                continue
            sl_t = torch.from_numpy(sl).to(device)
            cf = V_ref_t[sl_t].clone()
            ct = SBERT_warm_t[sl_t]
            target = V_ref_t[sl_t]
            # Per-sample random CF dropout (Bernoulli(dropout_p))
            drop_mask = (torch.rand(len(sl), device=device) < dropout_p).unsqueeze(1)
            cf_dropped = torch.where(drop_mask, torch.zeros_like(cf), cf)
            pred = item_net(cf_dropped, ct)
            loss = ((pred - target) ** 2).mean()
            opt.zero_grad(); loss.backward(); opt.step()

    # 5. Inference for cold items: zero CF + SBERT content -> predicted embedding
    item_net.eval()
    with torch.no_grad():
        zero_cf_cold = torch.zeros(n_cold, k, device=device)
        SBERT_cold_t = torch.from_numpy(SBERT_cold).to(device)
        V_cold_pred = item_net(zero_cf_cold, SBERT_cold_t).cpu().numpy()

    # 6. Score: U_ref[u] @ V_cold_pred[j].T
    score_mat = U_ref @ V_cold_pred.T  # (n_users, n_cold)

    def fn(user_ids, cold_arr):
        return score_mat[user_ids]
    return fn


def make_score_lc2c_v2(X_warm, B_warm, item_title_emb, warm_indices, cold_arr,
                        mu: float = 1.0):
    """LC2C V2 (HEADLINE METHOD, direct ridge, no SVD):
    1. Learn ridge regression W: SBERT_warm @ W ≈ B_warm.T
       (mapping SBERT embeddings directly to full collaborative behaviour vectors)
    2. Predict B_hat_cold[:, j] = (SBERT_cold[j] @ W).T  for each cold item j
    3. score(u, cold_j) = X[u, warm] @ B_hat_cold[:, j]

    This is the LC2C-direct (V2) method reported as the headline LC2C
    algorithm in the paper. See run_lc2c_ablation.py for the corresponding
    V1/V2/V3 comparison.
    """
    emb = item_title_emb.cpu().numpy() if hasattr(item_title_emb, 'cpu') else np.asarray(item_title_emb)
    emb = emb.astype(np.float32)
    SBERT_warm = emb[warm_indices]
    SBERT_cold = emb[cold_arr]

    # Direct ridge: map SBERT to full B-row of EASE on warm items.
    reg = Ridge(alpha=mu)
    reg.fit(SBERT_warm, B_warm.T.astype(np.float32))  # targets: (n_warm, n_warm)
    # reg.coef_ has shape (n_warm, 384) -> W = coef_.T = (384, n_warm)
    W = reg.coef_.T.astype(np.float32)
    # Predict B_hat columns for each cold item
    B_hat_cold = (SBERT_cold @ W).T  # (n_warm, n_cold)

    Xw = X_warm[:, warm_indices].astype(np.float32)
    score_mat = Xw @ B_hat_cold  # (n_users, n_cold)
    def fn(user_ids, cold_arr):
        return score_mat[user_ids]
    return fn


def _normalize_rows(x, eps: float = 1e-8):
    n = np.linalg.norm(x, axis=1, keepdims=True)
    return x / np.maximum(n, eps)


def _whiten_from_train(train, test, eps: float = 1e-6):
    mean = train.mean(axis=0, keepdims=True)
    std = train.std(axis=0, keepdims=True)
    std = np.maximum(std, eps)
    return (train - mean) / std, (test - mean) / std


def _rff_features(train, test, n_features: int = 1024, gamma: float = 0.25,
                  seed: int = SEED):
    rng = np.random.RandomState(seed)
    W = rng.normal(0.0, np.sqrt(2.0 * gamma), size=(train.shape[1], n_features)).astype(np.float32)
    b = rng.uniform(0.0, 2 * np.pi, size=(n_features,)).astype(np.float32)
    scale = np.float32(np.sqrt(2.0 / n_features))
    return (
        (scale * np.cos(train @ W + b)).astype(np.float32),
        (scale * np.cos(test @ W + b)).astype(np.float32),
    )


def make_score_lc2cpp_kernel(X_warm, B_warm, item_title_emb, warm_indices, cold_arr,
                             mu: float = 3.0, n_rff: int = 1024,
                             gamma: float = 0.25, seed: int = SEED):
    """LC2C++ kernel/rich-feature variant.

    Predeclared transformation: L2-normalize SBERT, whiten on warm items, append
    random Fourier features, then ridge-map into B_warm.T exactly as LC2C V2.
    """
    emb = item_title_emb.cpu().numpy() if hasattr(item_title_emb, 'cpu') else np.asarray(item_title_emb)
    emb = _normalize_rows(emb.astype(np.float32))
    warm = emb[warm_indices]
    cold = emb[cold_arr]
    warm_w, cold_w = _whiten_from_train(warm, cold)
    warm_rff, cold_rff = _rff_features(warm_w, cold_w, n_features=n_rff, gamma=gamma, seed=seed)
    warm_feat = np.concatenate([warm_w, warm_rff], axis=1).astype(np.float32)
    cold_feat = np.concatenate([cold_w, cold_rff], axis=1).astype(np.float32)

    reg = Ridge(alpha=mu)
    reg.fit(warm_feat, B_warm.T.astype(np.float32))
    W = reg.coef_.T.astype(np.float32)
    B_hat_cold = (cold_feat @ W).T

    Xw = X_warm[:, warm_indices].astype(np.float32)
    score_mat = Xw @ B_hat_cold
    def fn(user_ids, cold_arr):
        return score_mat[user_ids]
    return fn


def make_score_lc2cpp_fusion(sf_lc2c_v2, sf_content, sf_content_topk,
                             weights=(0.5, 0.3, 0.2)):
    """LC2C++ rank fusion over LC2C V2, content-direct, and top-rated content."""
    w_lc, w_co, w_top = weights

    def fn(user_ids, cold_arr):
        scores = [
            (w_lc, sf_lc2c_v2(user_ids, cold_arr)),
            (w_co, sf_content(user_ids, cold_arr)),
            (w_top, sf_content_topk(user_ids, cold_arr)),
        ]
        fused = None
        for w, s in scores:
            ranks = np.apply_along_axis(rankdata, 1, s).astype(np.float32)
            fused = w * ranks if fused is None else fused + w * ranks
        return fused
    return fn


def make_score_content_rating_weighted(train_inters, S_content, n_users, n_items,
                                        warm_indices, cold_arr):
    """Use centered ratings (r - gm) instead of binary X."""
    gs, gn = 0.0, 0
    for i in train_inters:
        gs += i['rating']; gn += 1
    gm = gs / gn if gn > 0 else 3.0

    X_centered = np.zeros((n_users, n_items), dtype=np.float32)
    for i in train_inters:
        X_centered[i['user_id'], i['item_id']] = i['rating'] - gm

    Xw = X_centered[:, warm_indices]
    S_wc = S_content[np.ix_(warm_indices, cold_arr)].astype(np.float32)
    score_mat = Xw @ S_wc  # (n_users, n_cold)

    def fn(user_ids, cold_arr):
        return score_mat[user_ids]
    return fn


def make_score_content_topk(train_inters, S_content, n_users, n_items,
                             warm_indices, cold_arr, threshold=4.0):
    """Use only user's top-rated items (rating >= threshold)."""
    X_top = np.zeros((n_users, n_items), dtype=np.float32)
    for i in train_inters:
        if i['rating'] >= threshold:
            X_top[i['user_id'], i['item_id']] = 1.0

    Xw = X_top[:, warm_indices]
    S_wc = S_content[np.ix_(warm_indices, cold_arr)].astype(np.float32)
    # Normalize by number of high-rated items per user
    counts = Xw.sum(axis=1, keepdims=True)
    counts[counts == 0] = 1
    score_mat = (Xw @ S_wc) / counts

    def fn(user_ids, cold_arr):
        return score_mat[user_ids]
    return fn


def make_score_cf_hybrid(make_lc2c_fn, make_content_fn, alpha=0.5):
    """Rank-fuse LC2C and content_direct."""
    fn_lc2c = make_lc2c_fn
    fn_content = make_content_fn

    def fn(user_ids, cold_arr):
        s_lc = fn_lc2c(user_ids, cold_arr)
        s_co = fn_content(user_ids, cold_arr)
        r_lc = np.apply_along_axis(rankdata, 1, s_lc).astype(np.float32)
        r_co = np.apply_along_axis(rankdata, 1, s_co).astype(np.float32)
        return alpha * r_lc + (1 - alpha) * r_co
    return fn


def _zscore_rows(x, eps: float = 1e-6):
    return (x - x.mean(axis=1, keepdims=True)) / np.maximum(x.std(axis=1, keepdims=True), eps)


def make_score_z_fusion(score_fns, weights):
    """Per-user z-score fusion. Fixed weights must be chosen before paper runs."""
    weights = np.asarray(weights, dtype=np.float32)
    weights = weights / weights.sum()

    def fn(user_ids, cold_arr):
        fused = None
        for w, score_fn in zip(weights, score_fns):
            z = _zscore_rows(score_fn(user_ids, cold_arr).astype(np.float32))
            fused = w * z if fused is None else fused + w * z
        return fused
    return fn


def make_score_random(seed=SEED):
    rng = np.random.RandomState(seed)
    def fn(user_ids, cold_arr):
        return rng.uniform(0, 1, size=(len(user_ids), len(cold_arr))).astype(np.float32)
    return fn


def make_score_content_direct(X_warm, S_content, warm_indices, cold_arr):
    Xw = X_warm[:, warm_indices].astype(np.float32)
    S_wc = S_content[np.ix_(warm_indices, cold_arr)].astype(np.float32)
    score_mat = Xw @ S_wc
    def fn(user_ids, cold_arr):
        return score_mat[user_ids]
    return fn


def run_cold_item_v2(dataset, n_splits=5):
    K_CORE = DATASET_KCORE[dataset]
    LAM, BETA = HP[dataset]
    print(f'\n{"#"*70}\n#  COLD-ITEM v2: {dataset.upper()} (k={K_CORE})\n{"#"*70}')
    cache_dir = os.path.join(ROOT, "cache", dataset)
    data = pickle.load(open(os.path.join(cache_dir, "raw_data_dedup.pkl"), 'rb'))
    filtered = kcore_filter(data['interactions'], K_CORE)
    interactions, item_meta, n_users, n_items, _ = reindex(filtered, data['item_metadata'])
    print(f'  {n_users:,} users / {n_items:,} items / {len(interactions):,} inters')

    title_path = os.path.join(cache_dir, "v5", f"item_title_k{K_CORE}_dedup.pt")
    item_title_emb = torch.load(title_path, weights_only=True)
    S_content = content_sim_matrix(item_title_emb, dtype=np.float32)

    splits = make_item_kfold(interactions, n_items, n_splits=n_splits)
    # NOTE: lc2c_v2 is the HEADLINE method reported in the paper as Table 5.4
    # "LC2C-direct (ours, no SVD)" / V2 / 0.173 / 0.155 / 0.058 / 0.065.
    # lc2c is the legacy V1 alias (SVD k=64 + ridge) kept for backward
    # compatibility with the older JSON keys consumed by make_figures_v3.py.
    methods = ['random', 'content_direct', 'content_rating_weighted',
                'content_topk', 'lc2c', 'lc2c_v2', 'cf_hybrid',
                'lc2cpp_zfusion', 'lc2cpp_fusion', 'lc2cpp_kernel',
                'dropoutnet']
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

        # Score functions
        sf_random = make_score_random()
        sf_content = make_score_content_direct(X_warm, S_content, warm_indices, cold_arr)
        sf_content_rw = make_score_content_rating_weighted(
            train_inters, S_content, n_users, n_items, warm_indices, cold_arr)
        sf_content_topk = make_score_content_topk(
            train_inters, S_content, n_users, n_items, warm_indices, cold_arr)
        sf_lc2c = make_score_lc2c_v1(X_warm, B_warm, item_title_emb, warm_indices, cold_arr)
        sf_lc2c_v2 = make_score_lc2c_v2(X_warm, B_warm, item_title_emb, warm_indices, cold_arr)
        sf_hybrid = make_score_cf_hybrid(sf_lc2c_v2, sf_content, alpha=0.5)
        sf_lc2cpp_zfusion = make_score_z_fusion([sf_lc2c_v2, sf_content], [0.95, 0.05])
        sf_lc2cpp_fusion = make_score_lc2cpp_fusion(sf_lc2c_v2, sf_content, sf_content_topk)
        sf_lc2cpp_kernel = make_score_lc2cpp_kernel(
            X_warm, B_warm, item_title_emb, warm_indices, cold_arr)
        sf_dropoutnet = make_score_dropoutnet(
            X_warm, B_warm, item_title_emb, warm_indices, cold_arr)

        for name, sf in zip(methods, [sf_random, sf_content, sf_content_rw,
                                        sf_content_topk, sf_lc2c, sf_lc2c_v2,
                                        sf_hybrid, sf_lc2cpp_zfusion,
                                        sf_lc2cpp_fusion, sf_lc2cpp_kernel,
                                        sf_dropoutnet]):
            r = eval_cold_item_ranking(sf, train_inters, test_inters, n_items, cold_items)
            results[name].append(r)

        print(f'  fold {fi}: ' + ' '.join(
            f'{m[:11]}={results[m][-1]["NDCG@10"]:.4f}' for m in methods))
        del B_warm, X_warm; gc.collect()

    summary = {}
    print(f'\n  === {dataset.upper()} cold-ITEM v2 5-fold means ===')
    # AUDITABLE per-test-pair records. We save for each method an array of
    # (fold_id, user_id, item_id, ndcg) tuples so a reviewer can independently
    # aggregate by user, by fold, by item, or do a clustered bootstrap.
    # This is the structure compute_significance.py needs to do per-user
    # paired Wilcoxon rather than pseudo-replicated per-pair pooling.
    per_pair_records = {}
    for m in methods:
        if not results[m]: continue
        ndcg = float(np.mean([r['NDCG@10'] for r in results[m]]))
        nstd = float(np.std([r['NDCG@10'] for r in results[m]]))
        hr = float(np.mean([r['HR@10'] for r in results[m]]))
        mrr = float(np.mean([r['MRR'] for r in results[m]]))
        summary[m] = {'NDCG@10': ndcg, 'NDCG@10_std': nstd, 'HR@10': hr, 'MRR': mrr}
        # Build (fold, user, item, ndcg) records per fold.
        records = []
        for fi_, fold_res in enumerate(results[m]):
            ndcg_arr = fold_res.get('ndcg_per_pair', [])
            users_arr = fold_res.get('user_id_per_pair', [])
            items_arr = fold_res.get('item_id_per_pair', [])
            for u, it, val in zip(users_arr, items_arr, ndcg_arr):
                records.append([fi_, u, it, val])
        per_pair_records[m] = records
        print(f'    {m:>24s}: NDCG@10={ndcg:.4f}±{nstd:.4f}  HR@10={hr:.4f}  MRR={mrr:.4f}'
              f'  (n_pairs={len(records)})')

    per_pair_path = os.path.join(
        os.path.dirname(__file__),
        f"results_cold_item_v2_perpair_{dataset}.json")
    # Structure: { "method_name": [[fold, user, item, ndcg], ...], ... }
    with open(per_pair_path, "w") as f:
        json.dump({'schema': '[[fold_id, user_id, item_id, ndcg], ...]',
                    'methods': per_pair_records}, f)
    print(f'  saved per-pair records (fold, user, item, ndcg) to '
          f'{os.path.basename(per_pair_path)} for paired-Wilcoxon downstream')
    return summary


def main():
    if len(sys.argv) > 1:
        datasets = sys.argv[1:]
    else:
        datasets = ['beauty', 'fashion', 'instruments', 'books']

    out_path = os.path.join(os.path.dirname(__file__), "results_cold_item_v2.json")
    # MERGE rather than overwrite: a single-dataset rerun should update only that
    # dataset's entry and preserve the others. (Fixes the F5 reproducibility bug
    # where `run_cold_item_v2.py beauty` silently deleted Fashion/Instruments/Books
    # from the source-of-truth JSON.)
    all_results = {}
    if os.path.exists(out_path):
        try:
            all_results = json.load(open(out_path))
        except Exception:
            all_results = {}

    for ds in datasets:
        all_results[ds] = run_cold_item_v2(ds)
        json.dump(all_results, open(out_path, "w"), indent=2,
                  default=lambda o: float(o) if hasattr(o, 'item') else str(o))

    print('\n' + '=' * 100)
    print('COLD-ITEM v2 SUMMARY: novel algorithms vs content-direct baseline')
    print('=' * 100)
    methods = ['random', 'content_direct', 'content_rating_weighted',
                'content_topk', 'lc2c', 'lc2c_v2', 'cf_hybrid',
                'lc2cpp_zfusion', 'lc2cpp_fusion', 'lc2cpp_kernel',
                'dropoutnet']
    print(f'\n{"Method":<26}', end='')
    for ds in datasets: print(f' {ds:>15}', end='')
    print()
    print('-' * (26 + 16 * len(datasets)))
    for m in methods:
        print(f'{m:<26}', end='')
        for ds in datasets:
            if m in all_results.get(ds, {}):
                v = all_results[ds][m]
                print(f' {v["NDCG@10"]:.4f}±{v.get("NDCG@10_std", 0):.3f}'.rjust(16), end='')
            else:
                print(f' {"---":>15}', end='')
        print()


if __name__ == "__main__":
    main()
