"""POC: CACR (Cross-Attention Cold-item Ranker) — a small neural model that
augments CDR's blend with a 4th signal coming from a 1-layer cross-attention
between the user's warm history and the cold item's SBERT embedding.

Why this might help where CDR-3way didn't:
  - CDR-3way's CLCRec uses InfoNCE on BPR-pretrained CF targets, which is an
    indirect optimization for ranking quality on the test metric.
  - CACR trains END-TO-END on pairwise BPR loss using warm items as
    pseudo-cold labels, with HARD NEGATIVE sampling from popularity-stratified
    pools. This directly targets the ranking objective.
  - Cross-attention captures user-item-pair-specific affinities (which warm
    history items resemble this cold item most?), going beyond the bilinear
    structure of LC2C Ridge / CLCRec.

Architecture (intentionally small — n_warm ~250-13K, must be fast):
  - User history: variable-length set of SBERT embeddings of user's training items
  - Item: cold item's SBERT embedding
  - Linear projections: SBERT (384) -> Q,K,V (d=64) using shared weights
  - Cross-attention: cold item is the query; user's items are keys/values
  - Attended user representation: sum_w softmax(Q·K^T)[w] * V[w]
  - Final score: MLP(concat([attended_user, item_query, popularity_features])) -> scalar
  - Popularity features (3-dim): log(1 + item's warm popularity), log(1 + mean
    of user's-history-items popularity), log(1 + mean of item's k=5 nearest-
    warm-neighbours popularity)

Training:
  - For each batch: sample N users; for each user sample a positive WARM item
    they interacted with and K=4 negatives (1 random, 3 from top-pop pool to
    create hard negatives).
  - Loss: pairwise BPR = -mean(log_sigmoid(score(u, +) - score(u, -)))
  - Adam lr=1e-3, batch=128, 30 epochs (small datasets train in seconds).
  - We re-encode the user's history each batch (random subsample if > 64 items)
    to avoid memory blowup.

Inference (cold items):
  - For each cold item j, compute CACR_score[u, j] using the trained model.
  - z-normalize across cold pool per user (same trick as CDR).
  - Blend in 4-way: alpha_cd * z_cd + alpha_ridge * z_lc + alpha_clcrec * z_cl + alpha_cacr * z_cacr
  - Validate (alpha_cd, alpha_ridge, alpha_clcrec, alpha_cacr) on inner-val.

Foreground execution: ~3-5 min on Beauty, ~5-10 min on Fashion/Instruments.
"""
from __future__ import annotations

import argparse
import gc
import json
import math
import os
import pickle
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from scipy.sparse import csr_matrix
from scipy.stats import wilcoxon
from sklearn.linear_model import Ridge

from ease_efficient import ease_fast
from run_cold_item import DATASET_KCORE, HP, make_item_kfold
from v5_utils import NUM_FOLDS, ROOT, TOP_K, content_sim_matrix, kcore_filter, reindex

# Reuse CLCRec utilities for the 4-way blend baseline
from run_faithful_clcrec import (
    ContentEncoder, NORMALIZE, encode_all, train_bpr, train_clcrec_encoder,
)


SEED = 20260521

# Simplex over (alpha_cd, alpha_ridge, alpha_clcrec, alpha_cacr) with sum=1
# Compact 4D grid: each coordinate in {0, 0.25, 0.5, 0.75, 1.0}
def make_simplex_4d():
    grid = []
    vals = [0.0, 0.1, 0.25, 0.4, 0.5, 0.75, 1.0]
    for a in vals:
        for b in vals:
            for c in vals:
                d = 1.0 - a - b - c
                if -1e-6 <= d <= 1.0 + 1e-6:
                    grid.append((round(a, 3), round(b, 3), round(c, 3), round(max(0.0, d), 3)))
    return sorted(set(grid))


SIMPLEX_4D = make_simplex_4d()
print(f"# 4D simplex grid has {len(SIMPLEX_4D)} weight tuples.")


