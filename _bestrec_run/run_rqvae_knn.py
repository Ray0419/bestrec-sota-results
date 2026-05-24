"""TIGER-inspired closed-form proxy: RQ-VAE semantic-ID kNN retrieval.

This is NOT a faithful TIGER/LIGER reproduction. It implements the
"minimum-viable closed-form proxy" from RESEARCH_TIGER_LIGER.md section 4:

    1. Train an RQ-VAE on SBERT title embeddings (warm-only).
    2. Quantize every item (warm + cold) to an L-token semantic ID.
    3. Build an item-item similarity S_semantic from the semantic IDs
       (one of: Hamming on codes, cosine on reconstruction, cosine on
       quantized continuous vector). Best option selected on inner val.
    4. Score cold (and warm) items as
            score(u, j) = sum_{w in user_history} S_semantic[w, j]
       (same shape as content_direct).

This isolates the "semantic-ID content prior" without an autoregressive
Transformer. It is a TIGER-INSPIRED PROXY, defensibly cited in the strict
pipeline's baseline audit as
    fidelity: rqvae_semantic_id_knn_proxy_not_official_tiger_or_liger.

Usage:
    _bestrec_run/.venv/Scripts/python _bestrec_run/run_rqvae_knn.py \
        beauty fashion instruments books --seeds 20260521,20260522,20260523

References:
- Rajput et al., NeurIPS 2023, "Recommender Systems with Generative Retrieval"
- Yang et al., 2024, "Unifying Generative and Dense Retrieval for Sequential Recommendation" (LIGER)
- RESEARCH_TIGER_LIGER.md (research recommendation that produced this proxy)
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

from run_cold_item import DATASET_KCORE, make_item_kfold
from v5_utils import NUM_FOLDS, ROOT, TOP_K, kcore_filter, reindex


# ---------- Hyperparameter grids ----------
HP_GRID = {
    "L": [2, 4, 6],
    "codebook_size": [128, 256],
    "commitment_cost": [0.1, 0.25],
    "sim_option": ["A_hamming", "B_recon_cos", "C_quant_cos"],
}
# Reduced grid for compute-bound datasets (instruments, books).
# Justification: on Beauty+Fashion POC, 23/30 folds independently selected
# (L=2, codebook_size in {128,256}, sim=A_hamming). We narrow to that family
# rather than the full 36-cell grid (3*2*2*3) so the inner-val sweep fits
# the < 2hr compute budget for the larger Amazon datasets.
HP_GRID_REDUCED = {
    "L": [2, 4],
    "codebook_size": [128, 256],
    "commitment_cost": [0.1, 0.25],
    "sim_option": ["A_hamming", "C_quant_cos"],
}
DEFAULT_HP = {"L": 2, "codebook_size": 256, "commitment_cost": 0.1, "sim_option": "A_hamming"}

# Training schedule
N_EPOCHS = {"beauty": 400, "fashion": 400, "instruments": 250, "books": 200}
HP_EPOCHS = 150  # epochs for inner HP sweep models (kept short for speed)
LR = 1e-3
LATENT_DIM = 128
HIDDEN_DIM = 256
EMA_DECAY = 0.99
DEAD_CODE_THRESHOLD = 100  # steps with zero usage before a codeword is reset

DEFAULT_SEEDS = [20260521, 20260522, 20260523]


# =====================================================================
# RQ-VAE model with EMA codebook + straight-through estimator
# =====================================================================
class EMAVectorQuantizer(nn.Module):
    """Single codebook with EMA-based updates and dead-code resets.

    Implements the standard VQ-VAE EMA update (Roy et al., 2018; Razavi et
    al., 2019). Each forward returns (quantized, indices, commitment_loss).
    The encoder commit loss is returned so the outer module can scale it.
    """

    def __init__(self, num_codes: int, dim: int, decay: float = EMA_DECAY, eps: float = 1e-5):
        super().__init__()
        self.num_codes = num_codes
        self.dim = dim
        self.decay = decay
        self.eps = eps
        embed = torch.randn(num_codes, dim) * 0.02
        self.register_buffer("embedding", embed)
        self.register_buffer("cluster_size", torch.zeros(num_codes))
        self.register_buffer("embed_avg", embed.clone())
        self.register_buffer("dead_steps", torch.zeros(num_codes, dtype=torch.long))

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        # x: (B, dim)
        # nearest neighbour by squared L2
        # dist[b, k] = ||x_b||^2 - 2 x_b . e_k + ||e_k||^2
        x2 = (x * x).sum(dim=-1, keepdim=True)
        e2 = (self.embedding * self.embedding).sum(dim=-1)
        dist = x2 - 2.0 * (x @ self.embedding.t()) + e2.unsqueeze(0)
        indices = dist.argmin(dim=-1)
        quantized = self.embedding[indices]

        # commitment loss: encoder should match codebook (codebook is updated via EMA, not gradient)
        commit_loss = F.mse_loss(x, quantized.detach())

        if self.training:
            with torch.no_grad():
                # one-hot of indices
                onehot = F.one_hot(indices, self.num_codes).type(x.dtype)
                cluster_now = onehot.sum(dim=0)
                # EMA cluster sizes
                self.cluster_size.mul_(self.decay).add_(cluster_now, alpha=1.0 - self.decay)
                # EMA accumulated embedding sums
                ema_sum = onehot.t() @ x
                self.embed_avg.mul_(self.decay).add_(ema_sum, alpha=1.0 - self.decay)
                # normalize, with Laplace-smoothing for empty codes
                n = self.cluster_size.sum()
                cluster = (self.cluster_size + self.eps) / (n + self.num_codes * self.eps) * n
                self.embedding.copy_(self.embed_avg / cluster.unsqueeze(-1))
                # track dead codes
                used = cluster_now > 0
                self.dead_steps = torch.where(used, torch.zeros_like(self.dead_steps), self.dead_steps + 1)

        # straight-through: pass gradient from quantized to x
        quantized_st = x + (quantized - x).detach()
        return quantized_st, indices, commit_loss

    @torch.no_grad()
    def reset_dead(self, x_pool: torch.Tensor):
        """Reset codewords that have been unused for > DEAD_CODE_THRESHOLD
        steps to random samples from x_pool."""
        dead_mask = self.dead_steps > DEAD_CODE_THRESHOLD
        n_dead = int(dead_mask.sum().item())
        if n_dead == 0:
            return 0
        idx = torch.randint(0, x_pool.shape[0], (n_dead,), device=x_pool.device)
        self.embedding[dead_mask] = x_pool[idx]
        self.embed_avg[dead_mask] = x_pool[idx]
        self.cluster_size[dead_mask] = 1.0
        self.dead_steps[dead_mask] = 0
        return n_dead


class RQVAE(nn.Module):
    """Residual-Quantized VAE.

    Encoder: 2-layer MLP (input -> hidden -> latent).
    Bottleneck: L residual VQ layers, each with `num_codes` codewords of `latent` dim.
    Decoder: 2-layer MLP (latent -> hidden -> input).
    """

    def __init__(self, input_dim: int, latent_dim: int = LATENT_DIM, hidden_dim: int = HIDDEN_DIM,
                 num_layers: int = 4, num_codes: int = 256, commitment_cost: float = 0.25):
        super().__init__()
        self.num_layers = num_layers
        self.num_codes = num_codes
        self.latent_dim = latent_dim
        self.commitment_cost = commitment_cost
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim), nn.ReLU(),
            nn.Linear(hidden_dim, latent_dim),
        )
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, hidden_dim), nn.ReLU(),
            nn.Linear(hidden_dim, input_dim),
        )
        self.quantizers = nn.ModuleList(
            [EMAVectorQuantizer(num_codes, latent_dim) for _ in range(num_layers)]
        )

    def encode_and_quantize(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Returns (quantized_st, indices LxB, total_commit_loss)."""
        z = self.encoder(x)
        residual = z
        sum_q = torch.zeros_like(z)
        sum_q_st = torch.zeros_like(z)
        all_idx = []
        commit_total = z.new_zeros(())
        for q in self.quantizers:
            q_st, idx, c_loss = q(residual)
            # The actual codeword is q_st minus the straight-through copy bit; we need
            # the gradient-detached codeword to update the residual:
            q_detached = q_st.detach()  # this is just the codebook vector
            sum_q = sum_q + q_detached
            sum_q_st = sum_q_st + q_st
            residual = residual - q_detached
            all_idx.append(idx)
            commit_total = commit_total + c_loss
        indices = torch.stack(all_idx, dim=0)  # (L, B)
        return sum_q_st, indices, commit_total

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        sum_q_st, indices, commit_total = self.encode_and_quantize(x)
        x_hat = self.decoder(sum_q_st)
        return x_hat, indices, commit_total

    @torch.no_grad()
    def quantize_to_codes(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Eval-time: return (L, N) int codes, (N, latent) quantized sum, (N, input_dim) reconstruction."""
        was_training = self.training
        self.eval()
        z = self.encoder(x)
        residual = z
        sum_q = torch.zeros_like(z)
        all_idx = []
        for q in self.quantizers:
            x2 = (residual * residual).sum(dim=-1, keepdim=True)
            e2 = (q.embedding * q.embedding).sum(dim=-1)
            dist = x2 - 2.0 * (residual @ q.embedding.t()) + e2.unsqueeze(0)
            idx = dist.argmin(dim=-1)
            qv = q.embedding[idx]
            sum_q = sum_q + qv
            residual = residual - qv
            all_idx.append(idx)
        indices = torch.stack(all_idx, dim=0)
        recon = self.decoder(sum_q)
        if was_training:
            self.train()
        return indices, sum_q, recon


def train_rqvae(emb_warm: np.ndarray, *, L: int, num_codes: int, commitment_cost: float,
                 n_epochs: int, lr: float, batch_size: int, seed: int, device: torch.device,
                 verbose: bool = False) -> tuple[RQVAE, dict]:
    """Train an RQ-VAE on the warm SBERT embeddings.

    Returns the trained model and a dict of training diagnostics.
    """
    seed32 = int(seed) & 0xFFFFFFFF
    torch.manual_seed(seed32)
    np.random.seed(seed32)
    model = RQVAE(input_dim=emb_warm.shape[1], num_layers=L, num_codes=num_codes,
                   commitment_cost=commitment_cost).to(device)
    optim = torch.optim.Adam(model.parameters(), lr=lr)
    X = torch.from_numpy(emb_warm.astype(np.float32)).to(device)
    N = X.shape[0]
    bs = min(batch_size, max(64, N))
    diag = {"final_recon": None, "final_commit": None, "dead_resets": 0, "uniqueness": None}
    model.train()
    for epoch in range(n_epochs):
        perm = torch.randperm(N, device=device)
        epoch_recon, epoch_commit, n_batches = 0.0, 0.0, 0
        for s in range(0, N, bs):
            batch_idx = perm[s:s + bs]
            xb = X[batch_idx]
            x_hat, _, commit = model(xb)
            recon = F.mse_loss(x_hat, xb)
            loss = recon + commitment_cost * commit
            optim.zero_grad()
            loss.backward()
            optim.step()
            epoch_recon += float(recon.item())
            epoch_commit += float(commit.item())
            n_batches += 1
        # dead-code reset using current encoder output as pool
        if (epoch + 1) % 20 == 0:
            with torch.no_grad():
                z = model.encoder(X)
                resid = z.clone()
                resets_this = 0
                for q in model.quantizers:
                    resets_this += q.reset_dead(resid)
                    # nearest codeword to maintain residual semantics
                    x2 = (resid * resid).sum(dim=-1, keepdim=True)
                    e2 = (q.embedding * q.embedding).sum(dim=-1)
                    dist = x2 - 2.0 * (resid @ q.embedding.t()) + e2.unsqueeze(0)
                    idx = dist.argmin(dim=-1)
                    resid = resid - q.embedding[idx]
                diag["dead_resets"] += resets_this
        if verbose and (epoch + 1) % 50 == 0:
            print(f"      epoch {epoch+1:3d} recon={epoch_recon/n_batches:.4f} "
                  f"commit={epoch_commit/n_batches:.4f}")
        diag["final_recon"] = epoch_recon / max(n_batches, 1)
        diag["final_commit"] = epoch_commit / max(n_batches, 1)
    # uniqueness: how many distinct semantic IDs in the warm set
    with torch.no_grad():
        idx, _, _ = model.quantize_to_codes(X)
        # idx: (L, N) -> per-column tuple is the semantic id
        codes = idx.t().cpu().numpy()
        tuples = {tuple(row.tolist()) for row in codes}
        diag["uniqueness"] = float(len(tuples) / N)
    return model, diag


# =====================================================================
# Semantic-ID similarity matrices
# =====================================================================
def build_semantic_sim(codes: np.ndarray, quant_vec: np.ndarray, recon: np.ndarray,
                        option: str, batch: int = 512) -> np.ndarray:
    """Build N x N similarity from semantic IDs.

    codes: (N, L) int.  quant_vec: (N, latent) float.  recon: (N, input_dim) float.
    option in {"A_hamming", "B_recon_cos", "C_quant_cos"}.
    Diagonal is zeroed (so self-sim doesn't trivially dominate).
    """
    N = codes.shape[0]
    if option == "A_hamming":
        # match-count similarity / L
        # vectorized: S[i, j] = sum_l (codes[i, l] == codes[j, l]) / L
        L = codes.shape[1]
        S = np.zeros((N, N), dtype=np.float32)
        for l in range(L):
            col = codes[:, l]
            # equality matrix via broadcasting
            eq = (col[:, None] == col[None, :])
            S += eq.astype(np.float32)
        S /= float(L)
        np.fill_diagonal(S, 0.0)
        return S
    if option == "B_recon_cos":
        x = recon.astype(np.float32)
        norms = np.linalg.norm(x, axis=1, keepdims=True) + 1e-12
        xn = x / norms
        S = xn @ xn.T
        np.fill_diagonal(S, 0.0)
        return S.astype(np.float32)
    if option == "C_quant_cos":
        x = quant_vec.astype(np.float32)
        norms = np.linalg.norm(x, axis=1, keepdims=True) + 1e-12
        xn = x / norms
        S = xn @ xn.T
        np.fill_diagonal(S, 0.0)
        return S.astype(np.float32)
    raise ValueError(f"Unknown sim option {option}")


# =====================================================================
# Scoring function: TIGER-inspired retrieval against full catalog
# =====================================================================
def make_score_rqvae(Xw_warm: np.ndarray, warm_indices: np.ndarray,
                      S_semantic: np.ndarray) -> "Callable[[np.ndarray], np.ndarray]":
    """score(u, j) = sum_{w in user_history} S_semantic[w, j] for all j.

    Mirrors content_direct: Xw_warm @ S_semantic[warm_indices, :].
    The same semantic similarity is used for warm and cold items, so this is
    an honest TIGER-style retrieval comparator without an EASE warm head.
    """
    S_w_all = S_semantic[warm_indices, :].astype(np.float32)

    def score(user_ids: np.ndarray) -> np.ndarray:
        return Xw_warm[user_ids] @ S_w_all

    return score


# =====================================================================
# Data loading
# =====================================================================
def load_dataset(dataset: str):
    cache_dir = Path(ROOT) / "cache" / dataset
    data = pickle.load(open(cache_dir / "raw_data_dedup.pkl", "rb"))
    filtered = kcore_filter(data["interactions"], DATASET_KCORE[dataset])
    interactions, _, n_users, n_items, _ = reindex(filtered, data["item_metadata"])
    title_path = cache_dir / "v5" / f"item_title_k{DATASET_KCORE[dataset]}_dedup.pt"
    emb = torch.load(title_path, weights_only=True)
    emb_np = emb.cpu().numpy().astype(np.float32) if hasattr(emb, "cpu") else np.asarray(emb, dtype=np.float32)
    return interactions, n_users, n_items, emb_np


def build_warm(train_inters, n_users, warm_indices):
    pos = {int(it): i for i, it in enumerate(warm_indices)}
    rows, cols = [], []
    for x in train_inters:
        p = pos.get(int(x["item_id"]))
        if p is None:
            continue
        rows.append(int(x["user_id"]))
        cols.append(p)
    X_sparse = csr_matrix((np.ones(len(rows), dtype=np.float32), (rows, cols)),
                          shape=(n_users, len(warm_indices)))
    return X_sparse, X_sparse.toarray().astype(np.float32)


# =====================================================================
# Eval (full-catalog cold-item, mask user training items)
# =====================================================================
def eval_full(score_fn, train_inters, test_inters, n_items, batch_size: int = 192,
               max_users: int | None = None, subsample_seed: int = 42):
    """Full-catalog eval. If max_users is set, randomly subsample the eligible
    users (used only for inner-val HP-sweep speed; final eval passes None).
    """
    ut = defaultdict(set)
    uts = defaultdict(list)
    for x in train_inters:
        ut[int(x["user_id"])].add(int(x["item_id"]))
    for x in test_inters:
        uts[int(x["user_id"])].append(int(x["item_id"]))
    users = sorted(u for u in uts if uts[u] and ut[u])
    if max_users is not None and len(users) > max_users:
        sub_rng = np.random.RandomState(subsample_seed & 0xFFFFFFFF)
        users = sorted(sub_rng.choice(users, max_users, replace=False).tolist())
    ndcg, hr, rr = [], [], []
    per_user_records = []
    per_user_ndcg = defaultdict(list)
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
                h_ = 1.0 if r0 < TOP_K else 0.0
                rr_ = 1.0 / (r0 + 1)
                ndcg.append(n_)
                hr.append(h_)
                rr.append(rr_)
                per_user_ndcg[int(u)].append(n_)
                per_user_records.append((int(u), int(tgt), float(n_), float(h_), float(rr_)))
    metrics = {
        "NDCG@10": float(np.mean(ndcg)) if ndcg else 0.0,
        "HR@10": float(np.mean(hr)) if hr else 0.0,
        "MRR": float(np.mean(rr)) if rr else 0.0,
        "n_eval": len(ndcg),
    }
    return metrics, per_user_ndcg, per_user_records


# =====================================================================
# Inner-validation HP sweep (per fold)
# =====================================================================
def hp_sweep(dataset: str, train_inters, n_users, n_items, cold_set, emb_np,
             *, seed: int, fold_id: int, device, rng, grid: dict | None = None) -> dict:
    if grid is None:
        grid = HP_GRID
    """Carve a held-out item subset from the OUTER training warm pool, train RQ-VAE
    on remaining warm + outer-cold-mask items, evaluate score_rqvae on the inner
    validation interactions. Pick (L, codebook_size, commitment_cost, sim_option).

    For speed: train one RQ-VAE per (L, num_codes, commit_cost) tuple at HP_EPOCHS;
    evaluate all sim_options on the same trained model. Then pick the winner.
    """
    outer_warm = sorted(set(range(n_items)) - set(cold_set))
    if len(outer_warm) < 50:
        # too small for an inner split — fall back to defaults
        return {"chosen": dict(DEFAULT_HP), "scores": {}, "skipped": True}
    shuf = np.array(outer_warm, dtype=np.int64)
    rng.shuffle(shuf)
    n_val = max(1, int(0.2 * len(shuf)))
    val_items = set(shuf[:n_val].tolist())
    val_inters = [x for x in train_inters if int(x["item_id"]) in val_items]
    if not val_inters:
        return {"chosen": dict(DEFAULT_HP), "scores": {}, "skipped": True}
    inner_cold = sorted(set(cold_set) | val_items)
    inner_warm = np.array(sorted(set(range(n_items)) - set(inner_cold)), dtype=np.int64)
    inner_train = [x for x in train_inters if int(x["item_id"]) not in val_items]
    _, Xw_in = build_warm(inner_train, n_users, inner_warm)
    SBERT_inner_warm = emb_np[inner_warm].astype(np.float32)

    scores = {}
    for L in grid["L"]:
        for nc in grid["codebook_size"]:
            for cc in grid["commitment_cost"]:
                t0 = time.time()
                model, diag = train_rqvae(
                    SBERT_inner_warm, L=L, num_codes=nc, commitment_cost=cc,
                    n_epochs=HP_EPOCHS, lr=LR, batch_size=512,
                    seed=int(seed * 100 + fold_id * 11 + L * 13 + nc + int(cc * 100)),
                    device=device, verbose=False,
                )
                # quantize ALL items
                with torch.no_grad():
                    X_all = torch.from_numpy(emb_np.astype(np.float32)).to(device)
                    idx, q_sum, recon = model.quantize_to_codes(X_all)
                    codes_all = idx.t().cpu().numpy()  # (N, L)
                    qv = q_sum.cpu().numpy()
                    rc = recon.cpu().numpy()
                for opt in grid["sim_option"]:
                    S = build_semantic_sim(codes_all, qv, rc, opt)
                    sf = make_score_rqvae(Xw_in, inner_warm, S)
                    # cap inner-val eval users to 800 (random subset) for HP-sweep speed
                    m, _, _ = eval_full(sf, inner_train, val_inters, n_items,
                                         max_users=800,
                                         subsample_seed=(seed * 1000 + fold_id * 7 + L * 13 + nc + int(cc * 100)))
                    key = f"L{L}_C{nc}_cc{cc}_{opt}"
                    scores[key] = {"NDCG@10": m["NDCG@10"], "uniqueness": diag["uniqueness"],
                                   "recon": diag["final_recon"], "dead_resets": diag["dead_resets"]}
                del model, X_all, idx, q_sum, recon
                gc.collect()
                if device.type == "cuda":
                    torch.cuda.empty_cache()
                dt = time.time() - t0
                # one-line progress
                best_for_combo = max((scores[f"L{L}_C{nc}_cc{cc}_{o}"]["NDCG@10"]
                                       for o in grid["sim_option"]), default=0.0)
                any_opt = grid["sim_option"][0]
                print(f"        HP L={L} C={nc} cc={cc}: best inner-val NDCG@10={best_for_combo:.4f}  "
                      f"uniq={scores[f'L{L}_C{nc}_cc{cc}_{any_opt}']['uniqueness']:.3f}  [{dt:.1f}s]")

    # pick best key
    best_key = max(scores, key=lambda k: scores[k]["NDCG@10"])
    # parse back
    parts = best_key.split("_")
    chosen = {
        "L": int(parts[0][1:]),
        "codebook_size": int(parts[1][1:]),
        "commitment_cost": float(parts[2][2:]),
        "sim_option": "_".join(parts[3:]),
        "inner_val_ndcg10": scores[best_key]["NDCG@10"],
    }
    return {"chosen": chosen, "scores": scores, "skipped": False}


# =====================================================================
# Per-dataset runner
# =====================================================================
def run(dataset: str, seeds: list[int], device: torch.device, perpair_path: Path,
         skip_hp: bool = False, hp_grid: dict | None = None) -> dict:
    if hp_grid is None:
        hp_grid = HP_GRID
    print(f"\n{'#' * 70}\n# RQ-VAE kNN proxy: {dataset.upper()}\n{'#' * 70}")
    interactions, n_users, n_items, emb_np = load_dataset(dataset)
    print(f"  n_users={n_users:,}  n_items={n_items:,}  emb_dim={emb_np.shape[1]}")

    perfold = []  # list of {seed, fold_id, NDCG@10, HR@10, MRR, n_eval, hp}
    per_user_all = defaultdict(list)  # per-user NDCG10 (averaged over fold/seed)
    chosen_hps = []  # one per fold
    n_epochs_full = N_EPOCHS[dataset]

    # If we ever revisit, we want to append to the perpair file with one line per record.
    perpair_path.parent.mkdir(parents=True, exist_ok=True)
    # truncate at start
    with open(perpair_path, "w") as f:
        pass

    for seed in seeds:
        splits = make_item_kfold(interactions, n_items, n_splits=NUM_FOLDS, seed=seed)
        for fold_id, (tr, te, cold) in enumerate(splits):
            t_fold = time.time()
            train_inters = [interactions[i] for i in tr]
            test_inters = [interactions[i] for i in te]
            warm_idx = np.array(sorted(set(range(n_items)) - set(cold)), dtype=np.int64)

            # ---- HP sweep on inner validation ----
            if skip_hp:
                chosen = dict(DEFAULT_HP)
                sweep_diag = {"chosen": chosen, "scores": {}, "skipped": True}
                print(f"  seed={seed} fold={fold_id}  (HP sweep skipped: defaults)")
            else:
                rng = np.random.RandomState((seed * 1000 + fold_id + 7) & 0xFFFFFFFF)
                print(f"  seed={seed} fold={fold_id}  HP sweep on inner-val ...")
                sweep_diag = hp_sweep(dataset, train_inters, n_users, n_items, set(cold),
                                       emb_np, seed=seed, fold_id=fold_id, device=device, rng=rng,
                                       grid=hp_grid)
                chosen = sweep_diag["chosen"]
            chosen_hps.append({"seed": seed, "fold_id": fold_id, **chosen,
                                "n_hp_configs_tried": len(sweep_diag.get("scores", {})),
                                "skipped": sweep_diag.get("skipped", False)})

            # ---- Final train RQ-VAE on outer-warm SBERT ----
            SBERT_warm = emb_np[warm_idx].astype(np.float32)
            t_train = time.time()
            model, diag = train_rqvae(
                SBERT_warm, L=chosen["L"], num_codes=chosen["codebook_size"],
                commitment_cost=chosen["commitment_cost"],
                n_epochs=n_epochs_full, lr=LR, batch_size=512,
                seed=seed * 1000 + fold_id * 17 + 3, device=device, verbose=False,
            )
            train_dt = time.time() - t_train

            # ---- Quantize all items ----
            with torch.no_grad():
                X_all = torch.from_numpy(emb_np.astype(np.float32)).to(device)
                idx, q_sum, recon = model.quantize_to_codes(X_all)
                codes_all = idx.t().cpu().numpy()
                qv = q_sum.cpu().numpy()
                rc = recon.cpu().numpy()
                del X_all, idx, q_sum, recon
                if device.type == "cuda":
                    torch.cuda.empty_cache()

            # ---- Build semantic similarity & score ----
            S_semantic = build_semantic_sim(codes_all, qv, rc, chosen["sim_option"])

            _, Xw = build_warm(train_inters, n_users, warm_idx)
            sf = make_score_rqvae(Xw, warm_idx, S_semantic)
            metrics, per_user_ndcg, records = eval_full(sf, train_inters, test_inters, n_items)

            # Append per-pair records
            with open(perpair_path, "a") as f:
                for u, tgt, nd, h_, rr_ in records:
                    f.write(json.dumps({
                        "dataset": dataset, "seed": int(seed), "fold_id": int(fold_id),
                        "method": "rqvae_knn",
                        "user_id": int(u), "target_item_id": int(tgt),
                        "candidate_scope": "full_catalog",
                        "ndcg10": float(nd), "hr10": float(h_), "rr": float(rr_),
                        "hp": chosen,
                    }) + "\n")

            for u, vs in per_user_ndcg.items():
                per_user_all[int(u)].extend(vs)

            row = {"seed": int(seed), "fold_id": int(fold_id),
                   **{k: v for k, v in metrics.items()},
                   "hp": chosen,
                   "diag": {"recon": diag["final_recon"], "commit": diag["final_commit"],
                            "uniqueness": diag["uniqueness"], "dead_resets": diag["dead_resets"]},
                   "train_seconds": float(train_dt),
                   "fold_seconds": float(time.time() - t_fold)}
            perfold.append(row)
            print(f"    seed={seed} fold={fold_id} HP={chosen}  NDCG@10={metrics['NDCG@10']:.4f}  "
                  f"HR@10={metrics['HR@10']:.4f}  uniq={diag['uniqueness']:.3f}  "
                  f"train={train_dt:.1f}s  fold={row['fold_seconds']:.1f}s")
            del model, S_semantic, Xw
            gc.collect()
            if device.type == "cuda":
                torch.cuda.empty_cache()

    means = {
        "NDCG@10_mean": float(np.mean([r["NDCG@10"] for r in perfold])),
        "NDCG@10_std": float(np.std([r["NDCG@10"] for r in perfold])),
        "HR@10_mean": float(np.mean([r["HR@10"] for r in perfold])),
        "HR@10_std": float(np.std([r["HR@10"] for r in perfold])),
        "MRR_mean": float(np.mean([r["MRR"] for r in perfold])),
        "MRR_std": float(np.std([r["MRR"] for r in perfold])),
        "n_folds": len(perfold),
    }
    print(f"\n  === {dataset.upper()} summary over {len(perfold)} folds ===")
    print(f"    NDCG@10 = {means['NDCG@10_mean']:.4f} +/- {means['NDCG@10_std']:.4f}")
    print(f"    HR@10   = {means['HR@10_mean']:.4f} +/- {means['HR@10_std']:.4f}")
    print(f"    MRR     = {means['MRR_mean']:.4f} +/- {means['MRR_std']:.4f}")

    per_user_mean = {u: float(np.mean(vs)) for u, vs in per_user_all.items()}
    return {
        "perfold": perfold,
        "means": means,
        "chosen_hps": chosen_hps,
        "per_user_mean_ndcg10": per_user_mean,
        "n_users_eval": len(per_user_mean),
        "epochs_full": n_epochs_full,
        "hp_epochs": HP_EPOCHS,
        "fidelity": "rqvae_semantic_id_knn_proxy_not_official_tiger_or_liger",
    }


# =====================================================================
# Significance vs content_direct / CDR_validated (from existing artifacts)
# =====================================================================
def _holm(pvals: dict[str, float]) -> dict[str, float]:
    """Holm step-down on a name->p mapping. Returns name->p_holm."""
    if not pvals:
        return {}
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    holm = {}
    running_max = 0.0
    for i, (name, p) in enumerate(items):
        adj = min(1.0, (m - i) * p)
        running_max = max(running_max, adj)
        holm[name] = running_max
    return holm


def compare_to_baselines(payload: dict) -> dict:
    """For each dataset, compare per-user RQ-VAE NDCG@10 to:
    - content_direct from results_cold_item_v2_perpair_<ds>.json (proper per-user paired test)
    - CDR_validated from results_poc_cdr.json (fold-mean only — perpair not stored)
    One-sided per-user Wilcoxon (target > baseline). Holm correction over both
    comparisons per dataset.
    """
    here = Path(__file__).parent
    cdr_path = here / "results_poc_cdr.json"
    cdr_data = json.load(open(cdr_path)) if cdr_path.exists() else {}

    comparisons = {}
    for ds, info in payload["datasets"].items():
        per_user_target = info.get("per_user_mean_ndcg10", {})
        # cast int keys (json stores as str)
        per_user_target = {int(k): float(v) for k, v in per_user_target.items()}

        cmp = {"rqvae_ndcg10_mean": info["means"]["NDCG@10_mean"],
                "rqvae_ndcg10_std": info["means"]["NDCG@10_std"]}

        # CDR_validated fold-mean comparison
        cdr_perfold = cdr_data.get("datasets", {}).get(ds, {}).get("perfold", {}).get("CDR_validated", [])
        if cdr_perfold:
            cmp["CDR_validated_fold_mean"] = {
                "cdr_ndcg10_mean": float(np.mean(cdr_perfold)),
                "cdr_ndcg10_std": float(np.std(cdr_perfold)),
                "delta_mean": info["means"]["NDCG@10_mean"] - float(np.mean(cdr_perfold)),
                "note": "fold-mean comparison only; per-user CDR not stored in results_poc_cdr.json",
            }

        # content_direct per-user (from results_cold_item_v2_perpair_<ds>.json)
        cd_path = here / f"results_cold_item_v2_perpair_{ds}.json"
        wilcox_payload: dict[str, dict] = {}
        if cd_path.exists():
            cd = json.load(open(cd_path))
            recs = cd.get("methods", {}).get("content_direct", [])
            # records: [fold_id, user_id, item_id, ndcg]
            cd_user_ndcg: dict[int, list[float]] = defaultdict(list)
            for r in recs:
                cd_user_ndcg[int(r[1])].append(float(r[3]))
            cd_user_mean = {u: float(np.mean(v)) for u, v in cd_user_ndcg.items()}
            common = sorted(set(per_user_target) & set(cd_user_mean))
            if common:
                diffs = np.array([per_user_target[u] - cd_user_mean[u] for u in common])
                if np.allclose(diffs, 0):
                    p_raw = 1.0
                else:
                    p_raw = float(wilcoxon(diffs, alternative='greater', zero_method='wilcox').pvalue)
                wilcox_payload["content_direct"] = {
                    "n_users_paired": int(len(common)),
                    "rqvae_mean": float(np.mean([per_user_target[u] for u in common])),
                    "content_direct_mean": float(np.mean([cd_user_mean[u] for u in common])),
                    "delta_user_mean": float(np.mean(diffs)),
                    "p_raw_one_sided_greater": float(p_raw),
                }
        # CDR per-user: load if a perpair file exists (it doesn't for poc_cdr; only for cdr_variants)
        cdr_perpair_path = here / f"results_cdr_variants_perpair_{ds}.jsonl"
        if cdr_perpair_path.exists():
            cdr_user_ndcg: dict[int, list[float]] = defaultdict(list)
            with open(cdr_perpair_path) as f:
                for line in f:
                    try:
                        r = json.loads(line)
                    except Exception:
                        continue
                    if r.get("method") != "CDR_validated":
                        continue
                    cdr_user_ndcg[int(r["user_id"])].append(float(r.get("ndcg10", 0.0)))
            if cdr_user_ndcg:
                cdr_user_mean = {u: float(np.mean(v)) for u, v in cdr_user_ndcg.items()}
                common = sorted(set(per_user_target) & set(cdr_user_mean))
                if common:
                    diffs = np.array([per_user_target[u] - cdr_user_mean[u] for u in common])
                    if np.allclose(diffs, 0):
                        p_raw = 1.0
                    else:
                        p_raw = float(wilcoxon(diffs, alternative='greater', zero_method='wilcox').pvalue)
                    wilcox_payload["CDR_validated"] = {
                        "n_users_paired": int(len(common)),
                        "rqvae_mean": float(np.mean([per_user_target[u] for u in common])),
                        "cdr_mean": float(np.mean([cdr_user_mean[u] for u in common])),
                        "delta_user_mean": float(np.mean(diffs)),
                        "p_raw_one_sided_greater": float(p_raw),
                    }
        # Holm-correct over both
        if wilcox_payload:
            raw = {k: v["p_raw_one_sided_greater"] for k, v in wilcox_payload.items()}
            holm = _holm(raw)
            for k in wilcox_payload:
                p = wilcox_payload[k]["p_raw_one_sided_greater"]
                ph = holm[k]
                marker = '***' if ph < 0.001 else '**' if ph < 0.01 else '*' if ph < 0.05 else 'n.s.'
                wilcox_payload[k]["p_holm"] = float(ph)
                wilcox_payload[k]["marker_holm"] = marker
        cmp["per_user_wilcoxon"] = wilcox_payload
        comparisons[ds] = cmp
    return comparisons


# =====================================================================
# Main
# =====================================================================
def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("datasets", nargs="*", default=["beauty"])
    ap.add_argument("--seeds", default=",".join(str(s) for s in DEFAULT_SEEDS))
    ap.add_argument("--out", default="results_rqvae_knn.json")
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--skip-hp", action="store_true", help="use DEFAULT_HP instead of inner sweep")
    args = ap.parse_args()
    device = torch.device(args.device)
    seeds = [int(s) for s in args.seeds.split(",") if s.strip()]

    out_path = Path(__file__).parent / args.out
    if out_path.exists():
        try:
            payload = json.load(open(out_path))
        except Exception:
            payload = {}
    else:
        payload = {}
    payload.setdefault("schema_version", 1)
    payload.setdefault("status", "tiger_inspired_proxy_complete")
    payload["fidelity"] = "rqvae_semantic_id_knn_proxy_not_official_tiger_or_liger"
    payload["candidate_scope"] = "full_catalog"
    payload["seeds"] = seeds
    payload["device"] = str(device)
    payload["hp_grid"] = HP_GRID
    payload["default_hp"] = DEFAULT_HP
    payload["n_epochs_full"] = N_EPOCHS
    payload["hp_epochs"] = HP_EPOCHS
    payload.setdefault("datasets", {})

    here = Path(__file__).parent
    for ds in args.datasets:
        perpair_path = here / f"results_rqvae_knn_perpair_{ds}.jsonl"
        per_ds_seeds = seeds
        # Books: use one seed only per instructions (compute) unless user overrides
        if ds == "books" and len(seeds) > 1 and not os.environ.get("RQVAE_BOOKS_ALL_SEEDS"):
            per_ds_seeds = [seeds[0]]
            print(f"  [books] using single seed {per_ds_seeds[0]} per budget; "
                  f"set RQVAE_BOOKS_ALL_SEEDS=1 to override")
        ds_grid = HP_GRID_REDUCED if ds in ("instruments", "books") else HP_GRID
        payload["datasets"][ds] = run(ds, per_ds_seeds, device, perpair_path,
                                       skip_hp=args.skip_hp, hp_grid=ds_grid)
        # snapshot after each dataset in case of crash
        with open(out_path, "w") as f:
            json.dump(payload, f, indent=2)

    payload["baseline_comparisons"] = compare_to_baselines(payload)
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()