def load_dataset(dataset):
    cache_dir = Path(ROOT) / "cache" / dataset
    data = pickle.load(open(cache_dir / "raw_data_dedup.pkl", "rb"))
    filtered = kcore_filter(data["interactions"], DATASET_KCORE[dataset])
    interactions, _, n_users, n_items, _ = reindex(filtered, data["item_metadata"])
    title_path = cache_dir / "v5" / f"item_title_k{DATASET_KCORE[dataset]}_dedup.pt"
    emb = torch.load(title_path, weights_only=True)
    return interactions, n_users, n_items, emb


def build_warm(train_inters, n_users, warm_indices):
    pos = {int(it): i for i, it in enumerate(warm_indices)}
    rows, cols = [], []
    for x in train_inters:
        p = pos.get(int(x["item_id"]))
        if p is None: continue
        rows.append(int(x["user_id"])); cols.append(p)
    X_sparse = csr_matrix((np.ones(len(rows), dtype=np.float32), (rows, cols)),
                           shape=(n_users, len(warm_indices)))
    return X_sparse, X_sparse.toarray().astype(np.float32)


def _z_per_user(x):
    m = x.mean(axis=1, keepdims=True)
    s = np.maximum(x.std(axis=1, keepdims=True), 1e-8)
    return (x - m) / s


# ---------------------------------------------------------------------------
# CACR: Cross-Attention Cold-item Ranker
# ---------------------------------------------------------------------------

class CACR(nn.Module):
    def __init__(self, sbert_dim=384, d=64, dropout=0.1):
        super().__init__()
        self.d = d
        # Shared QKV projection from SBERT (with separate scales)
        self.Wq = nn.Linear(sbert_dim, d, bias=False)
        self.Wk = nn.Linear(sbert_dim, d, bias=False)
        self.Wv = nn.Linear(sbert_dim, d, bias=False)
        # Final MLP head: [attended_user (d), item_query (d), popularity (3)] -> scalar
        self.head = nn.Sequential(
            nn.Linear(d + d + 3, d),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(d, 1),
        )

    def forward(self, user_hist_emb, item_emb, pop_features):
        """
        user_hist_emb: (B, L, sbert_dim)  — padded user history embeddings
        user_hist_mask: NOT used here; we assume the caller passes 0-vectors for padding
        item_emb: (B, sbert_dim)  — cold item embeddings
        pop_features: (B, 3)  — popularity features
        Returns: (B,) score
        """
        Q = self.Wq(item_emb).unsqueeze(1)         # (B, 1, d)
        K = self.Wk(user_hist_emb)                 # (B, L, d)
        V = self.Wv(user_hist_emb)                 # (B, L, d)
        # Attention scores (B, 1, L)
        attn_logits = (Q @ K.transpose(1, 2)) / math.sqrt(self.d)
        # Mask zero rows in user_hist_emb (padding)
        is_pad = (user_hist_emb.abs().sum(dim=-1, keepdim=True).squeeze(-1) < 1e-12)  # (B, L)
        attn_logits = attn_logits.masked_fill(is_pad.unsqueeze(1), -1e9)
        attn = F.softmax(attn_logits, dim=-1)      # (B, 1, L)
        attended = (attn @ V).squeeze(1)           # (B, d)
        head_in = torch.cat([attended, Q.squeeze(1), pop_features], dim=-1)
        return self.head(head_in).squeeze(-1)      # (B,)


def make_user_history_tensor(Xw_dense, sbert_warm, max_hist=64, device="cpu"):
    """For each user, compute their warm-history SBERT embeddings as a padded
    tensor of shape (n_users, max_hist, sbert_dim). If user has > max_hist items,
    randomly sub-sample (for memory)."""
    n_users, n_warm = Xw_dense.shape
    sbert_dim = sbert_warm.shape[1]
    out = np.zeros((n_users, max_hist, sbert_dim), dtype=np.float32)
    for u in range(n_users):
        hist_items = np.where(Xw_dense[u] > 0)[0]
        if len(hist_items) == 0:
            continue
        if len(hist_items) > max_hist:
            hist_items = np.random.choice(hist_items, max_hist, replace=False)
        out[u, :len(hist_items)] = sbert_warm[hist_items]
    return torch.from_numpy(out).to(device)


def compute_pop_features(Xw_dense, warm_idx, all_idx, S_content_full, k_nn=5):
    """Compute 3-dim popularity features per (user, item) — used for both
    warm (during training) and cold (at inference)."""
    n_users = Xw_dense.shape[0]
    n_all = len(all_idx)
    # warm popularity (count of user interactions per warm item)
    warm_pop = Xw_dense.sum(axis=0)                       # (n_warm,)
    log_pop = np.log1p(warm_pop)                          # (n_warm,)
    # for each all-catalog item: log1p of its OWN popularity (0 for cold)
    item_pop = np.zeros(n_all, dtype=np.float32)
    for i, idx in enumerate(warm_idx):
        item_pop[idx] = log_pop[i]
    # user's mean history-item popularity (per-user feature, same for all items)
    user_hist_pop = (Xw_dense @ log_pop) / np.maximum(Xw_dense.sum(axis=1), 1.0)  # (n_users,)
    # item's mean k-nearest-warm-neighbour popularity (per-item feature)
    S_w_all = S_content_full[np.ix_(warm_idx, np.arange(n_all))]                # (n_warm, n_all)
    top_k_indices = np.argpartition(-S_w_all, k_nn, axis=0)[:k_nn]                # (k_nn, n_all)
    item_nn_pop = log_pop[top_k_indices].mean(axis=0).astype(np.float32)         # (n_all,)
    return item_pop, user_hist_pop.astype(np.float32), item_nn_pop


def train_cacr(Xw_dense, warm_idx, sbert_full, S_content_full, n_users, n_items,
                seed, n_epochs=30, batch_size=128, lr=1e-3, max_hist=64,
                n_neg=4, device="cuda" if torch.cuda.is_available() else "cpu"):
    """Train CACR via pairwise BPR on warm items as pseudo-cold labels."""
    torch.manual_seed(seed); np.random.seed(seed)

    sbert_warm = sbert_full[warm_idx]
    user_hist = make_user_history_tensor(Xw_dense, sbert_warm, max_hist=max_hist, device=device)
    sbert_full_t = torch.from_numpy(sbert_full).to(device)

    # Popularity features
    item_pop, user_hist_pop, item_nn_pop = compute_pop_features(
        Xw_dense, warm_idx, np.arange(n_items), S_content_full, k_nn=5)
    item_pop_t = torch.from_numpy(item_pop).to(device)
    user_hist_pop_t = torch.from_numpy(user_hist_pop).to(device)
    item_nn_pop_t = torch.from_numpy(item_nn_pop).to(device)

    # Build training positives: (user, item) pairs from Xw_dense
    pos_users, pos_warm_cols = np.where(Xw_dense > 0)   # arrays of indices
    pos_items_full = warm_idx[pos_warm_cols]
    n_pos = len(pos_users)
    print(f"    CACR train: {n_pos} positive (user, warm-item) pairs on {n_users} users")

    # Warm-item popularity for hard-neg sampling
    warm_pop_full = np.zeros(n_items, dtype=np.float32)
    warm_pop_full[warm_idx] = Xw_dense.sum(axis=0)
    # Top-50% popular warm items make the hard-neg pool
    pop_threshold = np.percentile(warm_pop_full[warm_idx], 50)
    hard_neg_pool = warm_idx[warm_pop_full[warm_idx] >= pop_threshold]

    model = CACR(sbert_dim=sbert_full.shape[1], d=64, dropout=0.1).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=lr)

    rng = np.random.RandomState(seed)
    for epoch in range(n_epochs):
        perm = rng.permutation(n_pos)
        losses = []
        for batch_start in range(0, n_pos, batch_size):
            batch_idx = perm[batch_start:batch_start + batch_size]
            u_batch = pos_users[batch_idx]
            jpos_batch = pos_items_full[batch_idx]
            # Sample n_neg negatives per (u, jpos): mix of random (n_neg-2) and hard (2)
            jneg_batch = np.empty((len(batch_idx), n_neg), dtype=np.int64)
            for i, (u, jp) in enumerate(zip(u_batch, jpos_batch)):
                seen_warm_cols = set(np.where(Xw_dense[u] > 0)[0].tolist())
                seen_full = set(warm_idx[list(seen_warm_cols)].tolist())
                # random negatives
                tries = 0
                negs = []
                while len(negs) < n_neg and tries < n_neg * 10:
                    if len(negs) < n_neg - 2:
                        cand = int(warm_idx[rng.randint(0, len(warm_idx))])
                    else:
                        cand = int(hard_neg_pool[rng.randint(0, len(hard_neg_pool))])
                    if cand not in seen_full and cand != int(jp):
                        negs.append(cand)
                    tries += 1
                while len(negs) < n_neg:
                    negs.append(int(warm_idx[rng.randint(0, len(warm_idx))]))
                jneg_batch[i] = negs

            # Build tensors
            # User histories (shared across pos and neg)
            hist_b = user_hist[u_batch]                                     # (B, L, d_s)
            user_pop_b = user_hist_pop_t[u_batch]                           # (B,)

            # Positive score
            pos_emb = sbert_full_t[jpos_batch]                              # (B, d_s)
            pop_feat_pos = torch.stack([
                item_pop_t[jpos_batch], user_pop_b, item_nn_pop_t[jpos_batch]
            ], dim=-1)                                                       # (B, 3)
            s_pos = model(hist_b, pos_emb, pop_feat_pos)                    # (B,)

            # Negative scores
            B = hist_b.shape[0]
            hist_neg_b = hist_b.unsqueeze(1).expand(-1, n_neg, -1, -1).reshape(B*n_neg, hist_b.shape[1], hist_b.shape[2])
            user_pop_neg_b = user_pop_b.unsqueeze(1).expand(-1, n_neg).reshape(-1)
            jneg_flat = torch.from_numpy(jneg_batch.flatten()).to(device).long()
            neg_emb = sbert_full_t[jneg_flat]
            pop_feat_neg = torch.stack([
                item_pop_t[jneg_flat], user_pop_neg_b, item_nn_pop_t[jneg_flat]
            ], dim=-1)
            s_neg = model(hist_neg_b, neg_emb, pop_feat_neg).reshape(B, n_neg)  # (B, n_neg)

            # Pairwise BPR loss
            diffs = s_pos.unsqueeze(1) - s_neg                              # (B, n_neg)
            loss = -F.logsigmoid(diffs).mean()
            opt.zero_grad(); loss.backward(); opt.step()
            losses.append(loss.item())
        if (epoch + 1) % 10 == 0:
            print(f"    epoch {epoch+1}/{n_epochs}  loss={np.mean(losses):.4f}")
    return model, item_pop, user_hist_pop, item_nn_pop


def cacr_score_cold(model, Xw_dense, warm_idx, cold_idx, sbert_full, n_items,
                     item_pop, user_hist_pop, item_nn_pop, max_hist=64,
                     device="cuda" if torch.cuda.is_available() else "cpu",
                     batch_users=64):
    """Compute CACR scores for all (user, cold_item) pairs."""
    model.eval()
    n_users = Xw_dense.shape[0]
    n_cold = len(cold_idx)

    sbert_warm = sbert_full[warm_idx]
    user_hist = make_user_history_tensor(Xw_dense, sbert_warm, max_hist=max_hist, device=device)
    sbert_full_t = torch.from_numpy(sbert_full).to(device)

    item_pop_t = torch.from_numpy(item_pop).to(device)
    user_hist_pop_t = torch.from_numpy(user_hist_pop).to(device)
    item_nn_pop_t = torch.from_numpy(item_nn_pop).to(device)

    cold_idx_t = torch.from_numpy(cold_idx).to(device).long()
    cold_emb = sbert_full_t[cold_idx_t]                                      # (n_cold, d_s)
    cold_item_pop = item_pop_t[cold_idx_t]                                   # (n_cold,)
    cold_item_nn_pop = item_nn_pop_t[cold_idx_t]                             # (n_cold,)

    scores = np.zeros((n_users, n_cold), dtype=np.float32)
    with torch.no_grad():
        for u_start in range(0, n_users, batch_users):
            ub = slice(u_start, u_start + batch_users)
            hist_b = user_hist[ub]                                           # (Bu, L, d_s)
            uph_b = user_hist_pop_t[u_start:u_start + batch_users]           # (Bu,)
            Bu = hist_b.shape[0]
            # Expand history over n_cold items
            hist_exp = hist_b.unsqueeze(1).expand(-1, n_cold, -1, -1).reshape(Bu * n_cold, hist_b.shape[1], hist_b.shape[2])
            uph_exp = uph_b.unsqueeze(1).expand(-1, n_cold).reshape(-1)
            cold_emb_exp = cold_emb.unsqueeze(0).expand(Bu, -1, -1).reshape(Bu * n_cold, -1)
            cold_pop_exp = cold_item_pop.unsqueeze(0).expand(Bu, -1).reshape(-1)
            cold_nn_pop_exp = cold_item_nn_pop.unsqueeze(0).expand(Bu, -1).reshape(-1)
            pop_feat = torch.stack([cold_pop_exp, uph_exp, cold_nn_pop_exp], dim=-1)
            s = model(hist_exp, cold_emb_exp, pop_feat).reshape(Bu, n_cold)
            scores[u_start:u_start + Bu] = s.cpu().numpy()
    return scores


# ---------------------------------------------------------------------------
# 4-way blend scorer (content + Ridge + CLCRec + CACR)
# ---------------------------------------------------------------------------

def make_score_4way(Xw, B_warm, warm_indices, cold_indices, S_content,
                     emb_np, U_cf, V_warm_cf, model_clcrec, cacr_scores,
                     n_items, alpha_cd, alpha_ridge, alpha_clcrec, alpha_cacr):
    """4-way blend: alpha_cd*z(content) + alpha_ridge*z(Ridge) + alpha_clcrec*z(CLCRec) + alpha_cacr*z(CACR)"""
    SBERT_w = emb_np[warm_indices].astype(np.float32)
    SBERT_c = emb_np[cold_indices].astype(np.float32)

    # content_direct
    S_w_c = S_content[np.ix_(warm_indices, cold_indices)].astype(np.float32)

    # LC2C Ridge
    reg = Ridge(alpha=1.0); reg.fit(SBERT_w, B_warm.T.astype(np.float32))
    B_hat_cold = (SBERT_c @ reg.coef_.T.astype(np.float32)).T.astype(np.float32)

    # CLCRec
    with torch.no_grad():
        V_cold_cl = encode_all(model_clcrec, SBERT_c)
    if NORMALIZE:
        norms = np.linalg.norm(V_cold_cl, axis=1, keepdims=True)
        V_cold_cl = V_cold_cl / np.maximum(norms, 1e-12)

    def f(uids):
        warm_scores = Xw[uids] @ B_warm
        cd_cold = _z_per_user(Xw[uids] @ S_w_c)
        lc_cold = _z_per_user(Xw[uids] @ B_hat_cold)
        cl_cold = _z_per_user(U_cf[uids] @ V_cold_cl.T)
        cacr_cold = _z_per_user(cacr_scores[uids])
        cold_blend = (alpha_cd * cd_cold + alpha_ridge * lc_cold +
                       alpha_clcrec * cl_cold + alpha_cacr * cacr_cold)
        out = np.empty((len(uids), n_items), dtype=np.float32)
        out[:, warm_indices] = warm_scores
        out[:, cold_indices] = cold_blend
        return out
    return f


def eval_full(score_fn, train_inters, test_inters, n_items, batch_size=192):
    ut = defaultdict(set); uts = defaultdict(list)
    for x in train_inters: ut[int(x["user_id"])].add(int(x["item_id"]))
    for x in test_inters: uts[int(x["user_id"])].append(int(x["item_id"]))
    users = sorted(u for u in uts if uts[u] and ut[u])
    ndcg, per_user_ndcg = [], defaultdict(list)
    for s in range(0, len(users), batch_size):
        batch = users[s:s + batch_size]
        scores = score_fn(np.array(batch, dtype=np.int32)).astype(np.float32, copy=True)
        for k, u in enumerate(batch):
            if ut[u]:
                scores[k, list(ut[u])] = -np.inf
            for tgt in uts[u]:
                ts = scores[k, tgt]
                r0 = int((scores[k] > ts).sum())
                n_ = 1.0 / math.log2(r0 + 2) if r0 < TOP_K else 0.0
                ndcg.append(n_); per_user_ndcg[int(u)].append(n_)
    return float(np.mean(ndcg)) if ndcg else 0.0, {u: float(np.mean(vs)) for u, vs in per_user_ndcg.items()}


def select_4way(dataset, outer_train, outer_cold_items, S_content, emb_np,
                  n_users, n_items, rng, bpr_epochs=40, tau=0.2, lr=1e-3, hidden=128,
                  cacr_epochs=30, cacr_lr=1e-3):
    outer_warm = sorted(set(range(n_items)) - set(outer_cold_items))
    shuf = np.array(outer_warm, dtype=np.int32); rng.shuffle(shuf)
    n_val = max(1, int(0.2 * len(shuf)))
    val_items = set(shuf[:n_val].tolist())
    val_inters = [x for x in outer_train if int(x["item_id"]) in val_items]
    if not val_inters: return (0.25, 0.5, 0.15, 0.10)
    inner_cold = sorted(set(outer_cold_items) | val_items)
    inner_warm = np.array(sorted(set(range(n_items)) - set(inner_cold)), dtype=np.int32)
    inner_train = [x for x in outer_train if int(x["item_id"]) not in val_items]
    X_in, Xw_in = build_warm(inner_train, n_users, inner_warm)
    S_warm_in = S_content[np.ix_(inner_warm, inner_warm)]
    lam, beta = HP[dataset]
    B_in = ease_fast(X_in, lam=lam, beta=beta, S_content=S_warm_in, dtype=np.float32)
    inner_seed = int(rng.randint(0, 2**31 - 1))
    U_inner, V_warm_inner, _ = train_bpr(inner_train, inner_warm, n_users, inner_seed,
                                          n_epochs=bpr_epochs)
    model_inner, _ = train_clcrec_encoder(emb_np[inner_warm], V_warm_inner, inner_seed,
                                            tau=tau, lr=lr, hidden=hidden)
    cacr_inner, ip, uhp, inp = train_cacr(Xw_in, inner_warm, emb_np, S_content, n_users, n_items,
                                            inner_seed, n_epochs=cacr_epochs, lr=cacr_lr)
    cold_arr = np.array(sorted(inner_cold), dtype=np.int32)
    cacr_scores_inner = cacr_score_cold(cacr_inner, Xw_in, inner_warm, cold_arr, emb_np,
                                          n_items, ip, uhp, inp)
    # cacr_scores_inner shape: (n_users, n_cold_inner), aligned with cold_arr indices into Xw_in
    # But the make_score_4way expects cacr_scores indexed by user only; cold dim is len(cold_indices)
    # Re-arrange so cacr_scores[u] aligns with cold_arr order.
    scores = {}
    for (a_cd, a_r, a_cl, a_ca) in SIMPLEX_4D:
        sf = make_score_4way(Xw_in, B_in, inner_warm, cold_arr, S_content, emb_np,
                               U_inner, V_warm_inner, model_inner, cacr_scores_inner,
                               n_items, alpha_cd=a_cd, alpha_ridge=a_r,
                               alpha_clcrec=a_cl, alpha_cacr=a_ca)
        m, _ = eval_full(sf, inner_train, val_inters, n_items)
        scores[(a_cd, a_r, a_cl, a_ca)] = m
    del X_in, Xw_in, B_in, U_inner, V_warm_inner, model_inner, cacr_inner; gc.collect()
    if torch.cuda.is_available(): torch.cuda.empty_cache()
    return max(scores, key=scores.get)


def run(dataset, seeds, bpr_epochs=40, tau=0.2, lr=1e-3, hidden=128,
         cacr_epochs=30, cacr_lr=1e-3):
    print(f"\n{'#'*70}\n# CACR POC: {dataset.upper()}\n{'#'*70}")
    interactions, n_users, n_items, item_title_emb = load_dataset(dataset)
    emb_np = item_title_emb.cpu().numpy().astype(np.float32) if hasattr(item_title_emb, "cpu") else np.asarray(item_title_emb, dtype=np.float32)
    S_content = content_sim_matrix(item_title_emb, dtype=np.float32)
    lam, beta = HP[dataset]
    k = DATASET_KCORE[dataset]
    print(f"  n_users={n_users:,}  n_items={n_items:,}  k={k}  lambda={lam}  beta={beta}")

    perfold_4way = []
    perfold_cdr = []
    per_user_4way = defaultdict(list)
    per_user_cdr = defaultdict(list)
    selected = []

    for seed in seeds:
        splits = make_item_kfold(interactions, n_items, n_splits=NUM_FOLDS, seed=seed)
        for fold_id, (tr, te, cold) in enumerate(splits):
            t0 = time.time()
            train_inters = [interactions[i] for i in tr]
            test_inters = [interactions[i] for i in te]
            warm_idx = np.array(sorted(set(range(n_items)) - set(cold)), dtype=np.int32)
            cold_idx = np.array(sorted(cold), dtype=np.int32)
            X_sparse, Xw = build_warm(train_inters, n_users, warm_idx)
            S_warm = S_content[np.ix_(warm_idx, warm_idx)]
            B_warm = ease_fast(X_sparse, lam=lam, beta=beta, S_content=S_warm, dtype=np.float32)

            # Train outer BPR + CLCRec + CACR
            U_out, V_warm_out, _ = train_bpr(train_inters, warm_idx, n_users, seed,
                                                n_epochs=bpr_epochs)
            model_clcrec_out, _ = train_clcrec_encoder(emb_np[warm_idx], V_warm_out, seed,
                                                          tau=tau, lr=lr, hidden=hidden)
            print(f"  seed={seed} fold={fold_id}  training CACR ({cacr_epochs} epochs)...")
            cacr_model, ip, uhp, inp = train_cacr(Xw, warm_idx, emb_np, S_content, n_users, n_items,
                                                    seed, n_epochs=cacr_epochs, lr=cacr_lr)
            cacr_scores = cacr_score_cold(cacr_model, Xw, warm_idx, cold_idx, emb_np,
                                            n_items, ip, uhp, inp)

            # Inner validation: choose 4-way simplex
            val_rng = np.random.RandomState((seed * 1000 + fold_id + 7) & 0xFFFFFFFF)
            best = select_4way(dataset, train_inters, set(cold), S_content, emb_np,
                                 n_users, n_items, val_rng,
                                 bpr_epochs=bpr_epochs, tau=tau, lr=lr, hidden=hidden,
                                 cacr_epochs=cacr_epochs, cacr_lr=cacr_lr)
            selected.append({"seed": seed, "fold_id": fold_id, "chosen_simplex": best})

            # Final 4-way score
            sf_4 = make_score_4way(Xw, B_warm, warm_idx, cold_idx, S_content, emb_np,
                                     U_out, V_warm_out, model_clcrec_out, cacr_scores,
                                     n_items, alpha_cd=best[0], alpha_ridge=best[1],
                                     alpha_clcrec=best[2], alpha_cacr=best[3])
            m_4, pu_4 = eval_full(sf_4, train_inters, test_inters, n_items)
            perfold_4way.append(m_4)
            for u, v in pu_4.items(): per_user_4way[u].append(v)

            # CDR_validated baseline (alpha_cd=0.25, alpha_ridge=0.75, others=0)
            sf_cdr = make_score_4way(Xw, B_warm, warm_idx, cold_idx, S_content, emb_np,
                                       U_out, V_warm_out, model_clcrec_out, cacr_scores,
                                       n_items, alpha_cd=0.25, alpha_ridge=0.75,
                                       alpha_clcrec=0.0, alpha_cacr=0.0)
            m_cdr, pu_cdr = eval_full(sf_cdr, train_inters, test_inters, n_items)
            perfold_cdr.append(m_cdr)
            for u, v in pu_cdr.items(): per_user_cdr[u].append(v)

            print(f"  seed={seed} fold={fold_id}  CDR={m_cdr:.4f}  "
                  f"4way{best}={m_4:.4f}  delta={m_4-m_cdr:+.4f}  [fold {time.time()-t0:.1f}s]")
            del X_sparse, Xw, B_warm, S_warm, U_out, V_warm_out, model_clcrec_out, cacr_model
            gc.collect()
            if torch.cuda.is_available(): torch.cuda.empty_cache()

    print(f"\n=== {dataset.upper()} fold means (NDCG@10) ===")
    print(f"  CDR_validated:    {np.mean(perfold_cdr):.4f} +/- {np.std(perfold_cdr):.4f}")
    print(f"  CDR-4way(CACR):   {np.mean(perfold_4way):.4f} +/- {np.std(perfold_4way):.4f}  delta={np.mean(perfold_4way)-np.mean(perfold_cdr):+.4f}")

    pu_4 = {u: float(np.mean(vs)) for u, vs in per_user_4way.items()}
    pu_c = {u: float(np.mean(vs)) for u, vs in per_user_cdr.items()}
    common = sorted(set(pu_4) & set(pu_c))
    diffs = np.array([pu_4[u] - pu_c[u] for u in common])
    if np.allclose(diffs, 0): p = 1.0
    else: p = float(wilcoxon(diffs, alternative='greater', zero_method='wilcox').pvalue)
    marker = '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else 'n.s.'
    print(f"\n=== Per-USER Wilcoxon (CDR-4way > CDR_validated) ===")
    print(f"  n={len(common)} delta_mean={diffs.mean():+.4f} p={p:.3e} {marker}")
    print(f"\n=== Chosen simplex per fold (alpha_cd, alpha_ridge, alpha_clcrec, alpha_cacr) ===")
    for s in selected:
        print(f"  seed={s['seed']} fold={s['fold_id']}: {s['chosen_simplex']}")

    return {
        "perfold_4way": list(map(float, perfold_4way)),
        "perfold_cdr": list(map(float, perfold_cdr)),
        "wilcoxon": {"n_users": len(common), "delta_mean": float(diffs.mean()),
                       "p_one_sided_greater": p, "marker": marker},
        "selected_simplex": selected,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("datasets", nargs="*", default=["beauty"])
    ap.add_argument("--seeds", default=str(SEED))
    ap.add_argument("--bpr-epochs", type=int, default=40)
    ap.add_argument("--cacr-epochs", type=int, default=30)
    ap.add_argument("--out", default="results_cacr_poc.json")
    args = ap.parse_args()
    seeds = [int(s) for s in args.seeds.split(",")]
    out_path = Path(__file__).parent / args.out
    payload = {"schema_version": 1, "candidate_scope": "full_catalog",
                "candidate_method": "CDR-4way + CACR (content + Ridge + CLCRec + cross-attention)",
                "baseline_method": "CDR_validated",
                "seeds": seeds, "config": {"bpr_epochs": args.bpr_epochs,
                                              "cacr_epochs": args.cacr_epochs},
                "datasets": {}}
    for ds in args.datasets:
        payload["datasets"][ds] = run(ds, seeds, bpr_epochs=args.bpr_epochs,
                                         cacr_epochs=args.cacr_epochs)
        with out_path.open("w") as f:
            json.dump(payload, f, indent=2,
                       default=lambda o: float(o) if hasattr(o, "item") else str(o))
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()
