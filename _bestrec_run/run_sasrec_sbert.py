"""SASRec-SBERT: SBERT-augmented sequential recommender.

Citations and attribution:
- SASRec architecture: Kang & McAuley (2018), "Self-Attentive Sequential
  Recommendation", ICDM. This file reimplements a SASRec-style
  left-to-right Transformer recommender in PyTorch.
- SBERT / MiniLM text embeddings: Reimers & Gurevych (2019),
  "Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks", EMNLP.
- BLaIR encoder and Amazon Reviews 2023 dataset: Hou et al. (2024),
  "Bridging Language and Items for Retrieval and Recommendation",
  arXiv:2403.03952.
- MLP adaptor option: adopted from the SASRecText AdaptorLayer released by
  Hou et al. (2024) in
  external/AmazonReviews2023/seq_rec_results/model/sasrectext.py.

Our contributions in this file are the 5-core transfer experiments, the
chunked-full-softmax implementation, evaluation caching, and the documented
engineering fixes; we do not claim novelty for SASRec, SBERT, BLaIR, or the
SASRecText MLP adaptor architecture.

Session goal: compete with TIGER/LIGER/BLaIR-style sequential retrieval on this
repository's Amazon Reviews 2023 5-core leave-last-out benchmark. The external
paper numbers used in the session are approximate targets; final SOTA wording
requires exact comparator protocol verification. The local closed-form
ease_sbert baseline was well below these targets on Video_Games, motivating an
autoregressive sequence model.

Architecture (SASRec + SBERT, ~simple-as-possible):
  - Item embedding: learned[d_model] + SBERT-projection (384 -> d_model)
                    summed; the SBERT branch lets cold items get a sensible
                    initialisation from their text alone.
  - Positional embedding: learned, max_seq_len=50.
  - Transformer encoder: n_layers=2 layers, n_heads=2, d_ff=4*d_model, GELU.
  - Causal mask (autoregressive next-item prediction).
  - Output: dot product with full item-embedding table (shared with input).
  - Loss: cross-entropy with full softmax (n_items <= 50K so full softmax fits
          on GPU comfortably).
  - Optimiser: Adam lr=1e-3, weight_decay=1e-5, gradient clip 5.
  - Dropout=0.2 on input embeddings and attention.

Training data construction:
  - Each user's training sequence (sorted chronologically). For each
    position 1..L-1, predict the item at that position from the prefix.
  - We use the standard "left-to-right" prefix prediction, not BERT-style
    masking (SASRec, not BERT4Rec).

Evaluation:
  - Same leave-last-out protocol as in run_5core_benchmark.py.
  - For each user: build their training sequence, run the encoder, get the
    final hidden state, score every item via dot product, mask training items,
    rank the test item, compute NDCG@10/HR@10/MRR.

Usage:
    uv run python run_sasrec_sbert.py Video_Games --epochs 30
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

# --- PAUSE circuit-breaker ------------------------------------------------
# If a PAUSE_EXPERIMENTS sentinel exists in the repo root, exit IMMEDIATELY —
# before importing torch or touching the GPU. This lets a user pause all
# experiment launches (incl. any in-flight scheduled agents that keep
# relaunching) with one file, with zero GPU/RAM cost per relaunch. Only fires
# on direct execution, so `import run_sasrec_sbert` (e.g. the ensemble script)
# is unaffected. To resume: delete the sentinel file.
if __name__ == "__main__":
    _pause = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir,
                           "PAUSE_EXPERIMENTS")
    if os.path.exists(_pause):
        sys.stderr.write("PAUSE_EXPERIMENTS sentinel present — experiments are "
                         "paused; exiting without running.\n")
        raise SystemExit(0)
# --------------------------------------------------------------------------

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader

ROOT = Path(__file__).resolve().parent.parent
SPLIT_DIR = ROOT / "data_5core" / "5core" / "last_out"
EMB_CACHE_DIR = ROOT / "cache_5core"

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


def load_split_csv(path: Path) -> list[tuple]:
    rows = []
    with path.open("r", encoding="utf-8") as fp:
        rdr = csv.DictReader(fp)
        for r in rdr:
            rows.append((r["user_id"], r["parent_asin"],
                          float(r["rating"]), int(r["timestamp"])))
    return rows


def reindex(train_rows, valid_rows, test_rows):
    all_rows = train_rows + valid_rows + test_rows
    users = sorted({r[0] for r in all_rows})
    items = sorted({r[1] for r in all_rows})
    u2idx = {u: i for i, u in enumerate(users)}
    i2idx = {a: j for j, a in enumerate(items)}
    def cvt(rows):
        return [(u2idx[u], i2idx[a], r, t) for u, a, r, t in rows]
    return cvt(train_rows), cvt(valid_rows), cvt(test_rows), users, items


def build_user_sequences(train_inters):
    """For each user, return their training items sorted by timestamp."""
    by_user = defaultdict(list)
    for u, i, _, t in train_inters:
        by_user[u].append((t, i))
    user_seqs = {}
    for u, lst in by_user.items():
        lst.sort()
        user_seqs[u] = [i for (_, i) in lst]
    return user_seqs


def build_user_time_sequences(train_inters):
    """Parallel to build_user_sequences: per-user interaction timestamps
    (seconds), sorted identically (timestamps in the CSVs are milliseconds)."""
    by_user = defaultdict(list)
    for u, i, _, t in train_inters:
        by_user[u].append((t, i))
    user_times = {}
    for u, lst in by_user.items():
        lst.sort()
        user_times[u] = [t // 1000 for (t, _) in lst]
    return user_times


def torch_kmeans(x: torch.Tensor, k: int, iters: int = 25, seed: int = 0) -> torch.Tensor:
    """Plain k-means on L2-normalized rows (cosine k-means). Returns (k, d)
    L2-normalized centroids. Used to build Text-Anchored Prototype assignments."""
    g = torch.Generator(device="cpu").manual_seed(seed)
    idx = torch.randperm(x.shape[0], generator=g)[:k].to(x.device)
    C = x[idx].clone()
    for _ in range(iters):
        assign = (x @ C.T).argmax(dim=1)                  # (n,)
        C_new = torch.zeros_like(C)
        cnt = torch.zeros(k, device=x.device, dtype=x.dtype)
        C_new.index_add_(0, assign, x)
        cnt.index_add_(0, assign, torch.ones_like(assign, dtype=x.dtype))
        nonempty = cnt > 0
        C[nonempty] = C_new[nonempty] / cnt[nonempty].unsqueeze(1)
        C = torch.nn.functional.normalize(C, dim=1)
    return C


# Log-scale time-delta bucket boundaries (seconds): <1h, <6h, <1d, <3d, <1w,
# <2w, <1mo, <3mo, <6mo, <1y, <2y, >=2y  -> bucket ids 0..11
TIME_BUCKET_BOUNDARIES_S = [3600, 21600, 86400, 259200, 604800, 1209600,
                            2592000, 7776000, 15552000, 31536000, 63072000]
N_TIME_BUCKETS = len(TIME_BUCKET_BOUNDARIES_S) + 1


class SASRecDataset(Dataset):
    """For each user with seq [i1, i2, ..., iL], emits one training example
    with RIGHT-padding (standard SASRec convention):
      input  = [i1, i2, ..., i_{L-1}, pad ... pad]  (length max_seq_len)
      target = [i2, i3, ..., iL,       pad ... pad]  (length max_seq_len)
    Loss only counts positions where target != pad.
    Right-padding + causal mask (no key padding mask) avoids the NaN-trap.

    augment_factor: number of training examples per user per epoch. If > 1,
    additional examples use random subsequence starting positions, giving the
    model multiple "views" of the same user history per epoch.
    """
    def __init__(self, user_seqs, max_seq_len, n_items, pad_id, augment_factor=1,
                  user_times=None):
        self.examples = []
        self.max_seq_len = max_seq_len
        self.pad_id = pad_id
        self.n_items = n_items
        self.augment_factor = augment_factor
        self.emit_times = user_times is not None
        for u, seq in user_seqs.items():
            if len(seq) < 2:
                continue
            tms = user_times[u] if self.emit_times else None
            for _ in range(augment_factor):
                self.examples.append((u, seq, tms))

    def __len__(self):
        return len(self.examples)

    def __getitem__(self, idx):
        u, seq, tms = self.examples[idx]
        # If augmentation enabled, pick a random subsequence end position.
        # The subsequence is seq[start:end+1] with end uniformly in [1, L-1].
        if self.augment_factor > 1 and len(seq) > 2:
            end = np.random.randint(1, len(seq))
            sub = seq[:end + 1]
            sub_t = tms[:end + 1] if tms is not None else None
        else:
            sub = seq
            sub_t = tms
        # Truncate to most-recent max_seq_len+1 items
        if len(sub) > self.max_seq_len + 1:
            sub = sub[-(self.max_seq_len + 1):]
            sub_t = sub_t[-(self.max_seq_len + 1):] if sub_t is not None else None
        input_ids = sub[:-1]
        target_ids = sub[1:]
        # Right-pad
        L = len(input_ids)
        pad_amount = self.max_seq_len - L
        input_ids = input_ids + [self.pad_id] * pad_amount
        target_ids = target_ids + [self.pad_id] * pad_amount
        out = (torch.tensor(input_ids, dtype=torch.long),
               torch.tensor(target_ids, dtype=torch.long))
        if self.emit_times:
            in_times = sub_t[:-1]
            in_times = in_times + [0] * pad_amount
            out = out + (torch.tensor(in_times, dtype=torch.long),)
        return out


def collate_batch(batch):
    inputs = torch.stack([b[0] for b in batch])
    targets = torch.stack([b[1] for b in batch])
    if len(batch[0]) == 3:
        times = torch.stack([b[2] for b in batch])
        return inputs, targets, times
    return inputs, targets


class HSTULayer(nn.Module):
    """Pointwise-aggregated-attention layer in the style of HSTU
    (Zhai et al., 2024, "Actions Speak Louder than Words", ICML) — NOT claimed
    as novel; cited and reimplemented here so our TAPE / time-bias / text-sim
    components can be evaluated on a stronger sequence encoder.

    Differences from softmax attention:
      A(i,j) = silu(q_i·k_j/sqrt(dh) + bias_ij) for j <= i, else 0,
      normalized by row count (i+1); output gated elementwise by U branch:
      y = W_out( LayerNorm(A·V) * U ), residual added. No separate FFN
      (the silu gating plays that role, per the HSTU design)."""

    def __init__(self, d_model, n_heads, dropout, n_experts=0):
        super().__init__()
        assert d_model % n_heads == 0
        self.h = n_heads
        self.dh = d_model // n_heads
        self.norm_in = nn.LayerNorm(d_model)
        self.uvqk = nn.Linear(d_model, 4 * d_model)
        self.norm_attn = nn.LayerNorm(d_model)
        self.out = nn.Linear(d_model, d_model)
        self.drop = nn.Dropout(dropout)
        for m in (self.uvqk, self.out):
            nn.init.normal_(m.weight, std=0.02)
            nn.init.zeros_(m.bias)
        # --- NOVEL: prototype-routed expert value-heads. E expert linear maps
        # produce ADDITIVE deltas to the V branch; the per-token mixture weights
        # are supplied by the caller (derived from the frozen TAPE soft cluster
        # assignment — items in the same semantic neighborhood share an expert).
        # Zero-init weights AND biases => exact no-op at initialization, so the
        # layer is identical to vanilla HSTU until the experts learn. This lets
        # semantically-routed capacity specialize the value transform without
        # touching the attention scores (q,k unchanged).
        self.n_experts = n_experts
        if n_experts > 0:
            self.expert_v = nn.ModuleList(
                [nn.Linear(d_model, d_model) for _ in range(n_experts)])
            for m in self.expert_v:
                nn.init.zeros_(m.weight)
                nn.init.zeros_(m.bias)

    def forward(self, x, bias, keep, route=None):
        # x: (B, L, D); bias: (B, H, L, L) additive or None;
        # keep: (L, L) float lower-triangular 1/0 causal keep-mask.
        # Faithful HSTU pointwise-aggregated attention (Zhai et al., 2024):
        #   av = (silu(qk^T + rab) * causal) @ v     -- NO 1/sqrt(d), NO row norm
        #   y  = W_out( LayerNorm(av) * u )          -- LayerNorm absorbs scale
        # The unnormalized silu-weighted sum is the core mechanism; averaging it
        # (as an earlier reimpl did) collapses it to weak mean-pooling.
        B, L, D = x.shape
        xn = self.norm_in(x)
        g = F.silu(self.uvqk(xn))
        u, v, q, k = g.chunk(4, dim=-1)
        if self.n_experts > 0 and route is not None:
            # route: (B, L, E) per-token expert mixture from TAPE assignment.
            # v_delta = sum_e route_e * silu(Expert_e(xn)); zero-init => no-op.
            v_delta = 0.0
            for e in range(self.n_experts):
                v_delta = v_delta + route[..., e:e + 1] * F.silu(self.expert_v[e](xn))
            v = v + v_delta
        q = q.view(B, L, self.h, self.dh).transpose(1, 2)
        k = k.view(B, L, self.h, self.dh).transpose(1, 2)
        v = v.view(B, L, self.h, self.dh).transpose(1, 2)
        scores = q @ k.transpose(-2, -1)                         # (B,H,L,L) — no scaling
        if bias is not None:
            scores = scores + bias
        a = F.silu(scores) * keep                                # causal pointwise, unnormalized
        a = a / L                                                # fixed 1/L (HSTU normalization; scale-stable, not row-count)
        o = (a @ v).transpose(1, 2).reshape(B, L, D)
        y = self.out(self.norm_attn(o) * u)
        return x + self.drop(y)


class SASRecSBERT(nn.Module):
    """SASRec with optional frozen text-feature projection.

    Attribution: the base sequential architecture follows SASRec
    (Kang & McAuley, 2018). When ``mlp_adaptor=True``, the 2-layer MLP
    [sbert_dim -> 300 -> d_model] with Dropout(0.2), ReLU, and N(0, 0.02)
    linear initialization is adopted from the SASRecText ``AdaptorLayer``
    published by Hou et al. (2024) in
    external/AmazonReviews2023/seq_rec_results/model/sasrectext.py.
    We do not claim novelty for that architecture choice; the local claim is
    empirical transfer to our 5-core Amazon Reviews 2023 preprocessing.
    """

    def __init__(self, n_items, pad_id, max_seq_len, d_model=64, n_layers=2,
                  n_heads=2, dropout=0.2, sbert_emb=None, sbert_only=False,
                  mlp_adaptor=False, mlp_hidden=300, mlp_dropout=0.2,
                  time_bias=False, text_sim_bias=False, proto_assign=None,
                  encoder="transformer", pos_rab=False,
                  time_decay_kernel=False, time_decay_bases=8,
                  n_experts=0, text_init_emb=False, cl_aux=False,
                  causal_filter=False, filter_kernel=50,
                  niche_share=False, niche_pop=None,
                  js_shrink=False, item_freq=None,
                  heat_target=False, heat_nbr_idx=None, heat_nbr_sim=None,
                  fitness_gate=False, fg_alpha=0.0, fg_slope=4.0, fg_tau=0.0,
                  cue_fusion=False, cue_mode="sum2", cue_pi_id=None, cue_pi_text=None,
                  conn_gate=False, item_users=None,
                  cold_synth_knn=0, cold_synth_nbr=None, cold_synth_wgt=None,
                  cold_synth_is_cold=None, cold_synth_norm=False,
                  cold_id_drop=False,
                  cred_route_train=False, cred_k=2.0):
        super().__init__()
        self.n_items = n_items
        self.pad_id = pad_id
        self.d_model = d_model
        self.max_seq_len = max_seq_len
        self.n_heads = n_heads
        self.encoder_type = encoder
        self.sbert_only = sbert_only and (sbert_emb is not None)

        # Item embedding (learned). pad_id has its own slot.
        # In sbert_only mode (faithful SASRecText), this is unused but kept for
        # forward-compat with the rest of the script (e.g. all_item_features
        # iterates n_items items regardless). We disable its gradients so the
        # optimizer doesn't waste cycles updating an unused table.
        self.item_emb = nn.Embedding(n_items + 1, d_model, padding_idx=pad_id)
        nn.init.normal_(self.item_emb.weight, std=0.02)
        # NOVEL (this campaign, genuinely untried per ledger through 2026-06-15):
        # text WARM-START of the trainable item-ID embedding table. Distinct from
        # the additive frozen-text side-feature path (N1/O1) and from sbert_only:
        # here the ID table STARTS in the text manifold (top-d PCA of the frozen
        # text embeddings, rescaled to the std-0.02 init scale) and then trains
        # freely / specializes. This is how UniSRec/Recformer-style text-rec use
        # text — as initialization of the learnable representation, not a frozen
        # crutch added at every step. Optimization dynamics differ: the table
        # begins semantically structured instead of random. Default OFF.
        if text_init_emb and (sbert_emb is not None):
            with torch.no_grad():
                T = torch.from_numpy(np.asarray(sbert_emb, dtype=np.float32))
                T = T - T.mean(dim=0, keepdim=True)              # center
                # top-d_model principal directions via SVD (deterministic)
                U, S, Vh = torch.linalg.svd(T, full_matrices=False)
                k = min(d_model, Vh.shape[0])
                P = (U[:, :k] * S[:k])                            # (n_items, k) PCA scores
                # rescale columns to the std-0.02 init scale used elsewhere
                P = P / (P.std(dim=0, keepdim=True) + 1e-8) * 0.02
                self.item_emb.weight[:n_items, :k].copy_(P)
            print(f"  text-init-emb: warm-started item_emb from top-{k} PCA of text "
                  f"(n_items={n_items}, rescaled to std 0.02)")
        if self.sbert_only:
            self.item_emb.weight.requires_grad_(False)

        # SBERT projection (frozen embeddings, learned projection).
        # If mlp_adaptor=True, use the 2-layer MLP from SASRecText:
        #   Dropout -> Linear(sbert_dim, mlp_hidden) -> ReLU -> Dropout
        #   -> Linear(mlp_hidden, d_model).
        # The MLP adaptor design (2-layer MLP [768, 300, 64] with
        # Dropout(0.2) + ReLU in the tested BLaIR setting) is adopted from
        # the SASRecText AdaptorLayer published by Hou et al. (2024) in
        # external/AmazonReviews2023/seq_rec_results/model/sasrectext.py.
        # We do not claim novelty for this architecture choice; our
        # contribution is the empirical demonstration that it transfers to
        # our 5-core preprocessing. See Hou et al. (2024), arXiv:2403.03952.
        self.use_sbert = sbert_emb is not None
        if self.use_sbert:
            sbert_dim = sbert_emb.shape[1]
            # Frozen SBERT, including a zero row for the pad slot
            sbert_with_pad = np.zeros((n_items + 1, sbert_dim), dtype=np.float32)
            sbert_with_pad[:n_items] = sbert_emb
            self.sbert_table = nn.Embedding.from_pretrained(
                torch.from_numpy(sbert_with_pad), freeze=True, padding_idx=pad_id)
            if mlp_adaptor:
                self.sbert_proj = nn.Sequential(
                    nn.Dropout(mlp_dropout),
                    nn.Linear(sbert_dim, mlp_hidden),
                    nn.ReLU(),
                    nn.Dropout(mlp_dropout),
                    nn.Linear(mlp_hidden, d_model),
                )
                # Init to N(0, 0.02) to match SASRecText's AdaptorLayer._init_weights
                for m in self.sbert_proj:
                    if isinstance(m, nn.Linear):
                        nn.init.normal_(m.weight, std=0.02)
                        if m.bias is not None:
                            nn.init.zeros_(m.bias)
            else:
                self.sbert_proj = nn.Linear(sbert_dim, d_model, bias=False)
            # Text-distillation head: projects a sequence hidden state (d_model)
            # into the frozen text-embedding space (sbert_dim) so an auxiliary
            # loss can align the predicted next-item representation with the
            # target item's frozen text embedding. NOVEL auxiliary objective
            # (a text-target multi-task / distillation term for sequential rec).
            self.distill_head = nn.Linear(d_model, sbert_dim, bias=False)
            nn.init.normal_(self.distill_head.weight, std=0.02)

        # Position embedding (learned)
        self.pos_emb = nn.Embedding(max_seq_len, d_model)
        nn.init.normal_(self.pos_emb.weight, std=0.02)
        self.drop = nn.Dropout(dropout)

        # NOVEL probe (genuinely untried per the ledger through 2026-06-16):
        # CL4SRec-style sequence-level self-supervised CONTRASTIVE auxiliary
        # objective (Xie et al., 2022, "Contrastive Learning for Sequential
        # Recommendation", arXiv:2010.14395). Distinct from the c2 text-DISTILL
        # aux (which aligns the hidden to the target item's FROZEN TEXT embedding,
        # a supervised-target term): this is purely self-supervised in SEQUENCE
        # space — two augmented (item-masked) views of the SAME input sequence are
        # encoded, pooled, and pulled together by an InfoNCE loss against other
        # sequences in the batch. It directly targets the campaign's recurring
        # val>>test decoupling (generalization) rather than adding more text/time
        # signal. A small SimCLR-style 2-layer projection head maps the pooled
        # sequence representation into the contrastive space. Created ONLY when
        # cl_aux is set, so when OFF the model is parameter- and RNG-identical to
        # baseline (default-OFF no-op). Default OFF.
        self.cl_aux = cl_aux
        if cl_aux:
            self.cl_head = nn.Sequential(
                nn.Linear(d_model, d_model),
                nn.ReLU(),
                nn.Linear(d_model, d_model),
            )
            for m in self.cl_head:
                if isinstance(m, nn.Linear):
                    nn.init.normal_(m.weight, std=0.02)
                    if m.bias is not None:
                        nn.init.zeros_(m.bias)

        # NOVEL probe V1 (RESEARCH_QUEUE 2026-06-16-1): strictly-causal per-channel
        # learnable temporal FIR filter as a zero-init gated residual on the sequence
        # embeddings, inserted just before the encoder stack. Leak-free causal dual of
        # the FMLP-Rec (Zhou et al., WWW 2022, arXiv:2202.13556) / BSARec (Shin et al.,
        # AAAI 2024, arXiv:2312.10325) learnable frequency filter. Those papers use a
        # BIDIRECTIONAL FFT filter, which would leak the label under our all-position
        # next-item loss; a left-padded depthwise Conv1d (FIR) is strictly causal
        # (output position t depends only on inputs <= t) and is leak-free by design.
        # gate zero-init => exact no-op at init; kernel init = causal delta (all-pass).
        self.causal_filter = None
        if causal_filter:
            K = int(filter_kernel)
            self.filter_kernel_len = K
            self.causal_filter = nn.Conv1d(d_model, d_model, kernel_size=K,
                                            groups=d_model, bias=False)
            with torch.no_grad():
                self.causal_filter.weight.zero_()
                # causal delta: weight 1.0 at the LAST (most-recent) tap, 0 elsewhere
                self.causal_filter.weight[:, :, -1] = 1.0
            self.filter_gate = nn.Parameter(torch.zeros(1))

        # Sequence encoder: softmax Transformer (SASRec default) or
        # HSTU-style pointwise-attention stack (Zhai et al., 2024; cited).
        if encoder == "hstu":
            self.hstu_layers = nn.ModuleList(
                [HSTULayer(d_model, n_heads, dropout, n_experts=n_experts)
                 for _ in range(n_layers)])
            self.transformer = None
        else:
            encoder_layer = nn.TransformerEncoderLayer(
                d_model=d_model, nhead=n_heads, dim_feedforward=4 * d_model,
                dropout=dropout, activation="gelu", batch_first=True, norm_first=True)
            self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=n_layers)
        self.ln_final = nn.LayerNorm(d_model)

        # NOTE: the eval-mode C++ TransformerEncoder fastpath mishandles
        # per-batch 3D float attention masks (NaN outputs; verified on
        # torch 2.11 cu128, RTX 5060 Ti). Disable the MHA fastpath whenever
        # the float-mask features below are enabled. Training is unaffected
        # (the fastpath never runs in training mode).
        if time_bias or text_sim_bias or pos_rab or time_decay_kernel:
            torch.backends.mha.set_fastpath_enabled(False)

        # --- Relative time-bucket attention bias (NOT claimed as novel:
        # time-interval-aware attention follows TiSASRec (Li, Wang & McAuley,
        # 2020) and the relative time-bucket bias in HSTU (Zhai et al., 2024);
        # this is a lightweight additive-bias variant). Zero-init => exact
        # no-op at initialization.
        self.use_time_bias = time_bias
        if time_bias:
            self.register_buffer(
                "time_boundaries",
                torch.tensor(TIME_BUCKET_BOUNDARIES_S, dtype=torch.long),
                persistent=False)
            self.time_bias_emb = nn.Embedding(N_TIME_BUCKETS, n_heads)
            nn.init.zeros_(self.time_bias_emb.weight)

        # --- Relative-position attention bias (rab_p): a learned per-head
        # scalar for each causal position gap (i - j) in [0, max_seq_len).
        # This is HSTU's signature relative-attention-bias mechanism (Zhai et
        # al., 2024); my earlier HSTU reimplementation omitted it. Cited, not
        # claimed as novel. Zero-init => exact no-op at initialization.
        self.use_pos_rab = pos_rab
        if pos_rab:
            self.pos_rab_emb = nn.Embedding(max_seq_len, n_heads)
            nn.init.zeros_(self.pos_rab_emb.weight)

        # --- NOVEL: Learned continuous time-decay attention kernel. Replaces the
        # 12-bucket discrete lookup (use_time_bias) with a smooth, differentiable
        # per-head function of the real time gap dt. We expand dt into a small
        # bank of learnable exponential-decay basis functions over LOG-time:
        #     u_k = exp(-softplus(rate_k) * log1p(dt))
        # and mix them per head: bias_h(dt) = sum_k W[h,k] * u_k.
        # The decay rates are initialized to a geometric spread of timescales
        # (so the bank spans hours..years) and are LEARNABLE, letting the model
        # discover the recency profile that the fixed buckets cannot. W is
        # zero-init => exact no-op at initialization. This is an original
        # mechanism (continuous learnable kernel) distinct from TiSASRec's
        # bucketed interval embeddings and HSTU's bucketed rel-time bias; it is
        # closest in spirit to time-decay point processes (Hawkes) but learned
        # end-to-end as an attention bias.
        self.use_time_decay_kernel = time_decay_kernel
        if time_decay_kernel:
            self.n_decay_bases = time_decay_bases
            # Geometric spread of initial decay rates over log-time. log1p(dt)
            # ranges ~0..21 (dt up to a few years in seconds). Rates from ~2.0
            # (very local) down to ~0.02 (near-flat / long memory).
            init_rates = torch.logspace(
                math.log10(2.0), math.log10(0.02), steps=time_decay_bases)
            # store as inverse-softplus so softplus(raw) == init_rates
            self.decay_raw_rate = nn.Parameter(
                torch.log(torch.expm1(init_rates.clamp_min(1e-4))))
            self.decay_mix = nn.Parameter(torch.zeros(n_heads, time_decay_bases))

        # --- Text-similarity attention bias: attn(i,j) += w_h * cos(text_i,
        # text_j) with per-head learnable scale, zero-init (no-op at init).
        self.use_text_sim_bias = text_sim_bias and (sbert_emb is not None)
        if self.use_text_sim_bias:
            self.textsim_scale = nn.Parameter(torch.zeros(n_heads))

        # --- Text-Anchored Prototype Embeddings (TAPE): frozen soft cluster
        # assignments over the text-embedding space gate a LEARNABLE prototype
        # table that is added to each item's feature. Items in the same
        # semantic neighborhood share learnable capacity — the shared-structure
        # benefit of TIGER-style semantic IDs (Rajput et al., 2023) without
        # discrete codes or an autoregressive decoder. Related prototype ideas:
        # ProtoMF (Melchiorre et al., 2022); VQ-Rec (Hou et al., 2023).
        # proto_assign: (n_items + 1, K) float32, pad row = zeros (frozen).
        # proto_emb zero-init => exact no-op at initialization.
        # Hierarchical TAPE: accept one assignment matrix or a list of them
        # (coarse-to-fine levels, analogous to RQ levels in TIGER but soft and
        # frozen). Each level gets its own zero-init learnable prototype table.
        if proto_assign is not None and not isinstance(proto_assign, (list, tuple)):
            proto_assign = [proto_assign]
        self.use_prototypes = proto_assign is not None
        self.n_proto_levels = len(proto_assign) if proto_assign else 0
        if self.use_prototypes:
            for li, A in enumerate(proto_assign):
                self.register_buffer(f"proto_assign_{li}", A, persistent=False)
            self.proto_emb = nn.ModuleList(
                [nn.Embedding(A.shape[1], d_model) for A in proto_assign])
            for e in self.proto_emb:
                nn.init.zeros_(e.weight)

        # --- NOVEL: prototype-router for expert value-heads (c1). Maps the
        # frozen level-0 TAPE soft assignment (K-dim) to a per-token softmax
        # over E experts. Requires TAPE (--text-prototypes). Random-init router
        # is harmless because the expert deltas it gates are zero-init (no-op at
        # start); the experts and router co-adapt during training so that
        # semantically-clustered items share a specialized value transform.
        self.n_experts = n_experts
        if n_experts > 0:
            assert self.use_prototypes, "--expert-heads requires --text-prototypes (TAPE)"
            K0 = proto_assign[0].shape[1]
            self.expert_router = nn.Linear(K0, n_experts)
            nn.init.normal_(self.expert_router.weight, std=0.02)
            nn.init.zeros_(self.expert_router.bias)

        # --- NOVEL: niche-overlap fitness-sharing crowding penalty (W1,
        # RESEARCH_QUEUE 2026-06-16-2). Grounds the ecology limiting-similarity /
        # Goldberg-Richardson (1987) fitness-sharing idea as the first inter-item
        # competition term in the loss: discount the CE target logit of items in
        # a crowded, POPULAR semantic niche, forcing the encoder to earn
        # probability via distinguishing signal rather than niche popularity.
        # crowd_i = A_i . (A^T pop) = popularity-weighted soft count of items
        # sharing item i's frozen TAPE prototypes (the sharing denominator).
        # LEAK-FREE: `niche_pop` is built from TRAIN interactions only (main()),
        # and the penalty is applied at TRAINING only (eval scoring untouched).
        # beta zero-init => exact no-op at start. Honest CS analogues cited
        # (DPP-likelihood Liu 2022; PD/PDA Zhang 2021; logit-adjustment Menon
        # 2021) — none identical; this is a single similarity-modulated scalar.
        self.use_niche_share = bool(niche_share)
        if self.use_niche_share:
            assert self.use_prototypes, "--niche-share-beta requires --text-prototypes (TAPE)"
            A0 = proto_assign[0]                              # (n_items+1, K) frozen
            if niche_pop is None:
                pop = torch.zeros(A0.shape[0], dtype=A0.dtype, device=A0.device)
            else:
                pop = niche_pop.to(device=A0.device, dtype=A0.dtype)
            crowd = A0 @ (A0.t() @ pop)                       # (n_items+1,)
            self.register_buffer("niche_crowd",
                                 torch.log1p(crowd.clamp_min(0.0)), persistent=False)
            self.niche_share_beta = nn.Parameter(torch.zeros(1))

        # --- NOVEL: frequency-adaptive James–Stein / Efron–Morris embedding
        # shrinkage (X1, RESEARCH_QUEUE 2026-06-16-3). Shrinks each item's
        # learned id-vector (a per-item MLE estimated from that item's few
        # interactions) toward its TAPE semantic-cluster mean m_i, with
        # intensity lambda_i = c/(c+n_i) set by the train-only interaction
        # count n_i — heaviest for the rarest items (Stein's total-risk
        # reduction for d=64 >> 3). LEAK-FREE: item_freq is train-only;
        # the shrinkage is representation-side (eval scoring untouched).
        # shrink_c zero-init at -8.0 ⇒ c=softplus≈0.0003 ⇒ lambda≈0 ⇒ no-op.
        self.js_shrink = bool(js_shrink)
        if self.js_shrink:
            assert self.use_prototypes, "--js-shrink requires --text-prototypes (TAPE)"
            if item_freq is None:
                item_freq = torch.zeros(n_items + 1)
            self.register_buffer("item_freq", item_freq.float(), persistent=False)
            self.shrink_c = nn.Parameter(torch.tensor(-8.0))

        # --- NOVEL Y1 (heat-target): heat-kernel / manifold-diffusion label
        # smoothing (RESEARCH_QUEUE 2026-06-16-4). Frozen top-m text-cosine
        # neighbor index/sim buffers feed a Gibbs soft target in the loss;
        # heat_temp is a single learnable diffusion temperature, init -6.0 =>
        # T=softplus(-6)~0.0025 => the soft target collapses to the hard delta
        # (q~[1,0,...]) => EXACT no-op at init. LEAK-FREE: neighbors come from
        # the FROZEN text manifold only (no interactions, no val/test rows);
        # used in the TRAINING loss only (eval scoring is untouched).
        self.use_heat = bool(heat_target)
        if self.use_heat:
            assert heat_nbr_idx is not None and heat_nbr_sim is not None, \
                "--heat-target requires precomputed text neighbors (needs --text-prototypes / SBERT)"
            self.register_buffer("nbr_idx", heat_nbr_idx.long(), persistent=False)
            self.register_buffer("nbr_sim", heat_nbr_sim.float(), persistent=False)
            self.heat_temp = nn.Parameter(torch.tensor(-6.0))

        # --- NOVEL Z1 (fitness-gate): exposure-gated cold-item routing
        # (RESEARCH_QUEUE 2026-06-17-1, TAIL mission). For cold/low-exposure
        # items, damp the noisy learned ID vector toward the fully-observed
        # frozen-text channel, via a NON-LEARNABLE gate keyed to the train-only
        # log-frequency and the tail/mid tercile boundary tau. No learnable
        # scalar (unlike W1/X1/Y1) ⇒ cannot be voted off. fg_alpha=0 ⇒ exact
        # no-op. LEAK-FREE: item_freq + tau are train-only; representation-side
        # (eval scoring untouched).
        self.fitness_gate = bool(fitness_gate)
        if self.fitness_gate:
            assert self.use_sbert, "--fitness-gate requires text embeddings (frozen-text routing target)"
            if not hasattr(self, "item_freq"):
                if item_freq is None:
                    item_freq = torch.zeros(n_items + 1)
                self.register_buffer("item_freq", item_freq.float(), persistent=False)
            self.fg_alpha = float(fg_alpha)
            self.fg_slope = float(fg_slope)
            self.fg_tau = float(fg_tau)

        # --- NOVEL CF1 (cue-fusion): reliability-weighted ID×text fusion
        # (RESEARCH_QUEUE 2026-06-17-3, MID-regime). Frozen per-item precisions:
        # cue_pi_id = train-only freq (ID Fisher info), cue_pi_text = frozen-text
        # distinctiveness (calibrated to the median ID precision). NON-learnable
        # (no scalar to vote off); representation-side. OFF ⇒ block skipped.
        self.cue_fusion = bool(cue_fusion)
        self.cue_mode = str(cue_mode)
        if self.cue_fusion:
            assert self.use_sbert, "--cue-fusion requires text embeddings (frozen-text channel)"
            assert cue_pi_id is not None and cue_pi_text is not None, \
                "--cue-fusion needs precomputed cue_pi_id (train freq) + cue_pi_text (text distinctiveness)"
            self.register_buffer("cue_pi_id", cue_pi_id.float(), persistent=False)
            self.register_buffer("cue_pi_text", cue_pi_text.float(), persistent=False)

        # --- NOVEL: connectivity-gated cold-start fusion -----------------------
        # The user-mode titration proved text's tail/cold advantage tracks
        # COLLABORATIVE CONNECTIVITY (distinct users/item) — NOT interaction
        # frequency (the axis X1/Z1/CF1 all gated on, all DEAD). So gate the
        # ID<->text mix on TRAIN-only distinct users/item: for LOW-connectivity
        # (cold) items the learned ID vector is under-estimated, so down-weight it
        # and up-weight the frozen text. LEARNABLE + exact no-op at init
        # (cg_alpha=sigmoid(-6)≈0.0025 ⇒ additive baseline) so it can only help,
        # never force-damp like Z1. Cold-start = the users/item→0 limit.
        self.conn_gate = bool(conn_gate)
        if self.conn_gate:
            if item_users is None:
                item_users = torch.zeros(n_items + 1)
            self.register_buffer("item_users", item_users.float(), persistent=False)
            self.cg_alpha = nn.Parameter(torch.tensor(-6.0))     # sigmoid(-6)≈0 ⇒ no-op
            self.cg_slope = nn.Parameter(torch.tensor(1.0))
            lu = torch.log1p(item_users[:n_items].float())
            tau = float(lu[lu > 0].median()) if bool((lu > 0).any()) else 0.0
            self.register_buffer("cg_tau", torch.tensor(tau), persistent=False)

        # NOVEL (PROPOSAL 2026-06-23-1): synthetic-connectivity buffers. For COLD
        # items, the ID channel is rebuilt from a frozen-text-kNN weighted sum of
        # LEARNED warm-item ID rows (precomputed neighbor idx + weights). Non-
        # learnable, no-op when knn=0 or no item is flagged cold.
        self.cold_synth_knn = int(cold_synth_knn)
        if self.cold_synth_knn > 0 and cold_synth_nbr is not None:
            self.cold_synth = True
            self.register_buffer("cold_synth_nbr", cold_synth_nbr.long(), persistent=False)
            self.register_buffer("cold_synth_wgt", cold_synth_wgt.float(), persistent=False)
            self.register_buffer("cold_synth_is_cold", cold_synth_is_cold.bool(), persistent=False)
        else:
            self.cold_synth = False
        # NOVEL (PROPOSAL 2026-06-23-3): parameter-free MAGNITUDE calibration of the
        # kNN-imputed cold ID row. A softmax-weighted average of non-collinear
        # neighbor rows is norm-contracting (Jensen: ‖Σ wₖ eₖ‖ ≤ Σ wₖ‖eₖ‖), so the
        # synthesized cold row is systematically smaller than the warm rows it must
        # out-score under dot-product full-catalog softmax. When ON, rescale synth
        # to the LOCAL weighted-mean neighbor norm τ_i (direction preserved). OFF =>
        # cold path bit-identical to cold-synth. Cold-only (is_cold-gated) => warm
        # scoring byte-identical; parameter-free (nothing learned).
        self.cold_synth_norm = bool(cold_synth_norm)
        # NOVEL (PROPOSAL 2026-07-02-1): cold-item ID-DROP (text-fallback). For
        # TRUE-COLD items (item_users==0, the --cold-item-frac hold-out) the
        # learned ID row is pure untrained noise (~N(0,0.02), never gradient-
        # updated); ADDING it to sbert_proj(text) drowns the real text signal
        # (the on-disk --sbert-only diagnostic ranks cold ~5-9x higher than the
        # best impute arm). When ON, zero the cold ID row so each cold item is
        # carried by the trained additive frozen-text path (+ TAPE). Warm items
        # byte-untouched. Parameter-free, cold-only, no-op when OFF or no cold
        # split. Needs the is_cold mask even without cold-synth.
        self.cold_id_drop = bool(cold_id_drop)
        if self.cold_id_drop and not self.cold_synth and cold_synth_is_cold is not None:
            self.register_buffer("cold_synth_is_cold", cold_synth_is_cold.bool(), persistent=False)

        # --- NOVEL cold-start (PROPOSAL 2026-07-03-1, TRAIN-CONSISTENT variant):
        # credibility-ROUTED dual-space training loss. Needs the TRAIN-only
        # item_freq buffer to form Z_j = n_j/(n_j+k) in the loss. NON-learnable
        # (no scalar to vote off). OFF => the loss branch is skipped =>
        # bit-identical. LEAK-FREE: item_freq is train-only (cold items already
        # removed from train_inters => n_j=0 => Z_j=0 => pure text supervision).
        self.cred_route_train = bool(cred_route_train)
        self.cred_k = float(cred_k)
        if self.cred_route_train:
            assert self.use_sbert, "--cred-route-train requires text embeddings (frozen-text scoring space)"
            if not hasattr(self, "item_freq"):
                if item_freq is None:
                    item_freq = torch.zeros(n_items + 1)
                self.register_buffer("item_freq", item_freq.float(), persistent=False)

        # Output projection: tied to item_emb + optional SBERT bridge
        # We compute logits as hidden @ item_emb.T (full softmax over catalog).

    def item_features(self, item_ids):
        """Combine learned item embedding with frozen SBERT projection.
        If sbert_only=True, use ONLY the SBERT projection (no learned per-item
        table) — tests whether shared-content embedding suffices at huge
        catalogs where per-item learned vectors are too sparse."""
        if self.sbert_only:
            s = self.sbert_table(item_ids)
            return self.sbert_proj(s)
        e = self.item_emb(item_ids)                     # (..., d_model) per-item MLE id-vector
        # NOVEL cold-id-drop (PROPOSAL 2026-07-02-1): zero the untrained noise ID
        # row for TRUE-COLD items so the trained additive frozen-text path (+TAPE)
        # carries them (the DROP alternative to cold-synth's IMPUTE). Cold-only,
        # parameter-free; warm rows untouched. Mutually exclusive with cold-synth
        # (both write the cold slot) — run with --cold-synth-knn 0.
        if getattr(self, "cold_id_drop", False) and hasattr(self, "cold_synth_is_cold"):
            is_cold = self.cold_synth_is_cold[item_ids]            # (...,) bool
            if bool(is_cold.any()):
                e = torch.where(is_cold.unsqueeze(-1), torch.zeros_like(e), e)
        # NOVEL cold-synth (PROPOSAL 2026-06-23-1): for COLD items (untrained ID
        # row), replace the ID channel with a frozen-text-kNN weighted sum of the
        # LEARNED warm ID rows. Warm items kept verbatim (torch.where).
        # CORRECTION (2026-06-23, FIX #1b): this branch is NOT a no-op during
        # training. Cold items never appear as training INPUTS or TARGETS (removed
        # from train sequences), BUT chunked_full_softmax_loss() calls
        # item_features() over the WHOLE catalog (range(0, n_items) at line ~934),
        # so cold rows DO appear as NEGATIVE CANDIDATES in the training softmax
        # denominator. With cold-synth ON, those cold rows become populated
        # text-kNN vectors (live, recomputed from current warm item_emb each step)
        # instead of random-init untrained vectors => the partition function and
        # hence the warm-item gradients shift. This is the leak-free competitor-set
        # effect that systematically raises warm/overall NDCG (+0.00074 MI /
        # +0.00034 VG warm, +0.00041 VG overall, 5/5 seeds). Leak-free: no
        # train/val/test target is consulted; synthesis uses only frozen text +
        # learned warm rows.
        if getattr(self, "cold_synth", False) and self.cold_synth_knn > 0:
            is_cold = self.cold_synth_is_cold[item_ids]             # (...,) bool
            if bool(is_cold.any()):
                nbr = self.cold_synth_nbr[item_ids]                 # (..., K)
                w = self.cold_synth_wgt[item_ids]                   # (..., K)
                synth = (self.item_emb(nbr) * w.unsqueeze(-1)).sum(dim=-2)  # (..., d)
                # NOVEL norm-restore (PROPOSAL 2026-06-23-3): lift the averaging-
                # contracted magnitude back to the local neighbor scale τ_i, keeping
                # the cold-synth direction. Parameter-free, cold-only, no-op when OFF.
                if getattr(self, "cold_synth_norm", False):
                    nbr_norm = self.item_emb(nbr).norm(dim=-1)             # (..., K)
                    tgt = (nbr_norm * w).sum(dim=-1, keepdim=True)         # (..., 1) τ_i
                    synth = synth * (tgt / synth.norm(dim=-1, keepdim=True).clamp_min(1e-8))
                e = torch.where(is_cold.unsqueeze(-1), synth, e)
        # TAPE prototype reconstruction m = Σ_l A_l @ P_l (the semantic-cluster mean).
        m = None
        if self.use_prototypes:
            m = 0
            for li in range(self.n_proto_levels):
                a = getattr(self, f"proto_assign_{li}")[item_ids]
                m = m + a @ self.proto_emb[li].weight
        # NOVEL X1: James–Stein shrinkage of the id-vector toward m, intensity
        # lambda_i = c/(c+n_i) (rare items shrink most). c≈0 at init ⇒ no-op.
        if getattr(self, "js_shrink", False) and m is not None:
            c = F.softplus(self.shrink_c)
            lam = (c / (c + self.item_freq[item_ids])).unsqueeze(-1)
            e = (1.0 - lam) * e + lam * m               # Efron–Morris posterior mean
        # NOVEL Z1 (fitness-gate): non-learnable damping of the ID channel for
        # cold items so their representation leans on the frozen text channel.
        # g→1-alpha for cold (lf≪tau), g→1 for head (lf≫tau). alpha=0 ⇒ no-op.
        if getattr(self, "fitness_gate", False) and self.fg_alpha > 0.0:
            lf = torch.log1p(self.item_freq[item_ids])
            g = 1.0 - self.fg_alpha * torch.sigmoid(-self.fg_slope * (lf - self.fg_tau))
            e = g.unsqueeze(-1) * e
        # NOVEL CF1 (cue-fusion): reliability-weighted (inverse-variance) fusion
        # of the ID and frozen-text channels (multisensory inverse effectiveness).
        # NON-learnable: w_id ∝ ID precision (train-only freq), w_tx ∝ text
        # precision (frozen-text distinctiveness) — no scalar to vote off. sum2
        # preserves total channel mass (w_id+w_tx=2 == the plain "both weight 1").
        if getattr(self, "conn_gate", False) and self.use_sbert:
            # Connectivity-gated cold-start fusion: gate on TRAIN distinct
            # users/item (the causal axis), not freq. Low users ⇒ down-weight the
            # under-trained ID vector, up-weight the frozen text. No-op at init.
            lu = torch.log1p(self.item_users[item_ids].float())
            alpha = torch.sigmoid(self.cg_alpha)                        # ~0 at init
            cold = torch.sigmoid(-self.cg_slope * (lu - self.cg_tau))   # ~1 cold, ~0 warm
            w_id = (1.0 - alpha * cold).unsqueeze(-1)
            w_tx = (1.0 + alpha * cold).unsqueeze(-1)
            e = w_id * e + w_tx * self.sbert_proj(self.sbert_table(item_ids))
        elif getattr(self, "cue_fusion", False) and self.use_sbert:
            pid = self.cue_pi_id[item_ids]
            ptx = self.cue_pi_text[item_ids]
            denom = pid + ptx + 1e-8
            scale = 2.0 if self.cue_mode == "sum2" else 1.0
            w_id = (scale * pid / denom).unsqueeze(-1)
            w_tx = (scale * ptx / denom).unsqueeze(-1)
            e = w_id * e + w_tx * self.sbert_proj(self.sbert_table(item_ids))
        elif self.use_sbert:
            s = self.sbert_table(item_ids)              # (..., sbert_dim)
            e = e + self.sbert_proj(s)
        if m is not None:
            e = e + m                                   # additive TAPE term, unchanged
        return e

    def all_item_features(self):
        """(n_items, d_model) item-embedding table for scoring."""
        ids = torch.arange(self.n_items, device=self.item_emb.weight.device)
        return self.item_features(ids)

    def encode(self, input_ids, times=None):
        """Encode an input sequence into hidden states (no item-scoring).
        Returns (B, L, d_model).

        times: optional (B, L) int64 seconds. When time-bias / text-sim-bias
        are enabled, a per-example 3D float attention mask is built:
          mask = causal(-inf above diag) + time_bucket_bias + textsim_bias.
        Right-padding guarantees real queries never attend pad keys (pads sit
        at j > i), so garbage pad times/text are harmless."""
        B, L = input_ids.shape
        device = input_ids.device

        x = self.item_features(input_ids)                # (B, L, d)
        positions = torch.arange(L, device=device).unsqueeze(0).expand(B, L)
        x = x + self.pos_emb(positions)
        x = self.drop(x)

        # NOVEL probe V1: strictly-causal learnable FIR filter (zero-init gated
        # residual). Left-pad by K-1 (no right pad) => out[t] depends only on
        # inputs at positions <= t, so no future leakage under the all-position
        # next-item loss. gate=0 at init => exact no-op (x returned unchanged).
        if self.causal_filter is not None:
            K = self.filter_kernel_len
            xt = x.transpose(1, 2)                          # (B, d, L)
            xt = F.pad(xt, (K - 1, 0))                      # LEFT-pad only -> causal
            y = self.causal_filter(xt).transpose(1, 2)      # (B, L, d)
            x = x + self.filter_gate * (y - x)

        # Shared additive attention bias (B, H, L, L) from time buckets and/or
        # text similarity; None when neither feature is active.
        bias = None
        if self.use_pos_rab:
            # Learned per-head bias for causal position gap (i - j) in [0, L).
            # Shape (1, H, L, L), broadcast over batch.
            gap = (positions.new_tensor(range(L)).view(L, 1)
                   - positions.new_tensor(range(L)).view(1, L)).clamp_(0, L - 1)
            rb = self.pos_rab_emb(gap)                                       # (L, L, H)
            bias = rb.permute(2, 0, 1).unsqueeze(0)
        if self.use_time_bias and times is not None:
            dt = (times.unsqueeze(2) - times.unsqueeze(1)).clamp_min(0)      # (B, L, L)
            tb = self.time_bias_emb(torch.bucketize(dt, self.time_boundaries))
            tb = tb.permute(0, 3, 1, 2)
            bias = tb if bias is None else bias + tb
        if self.use_time_decay_kernel and times is not None:
            # Continuous learnable decay kernel over log-time gap.
            dt = (times.unsqueeze(2) - times.unsqueeze(1)).clamp_min(0)      # (B, L, L)
            u = torch.log1p(dt.float())                                      # (B, L, L)
            rates = torch.nn.functional.softplus(self.decay_raw_rate)        # (K,)
            # basis: (B, L, L, K) = exp(-rate_k * u)
            phi = torch.exp(-u.unsqueeze(-1) * rates.view(1, 1, 1, -1))
            # mix per head: (B, L, L, K) x (H, K) -> (B, H, L, L)
            tk = torch.einsum("blmk,hk->bhlm", phi, self.decay_mix)
            bias = tk if bias is None else bias + tk
        if self.use_text_sim_bias:
            t = self.sbert_table(input_ids)                                  # (B, L, k), L2-normalized rows
            sims = torch.bmm(t, t.transpose(1, 2)).unsqueeze(1) \
                   * self.textsim_scale.view(1, -1, 1, 1)
            bias = sims if bias is None else bias + sims

        if self.encoder_type == "hstu":
            keep = torch.tril(torch.ones(L, L, dtype=x.dtype, device=device))
            # Prototype-routed expert mixture weights (c1): per-token softmax
            # over experts from the frozen level-0 TAPE assignment. None unless
            # --expert-heads is set (experts are zero-init no-ops regardless).
            route = None
            if self.n_experts > 0:
                a0 = self.proto_assign_0[input_ids]                  # (B, L, K)
                route = F.softmax(self.expert_router(a0), dim=-1)     # (B, L, E)
            h = x
            for layer in self.hstu_layers:
                h = layer(h, bias, keep, route)
            h = self.ln_final(h)
            return h

        causal_bool = torch.triu(torch.ones(L, L, dtype=torch.bool, device=device), diagonal=1)
        if bias is not None:
            base = torch.zeros(L, L, dtype=x.dtype, device=device)
            base = base.masked_fill(causal_bool, float("-inf"))
            mask = base.unsqueeze(0).unsqueeze(0) + bias
            attn_mask = mask.reshape(B * self.n_heads, L, L)
        else:
            attn_mask = causal_bool

        h = self.transformer(x, mask=attn_mask)
        h = self.ln_final(h)                             # (B, L, d)
        return h

    def forward(self, input_ids, times=None):
        """input_ids: (B, L). Returns logits (B, L, n_items).
        Uses causal mask only (no key padding mask). Right-padded sequences
        keep the standard SASRec convention; pad positions still get computed
        but their outputs are masked-out by ignore_index in cross-entropy."""
        h = self.encode(input_ids, times=times)
        all_items = self.all_item_features()             # (n_items, d)
        logits = h @ all_items.T                         # (B, L, n_items)
        return logits


def chunked_full_softmax_loss(hidden, targets, model, pad_id, item_chunk: int = 8192,
                               cosine: bool = False, temp: float = 1.0,
                               label_smoothing: float = 0.0,
                               niche_share_beta: float = 0.0,
                               heat_target: bool = False,
                               cred_route_train: bool = False, cred_k: float = 2.0,
                               dual_head_decorr: float = 0.0,
                               decorr_mode: str = "pearson"):
    """Compute full-softmax cross-entropy in CHUNKS over the item dimension to
    avoid the (B, L, n_items) tensor that would OOM at large catalogs.

    Returns the mean cross-entropy over valid (non-pad) positions.

    Approach: for each valid position, we need log p(target) under softmax over
    all items. The log p = score_target - logsumexp(all scores). We compute
    logsumexp incrementally over chunks of the item dimension, then add the
    target score (gathered once)."""
    valid = (targets != pad_id)
    n_valid = valid.sum().item()
    if n_valid == 0:
        return torch.tensor(0.0, device=hidden.device, requires_grad=True)
    h_v = hidden[valid]                                  # (n_valid, d)
    if cosine:
        # Normalized-temperature scoring (cosine/tau), following the
        # interaction module of HSTU (Zhai et al., 2024) and the
        # HSTU-BLaIR config (Liu, 2025): L2-normalize both sides, divide
        # logits by temperature. Cited, not claimed as novel.
        h_v = F.normalize(h_v, dim=-1, eps=1e-6)
    pos_ids = targets[valid]                             # (n_valid,)
    n_items = model.n_items
    # Incremental logsumexp over item chunks
    lse = torch.full((n_valid,), -float("inf"), device=hidden.device)
    target_scores = None
    # For label smoothing we also need the uniform-over-all-items term
    # E_k[score_k] = (1/n_items) * sum_k score_k, accumulated chunk-wise.
    score_sum = torch.zeros((n_valid,), device=hidden.device) if label_smoothing > 0.0 else None
    # NOVEL cold-start (PROPOSAL 2026-07-03-1, TRAIN-CONSISTENT): parallel logsumexp
    # / target-score / uniform-term accumulators for the HOMOGENEOUS FROZEN-TEXT
    # score space s_txt = h @ sbert_proj(sbert_table).T (the --sbert-only scorer).
    # Only allocated when the routed-training flag is active AND the model has a
    # text channel; otherwise None => the branch below is skipped => bit-identical.
    cred_train = bool(cred_route_train) and getattr(model, "use_sbert", False)
    lse_txt = torch.full((n_valid,), -float("inf"), device=hidden.device) if cred_train else None
    target_scores_txt = None
    score_sum_txt = (torch.zeros((n_valid,), device=hidden.device)
                     if (cred_train and label_smoothing > 0.0) else None)
    for start in range(0, n_items, item_chunk):
        end = min(start + item_chunk, n_items)
        chunk_ids = torch.arange(start, end, device=hidden.device)
        chunk_emb = model.item_features(chunk_ids)       # (chunk, d)
        if cosine:
            chunk_emb = F.normalize(chunk_emb, dim=-1, eps=1e-6)
        chunk_logits = h_v @ chunk_emb.T                 # (n_valid, chunk)
        if cosine:
            chunk_logits = chunk_logits / temp
        # Update logsumexp: lse = logsumexp(lse, max(chunk_logits, axis=-1))
        chunk_max = chunk_logits.max(dim=-1).values      # (n_valid,)
        chunk_lse = chunk_max + torch.log(torch.sum(
            torch.exp(chunk_logits - chunk_max.unsqueeze(-1)), dim=-1))  # (n_valid,)
        lse = torch.logsumexp(torch.stack([lse, chunk_lse], dim=-1), dim=-1)
        if score_sum is not None:
            score_sum = score_sum + chunk_logits.sum(dim=-1)   # (n_valid,)
        # If pos_ids fall in this chunk, grab their score
        in_chunk = (pos_ids >= start) & (pos_ids < end)
        if in_chunk.any():
            local_idx = pos_ids[in_chunk] - start
            scores_here = chunk_logits[in_chunk, local_idx]   # (n_in_chunk,)
            if target_scores is None:
                target_scores = torch.full((n_valid,), -float("inf"), device=hidden.device)
            target_scores[in_chunk] = scores_here
        # NOVEL cold-start (PROPOSAL 2026-07-03-1, TRAIN-CONSISTENT): score the SAME
        # hidden against the homogeneous frozen-text space for this chunk and
        # accumulate its logsumexp / target score / uniform term in lock-step with
        # the CF space above. No-op unless cred_train (bit-identical off-path).
        if cred_train:
            txt_emb = model.sbert_proj(model.sbert_table(chunk_ids))   # (chunk, d)
            if cosine:
                txt_emb = F.normalize(txt_emb, dim=-1, eps=1e-6)
            txt_logits = h_v @ txt_emb.T                              # (n_valid, chunk)
            if cosine:
                txt_logits = txt_logits / temp
            txt_max = txt_logits.max(dim=-1).values
            txt_chunk_lse = txt_max + torch.log(torch.sum(
                torch.exp(txt_logits - txt_max.unsqueeze(-1)), dim=-1))
            lse_txt = torch.logsumexp(torch.stack([lse_txt, txt_chunk_lse], dim=-1), dim=-1)
            if score_sum_txt is not None:
                score_sum_txt = score_sum_txt + txt_logits.sum(dim=-1)
            if in_chunk.any():
                if target_scores_txt is None:
                    target_scores_txt = torch.full((n_valid,), -float("inf"), device=hidden.device)
                target_scores_txt[in_chunk] = txt_logits[in_chunk, pos_ids[in_chunk] - start]
    # NOVEL Y1 (heat-target): replace the hard target numerator (score_y) with a
    # heat-kernel / Gibbs soft target diffused over the frozen text manifold:
    #   q_yj = softmax(cand_sim / T),  soft_num = sum_j q_yj * score_j
    # over {y} ∪ top-m text neighbors. T = softplus(heat_temp); at init T≈0.0025
    # so self-sim 1.0 vs neighbor sims ≤~0.9 => q≈[1,0,..] => soft_num≈score_y =>
    # bit-identical no-op. Training-only (eval untouched); leak-free (frozen text).
    if heat_target and getattr(model, "use_heat", False) and target_scores is not None:
        T = F.softplus(model.heat_temp)
        nbr = model.nbr_idx[pos_ids]                                  # (n_valid, m)
        sim = model.nbr_sim[pos_ids]                                  # (n_valid, m) cosine <1
        cand_ids = torch.cat([pos_ids.unsqueeze(1), nbr], dim=1)      # (n_valid, 1+m)
        cand_sim = torch.cat([torch.ones_like(sim[:, :1]), sim], dim=1)  # self-sim = 1.0 (max)
        q = torch.softmax(cand_sim / T, dim=1)                        # heat weights; T→0 ⇒ delta
        m1 = cand_ids.shape[1]
        cand_emb = model.item_features(cand_ids.reshape(-1)).reshape(n_valid, m1, -1)
        if cosine:
            cand_emb = F.normalize(cand_emb, dim=-1, eps=1e-6)
        cand_score = (h_v.unsqueeze(1) * cand_emb).sum(-1)           # (n_valid, 1+m)
        if cosine:
            cand_score = cand_score / temp
        target_scores = (q * cand_score).sum(dim=1)                  # (n_valid,) soft numerator

    # NOVEL niche-share (W1): subtract a learnable, popularity-weighted crowding
    # penalty from the TARGET logit only (fitness-sharing "divide the focal
    # individual's fitness"). beta zero-init => no-op at start. Applied after
    # target_scores is fully gathered and BEFORE the CE branches, so it carries
    # into both the hard-CE and label-smoothed targets; the lse / mean_score
    # normalizer terms are intentionally left unpenalized (pure target-margin
    # discount). Eval scoring is untouched -> no test leakage.
    if niche_share_beta != 0.0 and getattr(model, "use_niche_share", False):
        pen = model.niche_share_beta * model.niche_crowd[pos_ids]   # (n_valid,)
        target_scores = target_scores - pen
    # NOVEL cold-start (PROPOSAL 2026-07-03-1, TRAIN-CONSISTENT): credibility-ROUTED
    # dual-space CE. Each valid target y is supervised in a per-item Bühlmann blend
    # of the two spaces: L = Z_y*CE(s_full,y) + (1-Z_y)*CE(s_txt,y), with
    # Z_y = n_y/(n_y+k) from the TRAIN-only item_freq. Cold targets (n_y=0 => Z=0)
    # train the frozen-text projection sbert_proj to score STANDALONE (the Finding-2
    # fix); warm targets (Z->1) train the CF space as before. Label smoothing (if on)
    # is applied consistently to BOTH per-position CE terms. Non-learnable route.
    if cred_train:
        _fr = model.item_freq[pos_ids]                                # (n_valid,)
        Zy = _fr / (_fr + float(cred_k))                             # Bühlmann credibility
        if label_smoothing > 0.0:
            eps = label_smoothing
            ce_full = lse - (1.0 - eps) * target_scores - eps * (score_sum / n_items)
            ce_txt = lse_txt - (1.0 - eps) * target_scores_txt - eps * (score_sum_txt / n_items)
        else:
            ce_full = lse - target_scores
            ce_txt = lse_txt - target_scores_txt
        loss = (Zy * ce_full + (1.0 - Zy) * ce_txt).mean()
        # NOVEL cold-start (PROPOSAL 2026-07-03-2): Hui-Walter conditional-
        # independence / error-DECORRELATION penalty. The cred-route-train text
        # head co-adapts into the ID head's shadow (correlated errors), so at the
        # Z->0 cold limit there is no standalone-calibrated text ordering to route
        # into (cred-route-train floored cold hits@10 at 3). Adding a penalty on
        # the batch dependence of the two heads' per-example errors (each already
        # conditioned on the realized target y => a tractable *conditional*-
        # independence proxy, Hui-Walter 1980 / co-training view-independence
        # Blum-Mitchell 1998 / HSIC Gretton 2005) forces the text head toward a
        # standalone relevance metric. dual_head_decorr == 0.0 => term absent =>
        # bit-identical to the plain --cred-route-train run. LEAK-FREE: consults
        # only the two model-score CEs at the realized target; no val/test label.
        if dual_head_decorr > 0.0:
            a = ce_full - ce_full.mean()
            b = ce_txt - ce_txt.mean()
            if decorr_mode == "hsic":
                # Biased HSIC estimator on the two scalar error vectors:
                # HSIC = tr(K H L H)/(m-1)^2 with RBF kernels K,L and centering
                # H = I - 11^T/m. Captures NONLINEAR conditional dependence a
                # residual head can hide behind Pearson's linear-only measure.
                m = ce_full.shape[0]
                if m > 1:
                    ca = ce_full.detach()
                    cb = ce_txt.detach()
                    # median-heuristic RBF bandwidths (detached; scale only)
                    da = (ce_full.unsqueeze(0) - ce_full.unsqueeze(1))
                    db = (ce_txt.unsqueeze(0) - ce_txt.unsqueeze(1))
                    sa = (ca.unsqueeze(0) - ca.unsqueeze(1)).abs().median() + 1e-8
                    sb = (cb.unsqueeze(0) - cb.unsqueeze(1)).abs().median() + 1e-8
                    K = torch.exp(-(da * da) / (2.0 * sa * sa))
                    L = torch.exp(-(db * db) / (2.0 * sb * sb))
                    H = torch.eye(m, device=ce_full.device) - 1.0 / m
                    hsic = torch.trace(K @ H @ L @ H) / ((m - 1) ** 2)
                    loss = loss + dual_head_decorr * hsic
            else:
                # Pearson rung (ship first): drive the LINEAR error-correlation
                # toward 0 (conditional independence proxy).
                rho = (a * b).sum() / (a.norm() * b.norm() + 1e-8)
                loss = loss + dual_head_decorr * rho.pow(2)
        return loss
    # Cross-entropy = -mean(target_score - logsumexp)
    if label_smoothing > 0.0:
        # Standard label smoothing over the full item vocabulary:
        #   L = -(1-eps)*log p(y) - (eps/K) * sum_k log p(k)
        #     = lse - (1-eps)*score_y - eps * E_k[score_k]
        # Exactly reduces to the hard-target CE when eps == 0 (no-op default).
        eps = label_smoothing
        mean_score = score_sum / n_items
        loss = (lse - (1.0 - eps) * target_scores - eps * mean_score).mean()
    else:
        loss = -(target_scores - lse).mean()
    return loss


def cl4srec_aux_loss(model, inputs, times, pad_id, mask_prob: float, tau: float):
    """CL4SRec-style self-supervised contrastive auxiliary loss.

    Two augmented views of each input sequence are produced by INDEPENDENT
    item masking (each non-pad item -> pad_id with prob mask_prob; a valid
    CL4SRec "mask" augmentation that preserves length and time alignment).
    Both views are encoded; the pooled sequence representation is taken at the
    last real position of the ORIGINAL sequence (always non-pad, shared index
    => view correspondence), passed through the projection head, L2-normalized,
    and contrasted with an InfoNCE loss over the batch (positive = the paired
    view of the same sequence; negatives = all other sequences' views).

    Reference: Xie et al. (2022), arXiv:2010.14395. Pure SEQUENCE-space SSL,
    distinct from the text-target distillation aux (c2).
    """
    B, L = inputs.shape
    device = inputs.device
    non_pad = (inputs != pad_id)
    # last real position per sequence (>=0; sequences always have >=1 real item)
    last_idx = (non_pad.sum(dim=1) - 1).clamp_min(0)            # (B,)

    def make_view():
        # mask each real item independently with prob mask_prob
        drop = (torch.rand(B, L, device=device) < mask_prob) & non_pad
        v = inputs.masked_fill(drop, pad_id)
        h = model.encode(v, times=times)                       # (B, L, d)
        rep = h[torch.arange(B, device=device), last_idx]      # (B, d)
        z = model.cl_head(rep)
        return F.normalize(z, dim=-1, eps=1e-6)

    z1 = make_view()                                           # (B, d)
    z2 = make_view()                                           # (B, d)
    logits = (z1 @ z2.T) / tau                                 # (B, B)
    labels = torch.arange(B, device=device)
    return 0.5 * (F.cross_entropy(logits, labels)
                  + F.cross_entropy(logits.T, labels))


def train_one_epoch(model, loader, opt, pad_id, device, grad_clip=5.0,
                      sampled_negs: int = 0, in_batch_negs: bool = False,
                      chunked_full_softmax: bool = False, item_chunk: int = 8192,
                      scheduler=None, cosine: bool = False, temp: float = 1.0,
                      text_distill_weight: float = 0.0,
                      cl_weight: float = 0.0, cl_mask_prob: float = 0.3,
                      cl_tau: float = 1.0, label_smoothing: float = 0.0,
                      niche_share_beta: float = 0.0, heat_target: bool = False,
                      cred_route_train: bool = False, cred_k: float = 2.0,
                      dual_head_decorr: float = 0.0, decorr_mode: str = "pearson"):
    """Training loss modes (in priority order):
      - in_batch_negs=True: use all items in the batch as negatives per
        position (12K+ negs per step at batch=256, much more than sampled-1024;
        free compute since batch items are already in memory).
      - sampled_negs > 0: sampled softmax with K random negatives.
      - default: full softmax over all n_items."""
    model.train()
    total_loss = 0.0
    n_batches = 0
    n_valid_positions = 0
    for batch in loader:
        if len(batch) == 3:
            inputs, targets, times = batch
            times = times.to(device, non_blocking=True)
        else:
            inputs, targets = batch
            times = None
        inputs = inputs.to(device, non_blocking=True)
        targets = targets.to(device, non_blocking=True)

        if chunked_full_softmax:
            # Full softmax via chunked logits — proper baseline for the "sampled
            # softmax is the bottleneck" hypothesis. Memory-bounded by item_chunk.
            hidden = model.encode(inputs, times=times)
            loss = chunked_full_softmax_loss(hidden, targets, model, pad_id,
                                                item_chunk=item_chunk,
                                                cosine=cosine, temp=temp,
                                                label_smoothing=label_smoothing,
                                                niche_share_beta=niche_share_beta,
                                                heat_target=heat_target,
                                                cred_route_train=cred_route_train,
                                                cred_k=cred_k,
                                                dual_head_decorr=dual_head_decorr,
                                                decorr_mode=decorr_mode)
            if text_distill_weight > 0.0 and getattr(model, "use_sbert", False):
                # NOVEL text-distillation aux: align predicted next-item
                # representation with the target item's frozen text embedding.
                valid = (targets != pad_id)
                if valid.any():
                    h_v = hidden[valid]                          # (n_valid, d)
                    tgt_text = model.sbert_table(targets[valid])  # (n_valid, k) frozen, L2-normed
                    pred_text = F.normalize(model.distill_head(h_v), dim=-1, eps=1e-6)
                    aux = (1.0 - (pred_text * tgt_text).sum(-1)).mean()
                    loss = loss + text_distill_weight * aux
            if cl_weight > 0.0 and getattr(model, "cl_aux", False):
                # CL4SRec self-supervised contrastive aux (sequence space).
                cl = cl4srec_aux_loss(model, inputs, times, pad_id,
                                       mask_prob=cl_mask_prob, tau=cl_tau)
                loss = loss + cl_weight * cl
        elif in_batch_negs:
            # In-batch + random negatives (hybrid):
            # Candidate pool = unique items in batch ∪ K random items.
            # In-batch alone causes train-test shift (training discriminates
            # against ~12K batch items, eval against all 207K). Adding random
            # negs samples the full catalog distribution.
            hidden = model.encode(inputs, times=times)   # (B, L, d)
            B, L, d = hidden.shape
            valid = (targets != pad_id)
            n_valid = valid.sum().item()
            if n_valid == 0:
                continue
            h_v = hidden[valid]                           # (n_valid, d)
            pos_ids = targets[valid]                      # (n_valid,)
            uniq_in_batch = torch.unique(pos_ids)         # (n_in_batch,)
            # If sampled_negs > 0, add that many random negatives drawn from
            # the full item catalog (rejection-free; some may overlap with
            # in-batch positives which is fine — they just stay as positives).
            if sampled_negs > 0:
                rand_negs = torch.randint(0, model.n_items, (sampled_negs,),
                                            device=device)
                cand = torch.unique(torch.cat([uniq_in_batch, rand_negs]))
            else:
                cand = uniq_in_batch
            cand_emb = model.item_features(cand)          # (n_cand, d)
            # Map pos_ids into compact cand index
            # pos_ids must all be in cand (in-batch positives are). Build
            # a mapping via searchsorted on the sorted cand.
            sorted_cand, sort_idx = torch.sort(cand)
            pos_in_sorted = torch.searchsorted(sorted_cand, pos_ids)
            pos_compact = sort_idx[pos_in_sorted]
            logits = h_v @ cand_emb.T                     # (n_valid, n_cand)
            loss = F.cross_entropy(logits, pos_compact, reduction="mean")
        elif sampled_negs == 0:
            # Full softmax
            logits = model(inputs, times=times)          # (B, L, n_items)
            B, L, n_items = logits.shape
            loss = F.cross_entropy(logits.reshape(B * L, n_items),
                                     targets.reshape(B * L),
                                     ignore_index=pad_id,
                                     reduction="mean")
        else:
            # Sampled softmax: produce hidden states, sample K negatives,
            # compute cross-entropy over (1 positive + K negatives)
            hidden = model.encode(inputs, times=times)   # (B, L, d)
            B, L, d = hidden.shape
            # Valid positions are where target != pad
            valid = (targets != pad_id)
            n_valid = valid.sum().item()
            if n_valid == 0:
                continue
            # Sample K random items per valid position
            sampled = torch.randint(0, model.n_items, (n_valid, sampled_negs),
                                     device=device)
            # Pos item ids + sampled neg ids
            h_v = hidden[valid]                          # (n_valid, d)
            pos_ids = targets[valid]                     # (n_valid,)
            cand_ids = torch.cat([pos_ids.unsqueeze(1), sampled], dim=1)  # (n_valid, 1 + K)
            cand_emb = model.item_features(cand_ids)     # (n_valid, 1+K, d)
            if cosine:
                h_v = F.normalize(h_v, dim=-1, eps=1e-6)
                cand_emb = F.normalize(cand_emb, dim=-1, eps=1e-6)
            logits = (cand_emb @ h_v.unsqueeze(-1)).squeeze(-1)  # (n_valid, 1+K)
            if cosine:
                logits = logits / temp
            # Cross-entropy with target=0 (first column is positive)
            target = torch.zeros(n_valid, dtype=torch.long, device=device)
            loss = F.cross_entropy(logits, target, reduction="mean")

        opt.zero_grad(); loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
        opt.step()
        if scheduler is not None:
            scheduler.step()
        total_loss += loss.item()
        n_batches += 1
        n_valid_positions += (targets != pad_id).sum().item()
    return total_loss / max(1, n_batches), n_valid_positions


def evaluate(model, user_seqs, test_inters, n_items, pad_id, max_seq_len,
              device, top_k=10, batch_size=512, extra_history=None,
              subsample_users=0, subsample_seed=0, stratify_head=0.0,
              user_times=None, extra_times=None, cosine=False, cold_items=None,
              zfusion=False, credibility_route=False, cred_k=2.0,
              zfusion_weight=0.5, cred_rank_fusion=False, rrf_c=60.0):
    """For each (u, target) in test_inters, encode u's training sequence and
    score the target item against all items. Mask training items. Compute
    NDCG@K, HR@K, MRR.

    Right-padding convention: real items are placed at positions 0..L-1, then
    pad at positions L..max_seq_len-1. The 'next-item prediction' is taken
    from position L-1 (the last REAL item).

    extra_history: optional dict {user_id: [extra_item_ids]} appended to the
    user's training sequence in chronological order. Used for test eval where
    the val item is included in the input."""
    model.eval()
    test_dict = {u: i for u, i, _, _ in test_inters}
    users = sorted(test_dict.keys())
    # Popularity strata (computed once from TRAIN sequences, cached on the model):
    # bucket each item into tail/mid/head terciles by train frequency so we can
    # report NDCG on the long tail — the regime where text/TAPE should beat ID
    # embeddings. Train-only frequency => no leakage; static => cache on model.
    # Computed BEFORE user selection so the stratified subsample can read it.
    if getattr(model, "_eval_item_bucket", None) is None \
            or len(model._eval_item_bucket) != n_items:
        _freq = np.zeros(n_items, dtype=np.int64)
        for _seq in user_seqs.values():
            for _it in _seq:
                if 0 <= _it < n_items:
                    _freq[_it] += 1
        _order = np.argsort(_freq, kind="stable")           # rarest first
        _bucket = np.empty(n_items, dtype=np.int8)
        _t1, _t2 = n_items // 3, 2 * n_items // 3
        _bucket[_order[:_t1]] = 0                            # tail (rarest third)
        _bucket[_order[_t1:_t2]] = 1                         # mid
        _bucket[_order[_t2:]] = 2                            # head (most popular third)
        model._eval_item_bucket = _bucket
    item_bucket = model._eval_item_bucket
    # User selection. Two mutually-exclusive subsample modes (default both OFF =>
    # full eval, bit-identical to the original behaviour):
    #   stratify_head in (0,1): TAIL-PRESERVING stratified subsample — keep ALL
    #     users whose test TARGET is a tail/mid item, subsample only head-target
    #     users to fraction `stratify_head`. Fixed RNG(subsample_seed) => the SAME
    #     eval-user set across arms (text vs ID) and across model seeds. Leak-free:
    #     terciles come from TRAIN freq; the target only decides which users to
    #     KEEP, every kept user still ranks against the FULL n_items catalog.
    #     (cycle-5 FIX: a uniform subsample would shrink the ~38-hit tail to noise.)
    #   subsample_users>0: legacy UNIFORM subsample (periodic-eval speedup only).
    if stratify_head and 0.0 < stratify_head < 1.0:
        rng = np.random.RandomState(subsample_seed)
        keep_lowmid = [u for u in users if item_bucket[test_dict[u]] < 2]
        head_users = [u for u in users if item_bucket[test_dict[u]] == 2]
        n_head_keep = int(round(len(head_users) * stratify_head))
        if 0 < n_head_keep < len(head_users):
            head_keep = rng.choice(head_users, n_head_keep, replace=False).tolist()
        else:
            head_keep = head_users
        users = sorted(keep_lowmid + head_keep)
    elif subsample_users and subsample_users < len(users):
        rng = np.random.RandomState(subsample_seed)
        users = sorted(rng.choice(users, subsample_users, replace=False).tolist())
    n_eval = len(users)
    extra = extra_history or {}
    cold_set = cold_items if cold_items is not None else set()
    ndcg, hr, rr, bkt, cld = [], [], [], [], []
    # rnk: full 0-indexed rank of each test target (sentinel n_items for the
    # no-history skip case). Captured so by_coldstart can report COARSER cutoffs
    # (NDCG/HR@{50,100}) — the cold-item metric is on the FLOOR at @10 (0 hits /
    # 8748 cold targets, all 3 arms, 2026-06-23), so @10 has zero resolving power
    # to distinguish ID-only / text-stack / conn-gate. Coarser cutoffs + MRR are
    # the resolving metrics. ADD-ONLY: by_popularity and the @10 keys are
    # untouched (paper tables stay bit-identical); only by_coldstart gains keys.
    rnk = []
    print(f"  evaluating {n_eval:,} users in batches of {batch_size}...")
    t0 = time.time()
    with torch.no_grad():
        # Cache the (n_items, d_model) item-features table ONCE per eval call
        # to avoid recomputing the MLP forward over all items for every batch
        # (a 1000x speedup for large catalogs at d_model >= 64).
        all_items = model.all_item_features()        # (n_items, d)
        if cosine:
            all_items = F.normalize(all_items, dim=-1, eps=1e-6)
        # COMPARATOR (--zfusion-eval): precompute the unit frozen-text table ONCE
        # for the z-score late-fusion cold-start bar. sb_norm[j] is item j's L2-
        # normalized SBERT vector (retained for ALL items incl. true-cold). OFF =>
        # None => the fusion branch below is skipped => scores bit-identical.
        sb_norm = None
        if zfusion and getattr(model, "use_sbert", False):
            _sb = model.sbert_table.weight[:n_items].to(device).float()
            sb_norm = F.normalize(_sb, dim=-1, eps=1e-6)     # (n_items, sbert_dim)
        # NOVEL --credibility-route (PROPOSAL 2026-07-03-1): precompute ONCE the
        # homogeneous frozen-text score space Ptext = sbert_proj(sbert_table) (the
        # exact --sbert-only scorer, projected into the d-dim hidden space) and the
        # per-candidate Bühlmann credibility weight Z_j = n_j/(n_j+k) from TRAIN-only
        # frequency. OFF or no SBERT => None => merge branch below is skipped =>
        # scores bit-identical. LEAK-FREE: item_freq is train-only (from user_seqs,
        # the same source as the leak-free popularity terciles above); the text
        # table is frozen; z-standardization (in the loop) is over candidates only.
        cred_ptext = None
        cred_Z = None
        if credibility_route and getattr(model, "use_sbert", False):
            with torch.no_grad():
                _ids = torch.arange(n_items, device=device)
                cred_ptext = model.sbert_proj(model.sbert_table(_ids))  # (n_items, d)
            # TRAIN-only per-item interaction count (== the tercile freq source).
            _cf = torch.zeros(n_items, device=device)
            for _seq in user_seqs.values():
                for _it in _seq:
                    if 0 <= _it < n_items:
                        _cf[_it] += 1.0
            cred_Z = _cf / (_cf + float(cred_k))              # (n_items,) in [0,1)
        use_times = (getattr(model, "use_time_bias", False)
                     or getattr(model, "use_time_decay_kernel", False)) \
                    and user_times is not None
        xtimes = extra_times or {}
        for s in range(0, n_eval, batch_size):
            batch_users = users[s:s + batch_size]
            # Right-padded inputs (train + optional extra_history)
            input_ids = torch.full((len(batch_users), max_seq_len), pad_id,
                                     dtype=torch.long, device=device)
            times_t = (torch.zeros((len(batch_users), max_seq_len),
                                    dtype=torch.long, device=device)
                       if use_times else None)
            train_items = []
            train_times = []
            for u in batch_users:
                seq = list(user_seqs.get(u, []))
                if u in extra:
                    seq = seq + list(extra[u])
                train_items.append(seq)
                if use_times:
                    tms = list(user_times.get(u, []))
                    if u in xtimes:
                        tms = tms + list(xtimes[u])
                    train_times.append(tms)
            real_len = []
            for k, items in enumerate(train_items):
                if not items:
                    real_len.append(0); continue
                truncated = items[-max_seq_len:]
                input_ids[k, :len(truncated)] = torch.tensor(truncated,
                                                                dtype=torch.long,
                                                                device=device)
                if use_times:
                    trunc_t = train_times[k][-max_seq_len:]
                    times_t[k, :len(trunc_t)] = torch.tensor(trunc_t,
                                                              dtype=torch.long,
                                                              device=device)
                real_len.append(len(truncated))
            # Memory-efficient: compute hidden states then score ONLY the
            # last real position against all items. Avoids materializing the
            # full (B, L, n_items) logits tensor — critical for n_items >> 50K.
            hidden = model.encode(input_ids, times=times_t)  # (B, L, d)
            B = len(batch_users)
            last_real_pos = torch.tensor([max(0, rl - 1) for rl in real_len],
                                          device=device)
            last_h = hidden[torch.arange(B, device=device), last_real_pos, :]  # (B, d)
            if cosine:
                last_h = F.normalize(last_h, dim=-1, eps=1e-6)
            final = last_h @ all_items.T                 # (B, n_items)

            # COMPARATOR (--zfusion-eval): z-score LATE FUSION of the warm-trained
            # model score with a mean-text content-profile cosine score — the
            # protocol-matched hybrid CF+content cold-start incumbent bar. Build
            # each user's content profile as the mean unit-text vector of their
            # (train+val) history, score all items by cosine, z-normalize BOTH the
            # model score and the content score across the candidate axis, and sum.
            # This lets cold items (which the ID model floors) be ranked by their
            # frozen text. Train-free, eval-only; masking/ranking below unchanged.
            if sb_norm is not None:
                prof = torch.zeros((B, sb_norm.shape[1]), device=device)
                for k, items in enumerate(train_items):
                    if items:
                        idx = torch.tensor(items, dtype=torch.long, device=device)
                        prof[k] = sb_norm[idx].mean(dim=0)
                prof = F.normalize(prof, dim=-1, eps=1e-6)    # (B, sbert_dim)
                content = prof @ sb_norm.T                    # (B, n_items)
                def _zc(x):
                    return (x - x.mean(dim=1, keepdim=True)) \
                           / x.std(dim=1, keepdim=True).clamp_min(1e-8)
                # ANALYST missing-ablation #2 (ANALYSIS 2026-07-03-1): TUNED fusion
                # weight, replacing the un-tuned 1:1 sum so the LC2C-proxy gets a
                # fair shot (does ANY content weight rank cold@10 without denting
                # warm?). w = zfusion_weight is the CONTENT share in [0,1]; the 2x
                # keeps w=0.5 EXACTLY equal to the prior `_zc(final)+_zc(content)`
                # (2*(0.5a+0.5b)=a+b) => all prior --zfusion-eval runs stay
                # bit-identical (default 0.5). w->0 = pure CF (baseline ranking),
                # w->1 = pure equated content (the cold-ranking regime). Non-learned
                # (a swept hyperparameter, NOT a scalar that can vote itself off).
                w = float(zfusion_weight)
                final = 2.0 * ((1.0 - w) * _zc(final) + w * _zc(content))

            # NOVEL --credibility-route (PROPOSAL 2026-07-03-1): score-level dual-
            # space, scale-equated, count-routed merge. s_txt scores the SAME hidden
            # against the homogeneous text space; z-standardize both over the
            # candidate axis, then per-candidate Bühlmann route Z_j*z_full +
            # (1-Z_j)*z_txt. Cold (n_j=0 => Z_j=0) ranks by pure equated text (the
            # sbert-only regime); warm (Z_j->1) by the CF space. Masking below is
            # unchanged. Eval-only; no gradient; leak-free (see precompute note).
            if cred_ptext is not None:
                s_txt = last_h @ cred_ptext.T                 # (B, n_items)
                if cred_rank_fusion:
                    # NOVEL rank-level calibration (SUPERVISOR cycle-20 granted
                    # probe): the ANALYST's FINDING 3 showed the co-trained /
                    # credibility-routed text head DOES rank cold items into the
                    # top-100 (HSIC cold hit@100=225) but the SCORE-level z-equate
                    # merge cannot surface them to @10 — the warm CF z-distribution
                    # has a wider spread, so `Z*zf + (1-Z)*zt` lets the CF axis
                    # dominate the head of the ranking even for cold (Z->0) items
                    # once the two z-scaled axes are summed candidate-wise. Rank
                    # fusion is SCALE-FREE: convert each head to per-candidate
                    # reciprocal rank rr = 1/(c + rank) (rank 0 = best in that
                    # head), then credibility-route the reciprocal ranks:
                    #   final_j = Z_j * rr_full_j + (1 - Z_j) * rr_txt_j.
                    # Cold (n_j=0 => Z_j=0) is then ranked by pure text reciprocal
                    # rank (a #30-in-text cold item gets 1/(c+30) irrespective of
                    # how the CF magnitudes are spread), directly attacking the
                    # top-rank calibration failure FINDING 3 diagnosed. c=rrf_c is
                    # the standard RRF damping constant (non-learnable). Eval-only,
                    # no gradient; leak-free (same precompute as the z-equate path).
                    # rank_full_j = # candidates strictly better than j in the CF
                    # head; argsort(argsort(descending)) gives the 0-indexed rank.
                    rf = final.argsort(dim=1, descending=True).argsort(dim=1).float()
                    rt = s_txt.argsort(dim=1, descending=True).argsort(dim=1).float()
                    rr_full = 1.0 / (float(rrf_c) + rf)
                    rr_txt = 1.0 / (float(rrf_c) + rt)
                    final = cred_Z.unsqueeze(0) * rr_full \
                            + (1.0 - cred_Z).unsqueeze(0) * rr_txt
                else:
                    def _zc2(x):
                        return (x - x.mean(dim=1, keepdim=True)) \
                               / x.std(dim=1, keepdim=True).clamp_min(1e-8)
                    zf = _zc2(final)
                    zt = _zc2(s_txt)
                    final = cred_Z.unsqueeze(0) * zf + (1.0 - cred_Z).unsqueeze(0) * zt

            # Sanity: detect NaN (should never happen now)
            if torch.isnan(final).any():
                raise RuntimeError(f"NaN logits at batch starting {s}; check architecture.")

            # Mask the user's full input history (train + any extras like val)
            # — train_items above already concatenates them.
            for k, items in enumerate(train_items):
                if items:
                    final[k, items] = -float("inf")
            # Rank the target
            for k, u in enumerate(batch_users):
                tgt = test_dict[u]
                b = int(item_bucket[tgt])
                _is_cold = tgt in cold_set
                if real_len[k] == 0:
                    # No training history — skip (shouldn't happen with 5-core)
                    ndcg.append(0.0); hr.append(0.0); rr.append(0.0)
                    bkt.append(b); cld.append(_is_cold)
                    rnk.append(n_items); continue   # sentinel rank => never a hit
                tgt_score = final[k, tgt].item()
                rank0 = int((final[k] > tgt_score).sum().item())
                if rank0 < top_k:
                    ndcg.append(1.0 / math.log2(rank0 + 2))
                    hr.append(1.0)
                else:
                    ndcg.append(0.0); hr.append(0.0)
                rr.append(1.0 / (rank0 + 1))
                bkt.append(b); cld.append(_is_cold)
                rnk.append(rank0)
            if (s // batch_size) % 10 == 0:
                print(f"    [{s + len(batch_users):,}/{n_eval:,}  elapsed {time.time()-t0:.1f}s]")
    print(f"  eval done in {time.time()-t0:.1f}s")
    ndcg_a, hr_a, rr_a, bkt_a = (np.array(ndcg), np.array(hr),
                                  np.array(rr), np.array(bkt))
    rnk_a0 = np.array(rnk, dtype=np.int64)
    by_pop = {}
    for _bid, _name in ((0, "tail"), (1, "mid"), (2, "head")):
        _m = bkt_a == _bid
        if _m.any():
            _r = rnk_a0[_m]
            # @10 kept bit-identical to prior runs; @20/@50/@100 + hit counts added
            # so the tail-tercile effect can be tested at hundreds of hits (not ~30),
            # defusing the tiny-base variance concern. HR@K / n_hit@K from ranks.
            entry = {"NDCG@10": float(ndcg_a[_m].mean()),
                      "HR@10": float(hr_a[_m].mean()),
                      "n": int(_m.sum()),
                      "n_hit@10": int((_r < 10).sum())}
            for _K in (20, 50, 100):
                entry[f"HR@{_K}"] = float((_r < _K).mean())
                entry[f"n_hit@{_K}"] = int((_r < _K).sum())
            by_pop[_name] = entry
    res = {
        "NDCG@10": float(ndcg_a.mean()) if len(ndcg_a) else 0.0,
        "HR@10":   float(hr_a.mean()) if len(hr_a) else 0.0,
        "MRR":     float(rr_a.mean()) if len(rr_a) else 0.0,
        "n_eval":  len(users),
        "by_popularity": by_pop,
    }
    # Audit provenance (Codex F2/fix#5): per-user records so bootstrap / tie /
    # rank diagnostics are reproducible from the artifact. Caller pops this key
    # before JSON-dumping the summary and writes it to a sidecar file.
    res["_user_records"] = {
        "user_id": [int(u) for u in users],
        "target_item_id": [int(test_dict[u]) for u in users],
        "rank0": [int(r) for r in rnk],
        "ndcg10": [float(x) for x in ndcg],
        "hr10": [float(x) for x in hr],
        "rr": [float(x) for x in rr],
        "pop_bucket": [int(b) for b in bkt],
    }
    if by_pop:
        print("  by-popularity NDCG@10: " +
              "  ".join(f"{k}={v['NDCG@10']:.4f}(n={v['n']:,})" for k, v in by_pop.items()))
    # NOVEL cold-start (PROPOSAL 2026-06-22-1): split metrics by whether the test
    # TARGET is a held-out cold item. Only emitted when a cold split is active so
    # non-cold runs stay bit-identical. cold-item NDCG/HR is the headline metric.
    if cold_items is not None:
        cld_a = np.array(cld, dtype=bool)
        rnk_a = np.array(rnk, dtype=np.int64)
        by_cold = {}
        # Coarser cutoffs: @10 is on the floor for cold items (0 hits / 8748,
        # all arms) => add @20/@50/@100 + MRR so the cold arms can be DISTINGUISHED
        # at all. NDCG@K = 1/log2(rank0+2) if rank0<K else 0; HR@K = 1[rank0<K].
        # MRR (= mean 1/(rank0+1)) is the always-resolving full-rank metric.
        _cutoffs = (10, 20, 50, 100)
        for _flag, _name in ((True, "cold"), (False, "warm")):
            _m = cld_a == _flag
            if _m.any():
                _r = rnk_a[_m]
                entry = {"NDCG@10": float(ndcg_a[_m].mean()),
                          "HR@10": float(hr_a[_m].mean()),
                          "MRR": float(rr_a[_m].mean()),
                          "n": int(_m.sum()),
                          "n_hit": int(hr_a[_m].sum())}
                for _K in _cutoffs:
                    _within = _r < _K
                    _ndcgK = np.where(_within, 1.0 / np.log2(_r + 2.0), 0.0)
                    entry[f"NDCG@{_K}"] = float(_ndcgK.mean())
                    entry[f"HR@{_K}"] = float(_within.mean())
                    entry[f"n_hit@{_K}"] = int(_within.sum())
                by_cold[_name] = entry
        res["by_coldstart"] = by_cold
        if by_cold:
            print("  by-coldstart cold-resolving metrics: " +
                  "  ".join(f"{k}[NDCG@50={v['NDCG@50']:.5f} MRR={v['MRR']:.5f} "
                            f"hits@50={v['n_hit@50']} hits@100={v['n_hit@100']} n={v['n']:,}]"
                            for k, v in by_cold.items()))
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("category", help="Category (Video_Games, Beauty_and_Personal_Care, ...)")
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--batch-size", type=int, default=256)
    ap.add_argument("--max-seq-len", type=int, default=50)
    ap.add_argument("--d-model", type=int, default=64)
    ap.add_argument("--n-layers", type=int, default=2)
    ap.add_argument("--n-heads", type=int, default=2)
    ap.add_argument("--dropout", type=float, default=0.2)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--no-sbert", action="store_true", help="Disable SBERT augmentation")
    ap.add_argument("--sbert-only", action="store_true",
                     help="Use ONLY frozen-SBERT projection as item embedding "
                          "(no learned per-item table). Tests whether shared "
                          "content embedding suffices at huge catalogs.")
    ap.add_argument("--encoder-cache", default=None,
                     help="Override the default sbert_titles_<cat>.npy cache "
                          "path (e.g. cache_5core/blair_titles_<cat>.npy for BLaIR).")
    ap.add_argument("--mlp-adaptor", action="store_true",
                     help="Replace single-Linear projection with 2-layer MLP "
                          "Dropout->Linear(sbert_dim, mlp_hidden)->ReLU->Dropout->"
                          "Linear(mlp_hidden, d_model). Matches the faithful "
                          "SASRecText AdaptorLayer in external/AmazonReviews2023.")
    ap.add_argument("--mlp-hidden", type=int, default=300,
                     help="Hidden dim of the MLP adaptor (default 300 = SASRecText default)")
    ap.add_argument("--mlp-dropout", type=float, default=0.2,
                     help="Dropout inside the MLP adaptor (default 0.2 = SASRecText default)")
    ap.add_argument("--eval-every", type=int, default=5)
    ap.add_argument("--eval-subsample", type=int, default=0,
                     help="Subsample N users for periodic eval (full eval at the end). 0 = full set always.")
    ap.add_argument("--eval-stratify-head", type=float, default=0.0,
                     help="TAIL-PRESERVING stratified eval (cycle-5 FIX). 0=OFF (full "
                          "eval, exact no-op). In (0,1): keep ALL tail+mid-target users, "
                          "subsample head-target users to this fraction (e.g. 0.10). Fixed "
                          "user set across arms/seeds; every kept user ranks vs the full "
                          "catalog. Use for large-catalog datasets (Beauty 207k items) where "
                          "a uniform subsample would shrink the ~38-hit tail bucket to noise.")
    ap.add_argument("--subsample-train-frac", type=float, default=1.0,
                     help="DATA-ABLATION (PROPOSAL 2026-06-18-1, density titration; NOT a model "
                          "lever, zero new params). Keep this fraction of TRAIN interactions "
                          "(default 1.0 = bit-identical no-op). Thins ONLY training data; eval "
                          "conditioning histories + tail/mid/head terciles are frozen from FULL "
                          "density (eval uses the full user_seqs), so the ONLY manipulated variable "
                          "is global training density. Leak-free (val/test never thinned). Lets one "
                          "dataset trace text-ID tail-Delta vs density (rarefaction / dose-response).")
    ap.add_argument("--subsample-mode", choices=("interaction", "user"), default="interaction",
                     help="--subsample-train-frac mode: 'interaction' drops train interactions "
                          "i.i.d. (lowers interactions/item AND users/item); 'user' keeps a fraction "
                          "of users with all their interactions (robustness check vs history-length).")
    ap.add_argument("--subsample-seed", type=int, default=0,
                     help="RNG seed for --subsample-train-frac thinning (default 0).")
    ap.add_argument("--sampled-negs", type=int, default=0,
                     help="If >0, use sampled softmax with this many negatives "
                          "per position (avoids OOM when n_items is huge). "
                          "0 = full softmax over all n_items.")
    ap.add_argument("--in-batch-negs", action="store_true",
                     help="Use all batch items as negatives per position "
                          "(much denser gradient than --sampled-negs at no extra cost). "
                          "Overrides --sampled-negs.")
    ap.add_argument("--chunked-full-softmax", action="store_true",
                     help="Compute full softmax loss over all n_items via chunked "
                          "logits (avoids OOM). Use this when n_items is huge and you "
                          "want the proper full-softmax baseline.")
    ap.add_argument("--item-chunk", type=int, default=8192,
                     help="Chunk size for --chunked-full-softmax")
    ap.add_argument("--augment-factor", type=int, default=1,
                     help="Number of random subsequences sampled per user per epoch "
                          "(1 = original SASRec, 2-5 = standard augmentation). "
                          "Each subsequence has start position uniformly sampled within "
                          "the user's history.")
    ap.add_argument("--seed", type=int, default=42,
                     help="Random seed for torch + numpy. Controls weight init, "
                          "dropout, shuffle, augmentation. For multi-seed experiments.")
    ap.add_argument("--lr-schedule", choices=("none", "warmup_cosine"), default="none",
                     help="Optional LR schedule. 'warmup_cosine' uses 5%% warmup + cosine decay to 0.")
    ap.add_argument("--time-bias", action="store_true",
                     help="Relative time-bucket attention bias from interaction "
                          "timestamps (TiSASRec/HSTU-style additive bias; not "
                          "claimed as novel). Zero-init = no-op at start.")
    ap.add_argument("--text-sim-bias", action="store_true",
                     help="Add per-head learnable scale * cos(text_i, text_j) to "
                          "attention logits. Zero-init = no-op at start.")
    ap.add_argument("--text-prototypes", type=str, default="0",
                     help="K>0 enables Text-Anchored Prototype Embeddings (TAPE): "
                          "k-means the frozen text embeddings into K clusters, "
                          "freeze soft assignments, learn a K x d prototype table "
                          "added to item features. Zero-init = no-op at start. "
                          "Comma list (e.g. '64,512') enables hierarchical TAPE "
                          "with one level per K.")
    ap.add_argument("--cosine-scoring", action="store_true",
                     help="L2-normalize hidden states and item features and "
                          "divide logits by --score-temp, in both training loss "
                          "and evaluation (normalized-temperature scoring per "
                          "HSTU / HSTU-BLaIR; cited, not claimed as novel).")
    ap.add_argument("--score-temp", type=float, default=0.05,
                     help="Temperature for --cosine-scoring (HSTU-BLaIR uses 0.05).")
    ap.add_argument("--text-distill-weight", type=float, default=0.0,
                     help="Weight of the NOVEL text-distillation auxiliary loss: "
                          "aligns each predicted next-item hidden state with the "
                          "target item's frozen text embedding (1 - cosine). "
                          "0 = off. Try 0.1-0.5.")
    ap.add_argument("--text-init-emb", action="store_true",
                     help="Warm-start the trainable item-ID embedding table from "
                          "the top-d PCA of the frozen text embeddings (rescaled to "
                          "std 0.02), then train it freely. Distinct from the "
                          "additive frozen-text side feature. Default OFF.")
    ap.add_argument("--pos-rab", action="store_true",
                     help="Learnable relative-position attention bias (rab_p): "
                          "a per-head bias for each causal position gap |i-j|. "
                          "HSTU's signature mechanism (Zhai et al., 2024); cited. "
                          "Zero-init = no-op at start.")
    ap.add_argument("--encoder", choices=("transformer", "hstu"), default="transformer",
                     help="Sequence encoder: softmax Transformer (SASRec default) "
                          "or HSTU-style pointwise-attention stack "
                          "(Zhai et al., 2024 — cited, not claimed as novel).")
    ap.add_argument("--proto-tau", type=float, default=0.05,
                     help="Softmax temperature for TAPE soft assignments (cosine "
                          "space; smaller = sharper).")
    ap.add_argument("--time-decay-kernel", action="store_true",
                     help="NOVEL continuous learnable time-decay attention kernel: "
                          "replaces the 12-bucket --time-bias lookup with a smooth "
                          "per-head mixture of learnable exponential decays over "
                          "log-time gap. Zero-init = no-op at start.")
    ap.add_argument("--time-decay-bases", type=int, default=8,
                     help="Number of learnable decay basis functions for "
                          "--time-decay-kernel (geometric timescale spread).")
    ap.add_argument("--expert-heads", type=int, default=0,
                     help="NOVEL prototype-routed expert value-heads (c1): E "
                          "zero-init expert linear maps add routed deltas to the "
                          "HSTU V branch; per-token mixture comes from the frozen "
                          "TAPE soft assignment. Requires --text-prototypes. "
                          "0 = off (no-op). Try 4-8.")
    ap.add_argument("--cl-weight", type=float, default=0.0,
                    help="NOVEL: weight of the CL4SRec-style self-supervised "
                         "contrastive auxiliary loss (Xie et al. 2022). 0.0 = OFF "
                         "(default, bit-identical to baseline). Typical 0.1.")
    ap.add_argument("--cl-mask-prob", type=float, default=0.3,
                    help="Item-mask augmentation probability for the two "
                         "contrastive views (CL4SRec mask augmentation).")
    ap.add_argument("--cl-tau", type=float, default=1.0,
                    help="InfoNCE temperature for the contrastive aux loss.")
    ap.add_argument("--label-smoothing", type=float, default=0.0,
                    help="Label-smoothing eps for the chunked-full-softmax CE "
                         "(default 0.0 = OFF, bit-identical to hard-target CE). "
                         "Probe U1: classic remedy for the val>>test "
                         "overconfidence signature; redistributes eps mass "
                         "uniformly over the full item vocabulary.")
    ap.add_argument("--ema-decay", type=float, default=0.0,
                     help="Weight-space EMA (SWA-style) for eval only: maintain a "
                          "shadow exponential moving average of model parameters "
                          "(updated once per epoch) and evaluate val+test on the "
                          "averaged weights. Training is left bit-identical "
                          "(passive shadow); only eval weights differ. Targets the "
                          "LLOO val/test sharp-minima overfit signature. "
                          "0 = off (eval on live weights). Try 0.8-0.95.")
    ap.add_argument("--causal-filter", action="store_true",
                     help="NOVEL probe V1 (RESEARCH_QUEUE 2026-06-16-1): insert ONE "
                          "strictly-causal per-channel learnable temporal FIR filter "
                          "(depthwise Conv1d, left-padded) as a zero-init gated residual "
                          "on the sequence embeddings, just before the encoder stack. "
                          "Leak-free causal realization of the FMLP-Rec/BSARec learnable "
                          "frequency filter (bidirectional in the source papers; made "
                          "causal here for the all-position next-item loss). Tests whether "
                          "attention's low-pass oversmoothing is an in-environment "
                          "bottleneck. Gate zero-init => exact no-op at start. Default OFF.")
    ap.add_argument("--filter-kernel", type=int, default=50,
                     help="FIR kernel length K for --causal-filter (default 50 = "
                          "max_seq_len). Kernel init = causal delta (all-pass) so the "
                          "filter begins as identity and learns to deviate.")
    ap.add_argument("--js-shrink", action="store_true",
                     help="NOVEL probe X1 (RESEARCH_QUEUE 2026-06-16-3): frequency-adaptive "
                          "James–Stein / Efron–Morris shrinkage of each item's learned id-"
                          "embedding TOWARD its TAPE semantic-cluster mean m_i, intensity "
                          "lambda_i = c/(c+n_i) modulated by the item's TRAIN-only interaction "
                          "count n_i (rare items shrink most, head items keep their vector). "
                          "c = softplus(shrink_c), shrink_c zero-init at -8.0 ⇒ c≈0 ⇒ lambda≈0 "
                          "⇒ exact no-op at init. Requires --text-prototypes (TAPE). Leak-free: "
                          "train-only n_i, representation-side (eval scoring untouched). The first "
                          "capacity-REDUCING, sparsity-adaptive lever. Source: Stein 1956 / "
                          "James-Stein 1961 / Efron-Morris 1973. Default OFF.")
    ap.add_argument("--heat-target", action="store_true",
                     help="NOVEL probe Y1 (RESEARCH_QUEUE 2026-06-16-4): heat-kernel / "
                          "manifold-diffusion label smoothing. Replaces CE's Dirac target "
                          "with a Gibbs distribution diffused along the frozen text (SBERT) "
                          "manifold — mass spreads from the target to its top-m semantic "
                          "neighbors with weights softmax(sim/T), T=softplus(heat_temp) a "
                          "single learnable diffusion temperature (init -6 ⇒ T≈0.0025 ⇒ "
                          "delta target ⇒ exact no-op at init). The geometry-aware "
                          "generalization of uniform label smoothing (the T→∞ limit). "
                          "Requires --text-prototypes (reuses the frozen SBERT matrix). "
                          "Leak-free: frozen text only, TRAINING-only (eval scoring untouched). "
                          "Sources: heat kernel/Gibbs measure; GraphHeat (Xu 2020); cite & "
                          "differentiate arXiv:2410.06536 (collaborative-graph soft labels). "
                          "Default OFF.")
    ap.add_argument("--heat-neighbors", type=int, default=20,
                     help="m = number of top-cosine text neighbors that receive diffused "
                          "soft-target mass under --heat-target (default 20).")
    ap.add_argument("--fitness-gate", action="store_true",
                     help="NOVEL probe Z1 (RESEARCH_QUEUE 2026-06-17-1, TAIL mission): "
                          "exposure-gated cold-item routing. For COLD/low-exposure items, "
                          "DAMP the noisy learned ID vector toward the fully-observed frozen-"
                          "text channel (sbert_proj+TAPE), via a NON-LEARNABLE gate g_i = "
                          "1 - alpha*sigmoid(-slope*(log1p(freq_i) - tau)), tau = the train "
                          "tail/mid tercile boundary. Head items (freq>>tau) keep g~1; cold "
                          "items (freq<<tau) get g~1-alpha. NON-LEARNABLE by design (no scalar "
                          "to vote off, unlike W1/X1/Y1). Primary metric = tail-tercile NDCG@10. "
                          "Leak-free (train-only freq+tau; representation-side, eval untouched). "
                          "Source: Bianconi-Barabasi fitness (2001) + Good-Turing/Chao1 coverage; "
                          "cf. CDN (KDD2023). Default OFF.")
    ap.add_argument("--fitness-gate-alpha", type=float, default=0.0,
                     help="Damping strength alpha for --fitness-gate (0.0 = exact no-op; "
                          "1.0 = fully remove the ID channel for the coldest items).")
    ap.add_argument("--fitness-gate-slope", type=float, default=4.0,
                     help="Sigmoid slope for the --fitness-gate schedule (default 4.0).")
    ap.add_argument("--cue-fusion", action="store_true",
                     help="NOVEL probe CF1 (RESEARCH_QUEUE 2026-06-17-3): reliability-"
                          "weighted (inverse-variance) fusion of the ID and frozen-text "
                          "channels (multisensory inverse effectiveness). NON-learnable "
                          "(weights = train-only freq x frozen-text distinctiveness, no "
                          "scalar to vote off); representation-side; mid-regime-targeted. "
                          "Requires text. Default OFF => exact no-op.")
    ap.add_argument("--cue-fusion-mode", choices=("sum2", "sum1"), default="sum2",
                     help="sum2 = weights sum to 2 (mass-preserving vs plain add); "
                          "sum1 = Bayesian sum-to-1 (default sum2).")
    ap.add_argument("--cue-fusion-nbr", type=int, default=20,
                     help="K nearest text-neighbors for the text-distinctiveness precision (default 20).")
    ap.add_argument("--spectral-shrink", action="store_true",
                     help="NOVEL probe GD1 (RESEARCH_QUEUE 2026-06-17-2): per-epoch "
                          "parameter-free Gavish-Donoho/Marchenko-Pastur singular-value "
                          "shrinkage of the item-embedding matrix (the item-axis-spectrum "
                          "dual of the causal temporal filter). NON-learnable (threshold "
                          "data-derived from the SVD spectrum + aspect ratio) => cannot be "
                          "voted off. Training-only, representation-side (eval scoring "
                          "untouched). Default OFF => exact no-op. Also logs the effective "
                          "rank + per-tercile BBP detectability (the directive-(c) "
                          "irreducibility diagnostic).")
    ap.add_argument("--spectral-shrink-every", type=int, default=1,
                     help="Apply --spectral-shrink every K epochs (default 1).")
    ap.add_argument("--spectral-shrink-mode", choices=("hard", "optimal"), default="hard",
                     help="hard = zero singular values below the GD/MP edge; optimal = "
                          "GD optimal shrinker (default hard).")
    ap.add_argument("--niche-share-beta", type=float, default=0.0,
                     help="NOVEL probe W1 (RESEARCH_QUEUE 2026-06-16-2): enable an "
                          "ecology fitness-sharing crowding penalty on the full-softmax "
                          "CE target logit. Discounts targets in crowded, popular semantic "
                          "niches (crowd = A @ (A^T pop), pop from TRAIN interactions only). "
                          "beta is a zero-init LEARNABLE scalar — this float just ENABLES "
                          "the path; the magnitude is learned. Requires --text-prototypes "
                          "+ --chunked-full-softmax. Leak-free: train-only popularity, "
                          "penalty applied at TRAINING only (eval scoring untouched). "
                          "Default 0.0 = OFF (bit-identical no-op). Source: Goldberg & "
                          "Richardson 1987; CS analogues DPP/PD/logit-adjustment cited.")
    ap.add_argument("--out", default=None)
    ap.add_argument("--conn-gate", action="store_true",
                     help="NOVEL cold-start application: connectivity-gated ID<->text "
                          "fusion. Gates the mix on TRAIN distinct users/item (the causal "
                          "axis from the user-mode titration) — down-weight the under-"
                          "trained ID vector and up-weight frozen text for LOW-connectivity "
                          "(cold) items. Learnable, exact no-op at init.")
    # NOVEL (PROPOSAL 2026-06-22-1, USER-DIRECTED cold-start study): a true
    # leave-items-out item cold-start split. A deterministic fraction of item
    # IDs is held out of ALL training (their item_emb never trains; frozen
    # sbert_table is retained for all items), and these COLD items remain valid/
    # test TARGETS. evaluate() then reports by_coldstart={cold,warm}. frac=0.0 =>
    # exact no-op (bit-identical to the non-cold run). Leak-free: cold set is
    # sampled from item IDs only, never from val/test rows.
    ap.add_argument("--cold-item-frac", type=float, default=0.0,
                     help="NOVEL cold-start: fraction of item IDs held out of ALL "
                          "training (item cold-start). 0.0 => no-op. Cold items stay "
                          "valid/test TARGETS; frozen text retained; item_users=0.")
    ap.add_argument("--cold-item-seed", type=int, default=1,
                     help="RandomState seed for the deterministic cold-item set "
                          "(shared across arms for a paired comparison).")
    # NOVEL (PROPOSAL 2026-06-23-1): synthetic connectivity for zero-interaction
    # cold items. For each COLD item (item never in train => its item_emb row is
    # untrained/random), replace the ID channel with a frozen-text-kNN weighted
    # sum of the LEARNED warm-item ID embeddings: e_cold = Sum_k w_ik*item_emb[n_ik]
    # (+ the frozen text path on top, unchanged). Warm items: untouched. The
    # neighbors n_ik are the top-K frozen-text cosine neighbors among WARM items
    # only; weights w_ik = softmax(cos/temp). Parameter-free (non-learnable),
    # leak-free (frozen text + train-only warm set). --cold-synth-knn 0 => exact
    # no-op; with no --cold-item-frac no item is cold => inert even if knn>0.
    ap.add_argument("--cold-synth-knn", type=int, default=0,
                     help="NOVEL cold-start (PROPOSAL 2026-06-23-1): K frozen-text "
                          "neighbors (WARM items only) whose LEARNED ID embeddings are "
                          "softmax-averaged to synthesize each COLD item's ID vector. "
                          "0 => OFF (exact no-op). Requires --cold-item-frac>0.")
    ap.add_argument("--cold-synth-temp", type=float, default=0.07,
                     help="Softmax temperature over text-cosine for the cold-synth "
                          "neighbor weights (lower => sharper, more top-1-like).")
    ap.add_argument("--cold-synth-norm", action="store_true",
                     help="NOVEL cold-start (PROPOSAL 2026-06-23-3): restore the "
                          "averaging-contracted magnitude of the kNN-imputed cold ID "
                          "row to the local weighted-mean neighbor norm (direction "
                          "preserved). Parameter-free, cold-only. OFF => bit-identical "
                          "to cold-synth. Requires --cold-synth-knn>0 + --cold-item-frac>0.")
    ap.add_argument("--cold-id-drop", action="store_true",
                     help="NOVEL cold-start (PROPOSAL 2026-07-02-1): for TRUE-COLD "
                          "items (item_users==0) zero the untrained noise ID row so "
                          "the trained additive frozen-text path carries them (the "
                          "DROP alternative to cold-synth's IMPUTE). Parameter-free, "
                          "cold-only. OFF => bit-identical to the text-stack baseline. "
                          "Requires --cold-item-frac>0; use with --cold-synth-knn 0.")
    ap.add_argument("--zfusion-eval", action="store_true",
                     help="COMPARATOR (protocol-matched LC2C/z-fusion cold-start bar, "
                          "the sole ADMISSIBLE incumbent-class test under our exact "
                          "sequential LLOO full-catalog cold split): eval-time z-score "
                          "LATE FUSION of the warm-trained model score with a mean-text "
                          "content-profile cosine score (each z-normalized across the "
                          "candidate axis, then summed). Standard hybrid CF+content "
                          "re-ranker; scores cold items the ID model floors via their "
                          "frozen text. TRAIN-FREE fusion, applied at eval only. OFF => "
                          "bit-identical to the base run. Report cold+warm straight.")
    ap.add_argument("--zfusion-weight", type=float, default=0.5,
                     help="Content share w in [0,1] for the tuned z-fusion merge "
                          "2*((1-w)*z(model)+w*z(content)). Default 0.5 == the prior "
                          "un-tuned 1:1 sum (bit-identical). Used by --zfusion-eval "
                          "and as the per-point weight in --zfusion-sweep.")
    ap.add_argument("--zfusion-sweep", type=str, default="",
                     help="ANALYST missing-ablation #2: comma-separated content "
                          "weights (e.g. '0.0,0.25,0.5,0.75,1.0'). After training, "
                          "re-evaluate the FINAL model at each weight (eval-only, no "
                          "retrain) and record the cold/warm/overall frontier under "
                          "the JSON key 'zfusion_sweep' — tests whether ANY fusion "
                          "weight ranks cold@10 while preserving warm CF. Empty=off.")
    ap.add_argument("--credibility-route", action="store_true",
                     help="NOVEL cold-start (PROPOSAL 2026-07-03-1): score-level, "
                          "dual-space, scale-EQUATED, count-ROUTED merge — the "
                          "constructive test of the sbert-only(cold-win)/CF(warm-win) "
                          "double-dissociation. Per query, build TWO catalog score "
                          "vectors from the SAME hidden: s_full (CF space = "
                          "item_emb+sbert_proj+TAPE, the eval scorer) and s_txt (the "
                          "homogeneous frozen-text space = sbert_proj(sbert_table), the "
                          "--sbert-only scorer). Z-standardize BOTH over the candidate "
                          "axis (psychometric test-equating), then per-candidate "
                          "actuarial-credibility route (Bühlmann): Z_j=n_j/(n_j+k) from "
                          "TRAIN-only item_freq; merged = Z_j*z_full + (1-Z_j)*z_txt. "
                          "n_j=0 (true-cold) => Z=0 => pure equated-text ranking; large "
                          "n_j => Z->1 => CF space. NON-learnable. EVAL-ONLY (train "
                          "untouched). OFF => scores bit-identical; ON with no "
                          "--cold-item-frac => all warm (Z~1) => merge~=z_full. LEAK-FREE "
                          "(train-only n_j; z over candidates; down-weights ID for "
                          "LOW-count items => opposite of popularity inflation).")
    ap.add_argument("--cred-k", type=float, default=2.0,
                     help="Bühlmann credibility constant k in Z_j=n_j/(n_j+k) for "
                          "--credibility-route (k=EPV/VHM). Non-learnable; swept "
                          "{0.5,1,2,5} at eval for free. Default 2.0.")
    ap.add_argument("--cred-rank-fusion", action="store_true",
                     help="SUPERVISOR cycle-20 GRANTED probe (rank-level calibration): "
                          "replace the --credibility-route SCORE-level z-equate merge with "
                          "a SCALE-FREE credibility-weighted RECIPROCAL-RANK fusion. Each "
                          "head (CF final, homogeneous-text s_txt) is converted to a "
                          "per-candidate reciprocal rank 1/(c+rank) (rank 0=best), then "
                          "routed by Bühlmann Z_j: final=Z_j*rr_full+(1-Z_j)*rr_txt. "
                          "Targets the ANALYST FINDING-3 top-rank calibration failure "
                          "(cold hit@100=225 >> @10=5 under z-equate). Only active with "
                          "--credibility-route. OFF => z-equate path bit-identical. "
                          "Eval-only; no gradient; leak-free (same train-only Z_j).")
    ap.add_argument("--rrf-c", type=float, default=60.0,
                     help="Reciprocal-rank-fusion damping constant c in 1/(c+rank) for "
                          "--cred-rank-fusion (standard RRF default 60). Non-learnable.")
    ap.add_argument("--cred-route-train", action="store_true",
                     help="NOVEL cold-start (PROPOSAL 2026-07-03-1, TRAIN-CONSISTENT "
                          "variant): route the TRAINING loss by the same Bühlmann "
                          "credibility Z_j=n_j/(n_j+k) so sbert_proj gets gradient to "
                          "SCORE STANDALONE for low-count targets while item_emb trains "
                          "for high-count targets. Per valid target y: L = Z_y*CE(s_full,y) "
                          "+ (1-Z_y)*CE(s_txt,y), where s_full is the CF-space score and "
                          "s_txt the homogeneous frozen-text score (sbert_proj(sbert_table)). "
                          "Cold (n_y=0 => Z=0) supervises the text space alone; warm (Z->1) "
                          "the CF space. This is the ANALYST Finding-2 fix (in the additive "
                          "stack sbert_proj is only a small residual, so eval-time text may "
                          "not stand alone). Parameter-free (Z=n/(n+k), non-learnable — "
                          "cannot be voted off like conn-gate alpha->0/X1 c->0/Y1 T->0). "
                          "OFF => training loss bit-identical. LEAK-FREE (train-only n_j; "
                          "frozen text). Pair with --credibility-route to also merge at eval.")
    ap.add_argument("--dual-head-decorr", type=float, default=0.0,
                     help="NOVEL cold-start (PROPOSAL 2026-07-03-2): Hui-Walter "
                          "conditional-independence / error-DECORRELATION penalty on the "
                          "two --cred-route-train heads. Adds lambda*corr(ce_full,ce_txt)^2 "
                          "(Pearson) or lambda*HSIC(ce_full,ce_txt) to the loss, driving the "
                          "two heads' per-example errors (each conditioned on the realized "
                          "target => a conditional-independence proxy) toward independence so "
                          "the frozen-text head becomes a STANDALONE-calibrated cold scorer "
                          "(the missing term that floored --cred-route-train at cold hits@10=3). "
                          "Only active with --cred-route-train. Default 0.0 => term absent => "
                          "loss bit-identical to plain --cred-route-train. LEAK-FREE (consults "
                          "only model-score CEs at the realized target; no val/test label). "
                          "Refs: Hui-Walter 1980; Blum-Mitchell 1998; Gretton 2005 (HSIC).")
    ap.add_argument("--decorr-mode", choices=("pearson", "hsic"), default="pearson",
                     help="Dependence measure for --dual-head-decorr. 'pearson' kills LINEAR "
                          "error-correlation (ship rung); 'hsic' kills NONLINEAR conditional "
                          "dependence a residual head can hide behind (sanctioned in-family "
                          "upgrade). Default pearson.")
    ap.add_argument("--krige-cold", action="store_true",
                     help="NOVEL cold-start (PROPOSAL 2026-06-23-2): replace the flat "
                          "softmax-kNN cold-synth weights with the BLUP/kriging weights "
                          "w=(K_ww+lam*I)^-1 k_iw (K_ww=warm-neighbor cosine Gram, "
                          "k_iw=cold-neighbor cosines), declustering redundant neighbors. "
                          "Parameter-free. OFF => bit-identical to cold-synth. Requires "
                          "--cold-synth-knn>0 + --cold-item-frac>0.")
    ap.add_argument("--krige-nugget", type=float, default=0.01,
                     help="Ridge nugget (proportional to mean Gram diagonal) added to "
                          "K_ww for invertibility in --krige-cold. Fixed numerical "
                          "regularizer, not learned.")
    args = ap.parse_args()

    # Set random seeds for reproducibility (per-seed runs for multi-seed CI).
    import random
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
    print(f"  random seed set to {args.seed}")

    out_path = Path(args.out) if args.out else (Path(__file__).parent /
                                                  f"results_sasrec_sbert_{args.category}.json")

    train_csv = SPLIT_DIR / f"{args.category}.train.csv"
    valid_csv = SPLIT_DIR / f"{args.category}.valid.csv"
    test_csv = SPLIT_DIR / f"{args.category}.test.csv"
    sbert_npy = (Path(args.encoder_cache) if args.encoder_cache
                  else EMB_CACHE_DIR / f"sbert_titles_{args.category}.npy")
    for p in (train_csv, valid_csv, test_csv):
        if not p.exists():
            print(f"ERROR: {p} missing")
            return 2
    if not args.no_sbert and not sbert_npy.exists():
        print(f"ERROR: SBERT cache {sbert_npy} missing. Run run_5core_benchmark.py --encode-titles first.")
        return 2

    print(f"=== {args.category}: load splits ===")
    train_rows = load_split_csv(train_csv)
    valid_rows = load_split_csv(valid_csv)
    test_rows = load_split_csv(test_csv)
    train_inters, valid_inters, test_inters, user_list, item_list = reindex(
        train_rows, valid_rows, test_rows)
    n_users, n_items = len(user_list), len(item_list)
    pad_id = n_items
    print(f"  n_users={n_users:,}  n_items={n_items:,}  pad_id={pad_id}")

    # NOVEL (PROPOSAL 2026-06-22-1): item cold-start leave-items-out split.
    # Sample frac*n_items item IDs deterministically (RandomState(cold_item_seed))
    # and REMOVE every cold item from train_inters at the source — so every
    # downstream training structure (user_seqs, train_user_seqs, item_users for
    # conn-gate, item_freq, niche_pop, tercile freq) sees ZERO cold interactions
    # and the cold items' item_emb never receives a gradient (untrained). The
    # frozen sbert_table keeps a row for every item (content retained). valid/
    # test_inters are UNTOUCHED => cold items remain ranking TARGETS. Leak-free:
    # the cold set is drawn from item IDs only; for conn-gate, cold items get
    # item_users=0 (its designed extreme: w_tx up, w_id down). frac=0 => no-op.
    cold_items = None
    if args.cold_item_frac > 0.0:
        n_cold = int(round(args.cold_item_frac * n_items))
        _crng = np.random.RandomState(args.cold_item_seed)
        cold_ids = _crng.choice(n_items, size=n_cold, replace=False)
        cold_items = set(int(x) for x in cold_ids.tolist())
        _n_train_before = len(train_inters)
        train_inters = [r for r in train_inters if r[1] not in cold_items]
        _test_cold = sum(1 for (_, i, _, _) in test_inters if i in cold_items)
        _valid_cold = sum(1 for (_, i, _, _) in valid_inters if i in cold_items)
        print(f"  COLD-START: held out {n_cold:,}/{n_items:,} items "
              f"(frac={args.cold_item_frac}, seed={args.cold_item_seed}); "
              f"train interactions {len(train_inters):,}/{_n_train_before:,} kept "
              f"({_n_train_before - len(train_inters):,} cold removed); "
              f"cold items as TARGETS: test={_test_cold:,}, valid={_valid_cold:,} "
              f"(item_emb for cold items never trains; frozen text retained)")

    # Build user training sequences. user_seqs / user_times are the FULL-density
    # set: they are used for EVAL conditioning histories AND to freeze the
    # tail/mid/head terciles (evaluate() computes the bucket from the passed
    # full user_seqs and caches it), so the only variable a density titration
    # manipulates is the TRAINING density.
    user_seqs = build_user_sequences(train_inters)
    print(f"  built sequences for {len(user_seqs):,} users")
    user_times = (build_user_time_sequences(train_inters)
                  if (args.time_bias or args.time_decay_kernel) else None)
    if args.time_bias:
        print(f"  built timestamp sequences ({N_TIME_BUCKETS} time buckets)")

    # DATA-ABLATION (PROPOSAL 2026-06-18-1): thin ONLY the training interactions
    # for the density-titration. Eval keeps the FULL user_seqs/user_times above.
    # frac >= 1.0 => train set is identical to full => bit-identical no-op.
    train_user_seqs, train_user_times = user_seqs, user_times
    if args.subsample_train_frac < 1.0:
        _rng = np.random.RandomState(args.subsample_seed)
        if args.subsample_mode == "user":
            keep_u = {u for u in {uu for (uu, _, _, _) in train_inters}
                      if _rng.random() < args.subsample_train_frac}
            train_inters_sub = [r for r in train_inters if r[0] in keep_u]
        else:  # interaction
            _mask = _rng.random(len(train_inters)) < args.subsample_train_frac
            train_inters_sub = [r for r, k in zip(train_inters, _mask) if k]
        train_user_seqs = build_user_sequences(train_inters_sub)
        train_user_times = (build_user_time_sequences(train_inters_sub)
                            if (args.time_bias or args.time_decay_kernel) else None)
        print(f"  TITRATION: subsample-train-frac={args.subsample_train_frac} "
              f"mode={args.subsample_mode} seed={args.subsample_seed} -> "
              f"{len(train_inters_sub):,}/{len(train_inters):,} train interactions kept; "
              f"train interactions/item = {len(train_inters_sub)/max(n_items,1):.3f} "
              f"(full = {len(train_inters)/max(n_items,1):.3f}); eval histories + terciles FROZEN at full density")

    # Load SBERT embeddings (aligned with item_list order from reindex())
    sbert_emb = None
    if not args.no_sbert:
        print(f"  loading SBERT embeddings from {sbert_npy}...")
        sbert_emb = np.load(sbert_npy).astype(np.float32)
        if sbert_emb.shape[0] != n_items:
            print(f"  WARN: SBERT cache has {sbert_emb.shape[0]} items but split has {n_items}; aligning by index")
            sbert_emb = sbert_emb[:n_items]

    # TAPE: Text-Anchored Prototype assignments (frozen) from k-means over the
    # frozen text embeddings. proto_emb itself is learnable and zero-init.
    proto_assign = None
    proto_ks = [int(k) for k in str(args.text_prototypes).split(",") if int(k) > 0]
    if proto_ks:
        if sbert_emb is None:
            print("ERROR: --text-prototypes requires text embeddings (omit --no-sbert)")
            return 2
        x = torch.from_numpy(sbert_emb).to(DEVICE)
        x = torch.nn.functional.normalize(x, dim=1)
        proto_assign = []
        for K in proto_ks:
            print(f"  TAPE: k-means {n_items:,} text embeddings into K={K} prototypes (tau={args.proto_tau})...")
            C = torch_kmeans(x, K, iters=25, seed=args.seed)
            A = torch.softmax((x @ C.T) / args.proto_tau, dim=1)  # (n_items, K)
            A_pad = torch.zeros((n_items + 1, K), dtype=torch.float32, device=DEVICE)
            A_pad[:n_items] = A
            proto_assign.append(A_pad)
            eff = float((A.max(dim=1).values).mean())
            print(f"  TAPE: K={K} mean max-assignment weight = {eff:.3f} (1.0 = hard clustering)")

    # NOVEL niche-share (W1): train-only item popularity vector for the
    # fitness-sharing crowding penalty. Built from TRAIN interactions ONLY
    # (train_inters; valid_inters/test_inters are never consulted) => leak-free.
    niche_pop = None
    if args.niche_share_beta != 0.0:
        item_ids = torch.tensor([i for (_, i, _, _) in train_inters], dtype=torch.long)
        niche_pop = torch.bincount(item_ids, minlength=n_items + 1).float()
        print(f"  niche-share: built TRAIN-only popularity (sum={int(niche_pop.sum())}, "
              f"max={int(niche_pop.max())}); beta is a zero-init learnable scalar")

    # NOVEL X1 (js-shrink): per-item TRAIN-only interaction count for the
    # frequency-adaptive James–Stein shrinkage. Same leak-free construction as
    # niche-share (train_inters only; valid/test never consulted).
    item_freq = None
    if args.js_shrink:
        ifreq_ids = torch.tensor([i for (_, i, _, _) in train_inters], dtype=torch.long)
        item_freq = torch.bincount(ifreq_ids, minlength=n_items + 1).float()
        nz = item_freq[item_freq > 0]
        print(f"  js-shrink: built TRAIN-only item_freq (min={int(nz.min())}, "
              f"median={int(nz.median())}, max={int(item_freq.max())}); "
              f"shrink_c zero-init at -8.0 -> lambda~0 -> no-op at start")

    # NOVEL cold-start (PROPOSAL 2026-07-03-1, TRAIN-CONSISTENT variant): build the
    # TRAIN-only item_freq that keys the Bühlmann credibility route Z_j=n_j/(n_j+k)
    # in the loss. Cold items are already removed from train_inters (--cold-item-frac
    # hold-out above) => their n_j=0 => Z_j=0 => the loss supervises them purely in
    # the text space. Leak-free (train_inters only; valid/test never consulted).
    if item_freq is None and args.cred_route_train:
        ifreq_ids = torch.tensor([i for (_, i, _, _) in train_inters], dtype=torch.long)
        item_freq = torch.bincount(ifreq_ids, minlength=n_items + 1).float()
        nz = item_freq[item_freq > 0]
        print(f"  cred-route-train: built TRAIN-only item_freq (min={int(nz.min())}, "
              f"median={int(nz.median())}, max={int(item_freq.max())}); "
              f"Z_j=n_j/(n_j+{args.cred_k}); cold n_j=0 => Z=0 => pure text supervision")

    # NOVEL Z1 (fitness-gate): TRAIN-only item_freq + tail/mid tercile boundary
    # tau (leak-free, same construction as js-shrink + the eval bucketer). The
    # gate is NON-LEARNABLE; tau is the catalog's empirical tail boundary.
    fg_tau = 0.0
    if args.fitness_gate:
        if item_freq is None:
            ifreq_ids = torch.tensor([i for (_, i, _, _) in train_inters], dtype=torch.long)
            item_freq = torch.bincount(ifreq_ids, minlength=n_items + 1).float()
        # tail/mid tercile boundary: rank the n_items real items by train freq,
        # take the freq at rank ceil(n_items/3) (rarest third = tail).
        real_freq = item_freq[:n_items]
        sorted_freq, _ = torch.sort(real_freq)                 # ascending (rarest first)
        boundary_rank = (n_items + 2) // 3                     # ceil(n_items/3)
        boundary_rank = min(max(boundary_rank, 0), n_items - 1)
        fg_tau = float(torch.log1p(sorted_freq[boundary_rank]).item())
        nzf = real_freq[real_freq > 0]
        print(f"  fitness-gate: TRAIN-only freq (min={int(nzf.min())}, median={int(nzf.median())}, "
              f"max={int(real_freq.max())}); tail/mid tercile boundary tau=log1p(freq)={fg_tau:.3f} "
              f"(rank {boundary_rank}/{n_items}); alpha={args.fitness_gate_alpha}, slope={args.fitness_gate_slope}, "
              f"NON-learnable (cannot be voted off); alpha=0 => no-op")

    # NOVEL (cold-start application): TRAIN-only DISTINCT users per item — the
    # causal connectivity axis the user-mode titration identified (NOT freq).
    # Leak-free: train_inters only; valid/test never consulted.
    item_users = None
    if args.conn_gate:
        _u = defaultdict(set)
        for (u, i, _, _) in train_inters:
            _u[i].add(u)
        item_users = torch.zeros(n_items + 1)
        for i, s in _u.items():
            item_users[i] = len(s)
        nzu = item_users[item_users > 0]
        print(f"  conn-gate: TRAIN-only distinct users/item (min={int(nzu.min())}, "
              f"median={int(nzu.median())}, max={int(item_users.max())}); cg_alpha=-6 "
              f"=> alpha~0 => additive no-op at start; gates on users/item, NOT freq")

    # NOVEL (PROPOSAL 2026-06-23-1): synthetic-connectivity precompute. For each
    # COLD item (held out of all training by --cold-item-frac => item_emb row
    # untrained), find its top-K frozen-text cosine neighbors among the WARM
    # candidate set ONLY, with softmax(cos/temp) weights. At forward time the
    # cold item's ID channel becomes Sum_k w_ik * item_emb[n_ik] (learned warm
    # rows). Parameter-free + leak-free (frozen text + train-only warm set).
    # Inert unless BOTH --cold-synth-knn>0 AND a cold split exists.
    cold_synth_nbr = cold_synth_wgt = cold_synth_is_cold = None
    if args.cold_synth_knn > 0 and cold_items is not None:
        if sbert_emb is None:
            print("ERROR: --cold-synth-knn requires text embeddings (omit --no-sbert)")
            return 2
        K = int(args.cold_synth_knn)
        temp = float(args.cold_synth_temp)
        xs = torch.nn.functional.normalize(
            torch.from_numpy(sbert_emb).to(DEVICE), dim=1)            # (n_items, d)
        cold_idx_t = torch.tensor(sorted(cold_items), dtype=torch.long, device=DEVICE)
        warm_mask = torch.ones(n_items, dtype=torch.bool, device=DEVICE)
        warm_mask[cold_idx_t] = False                                 # cold (incl self) excluded
        n_warm = int(warm_mask.sum().item())
        if n_warm < K:
            print(f"ERROR: --cold-synth-knn={K} but only {n_warm} warm items")
            return 2
        cold_synth_nbr = torch.zeros((n_items + 1, K), dtype=torch.long, device=DEVICE)
        cold_synth_wgt = torch.zeros((n_items + 1, K), dtype=torch.float32, device=DEVICE)
        cold_synth_is_cold = torch.zeros(n_items + 1, dtype=torch.bool, device=DEVICE)
        cold_synth_is_cold[cold_idx_t] = True
        CH = 1024
        _top1 = []
        _krige_cond = []                                              # cond numbers (kriging readout)
        _krige_negmass = []                                          # mean negative-weight mass
        for s0 in range(0, cold_idx_t.numel(), CH):
            block = cold_idx_t[s0:s0 + CH]
            sims = xs[block] @ xs.T                                   # (b, n_items)
            sims[:, ~warm_mask] = float("-inf")                       # WARM neighbors only
            tv, ti = sims.topk(K, dim=1)
            if getattr(args, "krige_cold", False):
                # NOVEL kriging/BLUP (PROPOSAL 2026-06-23-2): w=(K_ww+lam*I)^-1 k_iw
                # K_ww = warm-neighbor<->warm-neighbor cosine Gram (linear text kernel);
                # k_iw = cold<->neighbor cosines (== tv). Declusters redundant neighbors.
                Tn = xs[ti]                                          # (b, K, d) L2-normed warm text vecs
                Kww = torch.bmm(Tn, Tn.transpose(1, 2))              # (b, K, K) cosine Gram
                lam = float(args.krige_nugget) * Kww.diagonal(dim1=1, dim2=2).mean(dim=1)  # (b,)
                eyeK = torch.eye(K, device=DEVICE)
                Kww = Kww + lam.view(-1, 1, 1) * eyeK                # ridge nugget
                w = torch.linalg.solve(Kww, tv.unsqueeze(-1)).squeeze(-1)   # (b, K) BLUP weights
                w = w / w.sum(dim=1, keepdim=True).clamp_min(1e-8)   # renorm (signed) avg
                # readouts
                _krige_cond.append(torch.linalg.cond(Kww))
                _krige_negmass.append(w.clamp_max(0.0).abs().sum(dim=1))
            else:
                w = torch.softmax(tv / temp, dim=1)
            cold_synth_nbr[block] = ti
            cold_synth_wgt[block] = w
            _top1.append(tv[:, 0])
        mt1 = float(torch.cat(_top1).mean().item())
        print(f"  cold-synth: synthesized {cold_idx_t.numel():,} COLD ID vectors from "
              f"top-{K} frozen-text neighbors among {n_warm:,} WARM items "
              f"(temp={temp}, mean top-1 cosine={mt1:.3f}); parameter-free, leak-free; "
              f"warm items untouched")
        if getattr(args, "krige_cold", False) and _krige_cond:
            med_cond = float(torch.cat(_krige_cond).median().item())
            mean_neg = float(torch.cat(_krige_negmass).mean().item())
            print(f"  KRIGE-COLD (PROPOSAL 2026-06-23-2): BLUP weights via "
                  f"(K_ww+{args.krige_nugget}*diag)^-1 k_iw; median cond(K_ww+lam*I)="
                  f"{med_cond:.2f}, mean negative-weight mass={mean_neg:.4f} "
                  f"(0 => collapses to cold-synth; >0 => declustering fired)")

    # NOVEL cold-id-drop (PROPOSAL 2026-07-02-1): needs the is_cold mask even when
    # cold-synth is OFF (--cold-synth-knn 0). Build the same leak-free TRUE-COLD
    # (item_users==0, --cold-item-frac hold-out) boolean here if not already built.
    if getattr(args, "cold_id_drop", False) and cold_synth_is_cold is None and cold_items is not None:
        cold_idx_t = torch.tensor(sorted(cold_items), dtype=torch.long, device=DEVICE)
        cold_synth_is_cold = torch.zeros(n_items + 1, dtype=torch.bool, device=DEVICE)
        cold_synth_is_cold[cold_idx_t] = True
        print(f"  cold-id-drop (PROPOSAL 2026-07-02-1): will ZERO the untrained ID row "
              f"for {cold_idx_t.numel():,} TRUE-COLD items => carried by additive text (+TAPE); "
              f"warm items untouched; parameter-free, leak-free")

    # NOVEL Y1 (heat-target): precompute frozen top-m text-cosine neighbors ONCE
    # (chunked matmul to avoid the n_items^2 all-pairs tensor). LEAK-FREE: frozen
    # text only — no interactions, no val/test rows. Indexed by item id in the loss.
    heat_nbr_idx = heat_nbr_sim = None
    if args.heat_target:
        if sbert_emb is None:
            print("ERROR: --heat-target requires text embeddings (omit --no-sbert)")
            return 2
        m = int(args.heat_neighbors)
        xh = torch.nn.functional.normalize(torch.from_numpy(sbert_emb).to(DEVICE), dim=1)
        idx_rows, sim_rows = [], []
        CH = 2048
        for s0 in range(0, n_items, CH):
            e0 = min(s0 + CH, n_items)
            sims = xh[s0:e0] @ xh.T                                   # (chunk, n_items)
            sims[torch.arange(e0 - s0, device=DEVICE),
                 torch.arange(s0, e0, device=DEVICE)] = -float("inf")  # exclude self
            tv, ti = sims.topk(m, dim=1)
            idx_rows.append(ti); sim_rows.append(tv)
        nbr_idx = torch.cat(idx_rows, dim=0)                          # (n_items, m)
        nbr_sim = torch.cat(sim_rows, dim=0)                          # (n_items, m)
        heat_nbr_idx = torch.zeros((n_items + 1, m), dtype=torch.long, device=DEVICE)
        heat_nbr_idx[:n_items] = nbr_idx
        heat_nbr_sim = torch.zeros((n_items + 1, m), dtype=torch.float32, device=DEVICE)
        heat_nbr_sim[:n_items] = nbr_sim
        print(f"  heat-target: precomputed top-{m} frozen text neighbors for {n_items:,} items "
              f"(mean top-1 cosine={float(nbr_sim[:, 0].mean()):.3f}); "
              f"heat_temp init -6 -> T~0.0025 -> delta target -> no-op at start")

    # NOVEL CF1 (cue-fusion): frozen per-item precisions. ID precision = train-only
    # freq (Fisher info ∝ sample size). TEXT precision = text-manifold
    # distinctiveness d_i = 1 - mean(top-K cosine to K nearest frozen-text
    # neighbors) (generic title in a crowded region -> low precision), median-
    # matched to the ID-precision median so the channel crossover sits at the
    # median-frequency (mid-band) item. Both NON-learnable. LEAK-FREE (train freq
    # + frozen text only). Reuses the chunked top-K machinery (no n^2 tensor).
    cue_pi_id = cue_pi_text = None
    if args.cue_fusion:
        if sbert_emb is None:
            print("ERROR: --cue-fusion requires text embeddings (omit --no-sbert)")
            return 2
        if item_freq is None:
            ifreq_ids = torch.tensor([i for (_, i, _, _) in train_inters], dtype=torch.long)
            item_freq = torch.bincount(ifreq_ids, minlength=n_items + 1).float()
        K = int(args.cue_fusion_nbr)
        xc = torch.nn.functional.normalize(torch.from_numpy(sbert_emb).to(DEVICE), dim=1)
        d_rows = []
        CH = 2048
        for s0 in range(0, n_items, CH):
            e0 = min(s0 + CH, n_items)
            sims = xc[s0:e0] @ xc.T
            sims[torch.arange(e0 - s0, device=DEVICE),
                 torch.arange(s0, e0, device=DEVICE)] = -float("inf")
            tv, _ = sims.topk(K, dim=1)
            d_rows.append(1.0 - tv.mean(dim=1))                  # distinctiveness
        d = torch.cat(d_rows, dim=0)                             # (n_items,)
        d = torch.clamp(d, min=0.0)
        freq_real = item_freq[:n_items].to(DEVICE)
        med_id = float(freq_real[freq_real > 0].median())
        med_d = float(d[d > 0].median()) if (d > 0).any() else 1.0
        pi_text_real = d * (med_id / (med_d + 1e-8))            # median-matched
        cue_pi_id = torch.zeros(n_items + 1, device=DEVICE)
        cue_pi_id[:n_items] = freq_real
        cue_pi_text = torch.zeros(n_items + 1, device=DEVICE)
        cue_pi_text[:n_items] = pi_text_real
        print(f"  cue-fusion: ID precision (train freq) median={med_id:.1f}; "
              f"TEXT precision (distinctiveness, top-{K}) median={med_d:.4f} "
              f"-> calibrated to median {med_id:.1f}; mode={args.cue_fusion_mode}, "
              f"NON-learnable (cannot be voted off)")

    # Build SASRec model
    print(f"\n=== Build SASRec-SBERT (d={args.d_model}, layers={args.n_layers}, heads={args.n_heads}) ===")
    model = SASRecSBERT(n_items=n_items, pad_id=pad_id,
                         max_seq_len=args.max_seq_len,
                         d_model=args.d_model, n_layers=args.n_layers,
                         n_heads=args.n_heads, dropout=args.dropout,
                         sbert_emb=sbert_emb, sbert_only=args.sbert_only,
                         mlp_adaptor=args.mlp_adaptor,
                         mlp_hidden=args.mlp_hidden,
                         mlp_dropout=args.mlp_dropout,
                         time_bias=args.time_bias,
                         text_sim_bias=args.text_sim_bias,
                         proto_assign=proto_assign,
                         encoder=args.encoder,
                         pos_rab=args.pos_rab,
                         time_decay_kernel=args.time_decay_kernel,
                         time_decay_bases=args.time_decay_bases,
                         n_experts=args.expert_heads,
                         text_init_emb=args.text_init_emb,
                         cl_aux=(args.cl_weight > 0.0),
                         causal_filter=args.causal_filter,
                         filter_kernel=args.filter_kernel,
                         niche_share=(args.niche_share_beta != 0.0),
                         niche_pop=niche_pop,
                         js_shrink=args.js_shrink,
                         item_freq=item_freq,
                         heat_target=args.heat_target,
                         heat_nbr_idx=heat_nbr_idx,
                         heat_nbr_sim=heat_nbr_sim,
                         cue_fusion=args.cue_fusion,
                         cue_mode=args.cue_fusion_mode,
                         cue_pi_id=cue_pi_id,
                         cue_pi_text=cue_pi_text,
                         fitness_gate=args.fitness_gate,
                         fg_alpha=args.fitness_gate_alpha,
                         fg_slope=args.fitness_gate_slope,
                         fg_tau=fg_tau,
                         conn_gate=args.conn_gate,
                         item_users=item_users,
                         cold_synth_knn=args.cold_synth_knn,
                         cold_synth_nbr=cold_synth_nbr,
                         cold_synth_wgt=cold_synth_wgt,
                         cold_synth_is_cold=cold_synth_is_cold,
                         cold_synth_norm=args.cold_synth_norm,
                         cold_id_drop=args.cold_id_drop,
                         cred_route_train=args.cred_route_train,
                         cred_k=args.cred_k).to(DEVICE)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"  total params: {n_params:,}  device={DEVICE}")

    # Weight-space EMA (SWA-style) shadow for eval only. Passive: never feeds
    # back into training, so the optimization trajectory is bit-identical to the
    # no-EMA baseline. Captures full state_dict (params + buffers); only
    # floating-point tensors are averaged, others are copied verbatim.
    ema = None
    if args.ema_decay > 0.0:
        ema = {k: v.detach().clone() for k, v in model.state_dict().items()}
        print(f"  EMA weight averaging enabled for eval (decay={args.ema_decay}, per-epoch)")

    # DataLoader
    dataset = SASRecDataset(train_user_seqs, args.max_seq_len, n_items, pad_id,
                              augment_factor=args.augment_factor,
                              user_times=train_user_times)
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True,
                          num_workers=0, collate_fn=collate_batch, drop_last=False)
    print(f"  {len(dataset):,} training examples / {len(loader):,} batches per epoch")

    opt = torch.optim.Adam(model.parameters(), lr=args.lr, weight_decay=1e-5)

    # Optional LR schedule (warmup + cosine decay)
    scheduler = None
    if args.lr_schedule == "warmup_cosine":
        total_steps = args.epochs * len(loader)
        warmup_steps = max(1, int(0.05 * total_steps))
        cosine_steps = max(1, total_steps - warmup_steps)
        warmup = torch.optim.lr_scheduler.LinearLR(
            opt, start_factor=1e-3, end_factor=1.0, total_iters=warmup_steps)
        cosine = torch.optim.lr_scheduler.CosineAnnealingLR(
            opt, T_max=cosine_steps, eta_min=0)
        scheduler = torch.optim.lr_scheduler.SequentialLR(
            opt, schedulers=[warmup, cosine], milestones=[warmup_steps])
        print(f"  LR schedule: warmup_cosine ({warmup_steps} warmup + {cosine_steps} cosine steps)")

    # Train
    print(f"\n=== Train for {args.epochs} epochs ===")
    best_val_ndcg = 0.0
    best_test_metrics = None
    best_test_user_records = None
    best_test_epoch = None
    history = []
    # NOVEL GD1 (spectral-shrink) diagnostics (directive-(c) irreducibility figure).
    spectral_eff_rank = None
    spectral_bbp_rho = None
    if args.spectral_shrink:
        import numpy as _np
        _freq = _np.bincount([i for (_, i, _, _) in train_inters],
                              minlength=n_items + 1).astype(_np.float64)
        # per-popularity tercile boundaries by train frequency (rarest third = tail)
        _nz = _freq[:n_items]
        _order = _np.argsort(_nz)
        _t1, _t2 = n_items // 3, 2 * n_items // 3
        _terc = _np.empty(n_items, dtype=int)
        _terc[_order[:_t1]] = 0; _terc[_order[_t1:_t2]] = 1; _terc[_order[_t2:]] = 2
        # mean BBP reliability rho_i per tercile for fixed signal strengths ell
        spectral_bbp_rho = {}
        for _ell in (2, 4, 8):
            _gamma = float(args.d_model) / _np.maximum(_nz, 1.0)
            _num = 1.0 - _gamma / (_ell - 1) ** 2
            _den = 1.0 + _gamma / (_ell - 1)
            _rho = _np.clip(_num / _den, 0.0, 1.0)
            spectral_bbp_rho[f"ell{_ell}"] = {
                "tail": float(_rho[_terc == 0].mean()),
                "mid": float(_rho[_terc == 1].mean()),
                "head": float(_rho[_terc == 2].mean())}
        print(f"  spectral-shrink BBP detectability (mean rho per tercile): {spectral_bbp_rho}")
    for epoch in range(1, args.epochs + 1):
        t0 = time.time()
        train_loss, n_pos = train_one_epoch(model, loader, opt, pad_id, DEVICE,
                                              sampled_negs=args.sampled_negs,
                                              in_batch_negs=args.in_batch_negs,
                                              chunked_full_softmax=args.chunked_full_softmax,
                                              item_chunk=args.item_chunk,
                                              scheduler=scheduler,
                                              cosine=args.cosine_scoring,
                                              temp=args.score_temp,
                                              text_distill_weight=args.text_distill_weight,
                                              cl_weight=args.cl_weight,
                                              cl_mask_prob=args.cl_mask_prob,
                                              cl_tau=args.cl_tau,
                                              label_smoothing=args.label_smoothing,
                                              niche_share_beta=args.niche_share_beta,
                                              heat_target=args.heat_target,
                                              cred_route_train=args.cred_route_train,
                                              cred_k=args.cred_k,
                                              dual_head_decorr=args.dual_head_decorr,
                                              decorr_mode=args.decorr_mode)
        ep_time = time.time() - t0
        # NOVEL GD1 (spectral-shrink): per-epoch parameter-free Gavish-Donoho /
        # Marchenko-Pastur singular-value shrinkage of the item-embedding matrix
        # (item-axis-spectrum dual of the causal temporal filter). NON-learnable
        # (threshold derived from the SVD spectrum + aspect ratio), training-only,
        # representation-side. OFF => block skipped => weights bit-identical.
        if args.spectral_shrink and (epoch % args.spectral_shrink_every == 0):
            with torch.no_grad():
                W = model.item_emb.weight.data[:n_items].float()      # (n_items, d)
                U, S, Vh = torch.linalg.svd(W, full_matrices=False)
                n_, d_ = W.shape
                beta = float(min(n_, d_)) / float(max(n_, d_))
                omega = 0.56*beta**3 - 0.95*beta**2 + 1.82*beta + 1.43
                tau = omega * torch.median(S)
                if args.spectral_shrink_mode == "hard":
                    S_sh = torch.where(S >= tau, S, torch.zeros_like(S))
                else:
                    mu = math.sqrt(max(n_, d_))
                    sigma = torch.median(S) / (mu * 0.5)
                    yv = S / (sigma * mu)
                    eta = torch.sqrt(torch.clamp((yv**2 - beta - 1)**2 - 4*beta, min=0)) / yv
                    S_sh = torch.where(yv > 1 + math.sqrt(beta),
                                       sigma*mu*eta, torch.zeros_like(S))
                spectral_eff_rank = int((S_sh > 0).sum().item())
                W_dn = (U * S_sh.unsqueeze(0)) @ Vh
                model.item_emb.weight.data[:n_items] = W_dn.to(model.item_emb.weight.dtype)
                model.item_emb.weight.data[pad_id].zero_()
                if epoch % args.eval_every == 0 or epoch == args.epochs:
                    print(f"  spectral-shrink ep{epoch}: effective rank "
                          f"{spectral_eff_rank}/{d_} (tau={float(tau):.4f}, mode={args.spectral_shrink_mode})")
        # Update the EMA shadow once per epoch (after the optimizer steps in
        # train_one_epoch). Float tensors are averaged; ints/bools copied.
        if ema is not None:
            with torch.no_grad():
                for k, v in model.state_dict().items():
                    if ema[k].is_floating_point():
                        ema[k].mul_(args.ema_decay).add_(v.detach(),
                                                          alpha=1.0 - args.ema_decay)
                    else:
                        ema[k].copy_(v.detach())
        log = {"epoch": epoch, "train_loss": train_loss, "epoch_time_s": ep_time}
        if epoch % args.eval_every == 0 or epoch == args.epochs:
            # Periodic eval: subsample to keep wall time tractable.
            # Final eval is always on the full set.
            subs = args.eval_subsample if epoch < args.epochs else 0
            # Swap in the EMA-averaged weights for the eval pass (val + test are
            # selected on the SAME weights -> no leakage), then restore live ones.
            ema_backup = None
            if ema is not None:
                ema_backup = {k: v.detach().clone()
                              for k, v in model.state_dict().items()}
                model.load_state_dict(ema)
            val_metrics = evaluate(model, user_seqs, valid_inters, n_items, pad_id,
                                     args.max_seq_len, DEVICE,
                                     subsample_users=subs,
                                     stratify_head=args.eval_stratify_head,
                                     user_times=user_times,
                                     cosine=args.cosine_scoring,
                                     cold_items=cold_items,
                                     zfusion=args.zfusion_eval,
                                     credibility_route=args.credibility_route,
                                     cred_k=args.cred_k,
                                     zfusion_weight=args.zfusion_weight,
                                     cred_rank_fusion=args.cred_rank_fusion,
                                     rrf_c=args.rrf_c)
            valid_dict = {u: i for u, i, _, _ in valid_inters}
            test_extra = {u: [i] for u, i in valid_dict.items()}
            # BUGFIX (audit F2): the appended val-item timestamp must be supplied
            # to test-eval whenever evaluate() consumes times, i.e. for BOTH
            # --time-bias and --time-decay-kernel. Previously gated on time_bias
            # only, so --time-decay-kernel runs got timestamp-0 at the query
            # position on TEST (not val) — a fixed protocol asymmetry that
            # manufactured the c3 "val>>test gap". Headline unaffected (kernel off).
            val_time_extra = ({u: [t // 1000] for u, _, _, t in valid_inters}
                              if (args.time_bias or args.time_decay_kernel) else None)
            test_metrics = evaluate(model, user_seqs, test_inters, n_items, pad_id,
                                      args.max_seq_len, DEVICE, extra_history=test_extra,
                                      subsample_users=subs,
                                      stratify_head=args.eval_stratify_head,
                                      user_times=user_times,
                                      extra_times=val_time_extra,
                                      cosine=args.cosine_scoring,
                                      cold_items=cold_items,
                                      zfusion=args.zfusion_eval,
                                      credibility_route=args.credibility_route,
                                      cred_k=args.cred_k,
                                      zfusion_weight=args.zfusion_weight,
                                      cred_rank_fusion=args.cred_rank_fusion,
                                      rrf_c=args.rrf_c)
            # Restore live training weights so the next epoch continues from the
            # real (non-averaged) trajectory.
            if ema_backup is not None:
                model.load_state_dict(ema_backup)
            # Per-user records: keep them OUT of the (per-epoch) history log —
            # stash only the best-by-val epoch's copy for the sidecar artifact.
            val_metrics.pop("_user_records", None)
            _test_urec = test_metrics.pop("_user_records", None)
            log["val"] = val_metrics
            log["test"] = test_metrics
            print(f"  epoch {epoch:>3d}  loss={train_loss:.4f}  val_NDCG={val_metrics['NDCG@10']:.4f}  "
                  f"test_NDCG={test_metrics['NDCG@10']:.4f}  test_HR={test_metrics['HR@10']:.4f}  "
                  f"({ep_time:.1f}s)")
            if val_metrics["NDCG@10"] > best_val_ndcg:
                best_val_ndcg = val_metrics["NDCG@10"]
                best_test_metrics = test_metrics
                best_test_user_records = _test_urec
                best_test_epoch = epoch
        else:
            print(f"  epoch {epoch:>3d}  loss={train_loss:.4f}  ({ep_time:.1f}s)")
        history.append(log)

    print(f"\n=== Best by val NDCG@10 ===")
    print(f"  val_NDCG={best_val_ndcg:.4f}")
    if best_test_metrics:
        print(f"  test: {best_test_metrics}")

    # NOVEL niche-share (W1): report the LEARNED crowding-penalty scalar beta as
    # an interpretable readout (the proposal/supervisor ask for it regardless of
    # the test delta: beta~0 => model voted the penalty off; beta>0 => the stack
    # was over-rewarding crowded popular niches). Captured from the FINAL weights.
    learned_niche_beta = None
    if getattr(model, "use_niche_share", False):
        learned_niche_beta = float(model.niche_share_beta.detach().cpu().item())
        print(f"  learned niche_share_beta = {learned_niche_beta:.5f} "
              f"(>0 => crowded-popular-niche targets were discounted)")

    # NOVEL X1 (js-shrink): report the learned shrinkage intensity c (interpretable
    # readout — c→0 means the model voted the shrinkage off; larger c = more tail
    # capacity was over-fit). lambda_max = c/(c+min_freq) is the heaviest applied shrink.
    learned_js_c = None
    if getattr(model, "js_shrink", False):
        c_val = float(F.softplus(model.shrink_c.detach()).cpu().item())
        nz = model.item_freq[model.item_freq > 0]
        min_freq = float(nz.min().cpu().item()) if nz.numel() else 0.0
        lam_max = c_val / (c_val + min_freq) if (c_val + min_freq) > 0 else 0.0
        learned_js_c = c_val
        print(f"  learned js-shrink c = {c_val:.5f}  (lambda_max~{lam_max:.4f} at min_freq={min_freq:.0f}; "
              f"c->0 means shrinkage voted off)")

    # NOVEL Y1 (heat-target): report the learned diffusion temperature
    # T = softplus(heat_temp) — the interpretable readout (effective diffusion
    # radius). T->init (~0.0025) means the model voted the geometry off (delta
    # target); larger T => more soft mass diffused onto text-semantic neighbors.
    learned_heat_T = None
    if getattr(model, "use_heat", False):
        learned_heat_T = float(F.softplus(model.heat_temp.detach()).cpu().item())
        print(f"  learned heat-target T = {learned_heat_T:.5f}  (init~0.0025; "
              f"T->init means geometry voted off / delta target)")

    # NOVEL conn-gate: report the LEARNED connectivity-gate scalar
    # alpha = sigmoid(cg_alpha) (the pre-registered interpretable readout). alpha~0
    # (init sigmoid(-6)=0.0025) => gate voted off / additive baseline; larger alpha
    # => cold (low-users/item) items down-weight ID, up-weight frozen text. Also
    # report the learned slope. Captured from the FINAL weights.
    learned_conn_gate_alpha = None
    learned_conn_gate_slope = None
    if getattr(model, "conn_gate", False):
        learned_conn_gate_alpha = float(torch.sigmoid(model.cg_alpha.detach()).cpu().item())
        learned_conn_gate_slope = float(model.cg_slope.detach().cpu().item())
        print(f"  learned conn-gate alpha = {learned_conn_gate_alpha:.5f} "
              f"(init~0.0025; alpha->init means gate voted off / additive baseline), "
              f"slope = {learned_conn_gate_slope:.5f}")

    # ANALYST missing-ablation #2 (ANALYSIS 2026-07-03-1): TUNED z-fusion weight
    # frontier. The prior z-fusion comparator used an un-tuned 1:1 weight and
    # floored cold@10; the analyst flagged that a reviewer could object "maybe a
    # better weight bridges cold+warm." This sweeps the content share w in [0,1]
    # on the SAME final-epoch model (eval-only, no retrain — z-fusion never touches
    # training) and records the cold/warm/overall frontier, so the impossibility
    # boundary is a swept result, not a single-point artifact. Leak-free: identical
    # eval protocol; text frozen; z-standardization over candidates only.
    zfusion_sweep = None
    if getattr(args, "zfusion_sweep", "").strip():
        try:
            _ws = [float(x) for x in args.zfusion_sweep.split(",") if x.strip() != ""]
        except ValueError:
            _ws = []
        if _ws:
            print(f"\n=== z-fusion tuned-weight frontier sweep (final-epoch model, "
                  f"eval-only) over content weights {_ws} ===")
            zfusion_sweep = {}
            for _w in _ws:
                _m = evaluate(model, user_seqs, test_inters, n_items, pad_id,
                              args.max_seq_len, DEVICE, extra_history=test_extra,
                              subsample_users=0,
                              stratify_head=args.eval_stratify_head,
                              user_times=user_times, extra_times=val_time_extra,
                              cosine=args.cosine_scoring, cold_items=cold_items,
                              zfusion=True, zfusion_weight=_w)
                _cold = (_m.get("by_coldstart", {}) or {}).get("cold", {})
                _warm = (_m.get("by_coldstart", {}) or {}).get("warm", {})
                zfusion_sweep[f"{_w:g}"] = {
                    "content_weight": _w,
                    "overall_NDCG@10": _m.get("NDCG@10"),
                    "cold_NDCG@10": _cold.get("NDCG@10"),
                    "cold_n_hit@10": _cold.get("n_hit@10"),
                    "cold_n_hit@100": _cold.get("n_hit@100"),
                    "cold_MRR": _cold.get("MRR"),
                    "cold_n": _cold.get("n"),
                    "warm_NDCG@10": _warm.get("NDCG@10"),
                    "warm_n": _warm.get("n"),
                }
                print(f"  w_content={_w:g}: overall N@10={_m.get('NDCG@10'):.5f}  "
                      f"cold hit@10={_cold.get('n_hit@10')}  "
                      f"cold hit@100={_cold.get('n_hit@100')}  "
                      f"cold MRR={_cold.get('MRR'):.6f}  "
                      f"warm N@10={_warm.get('NDCG@10'):.5f}")

    # ---- Audit provenance manifest (Codex audit 2026-07-08, F2/fix#4) ----
    # Immutable link between this result and the code/data/environment state.
    import datetime as _dt
    import hashlib as _hl
    import socket as _sock
    import subprocess as _sp
    def _sha256(p):
        try:
            h = _hl.sha256()
            with open(p, "rb") as fh:
                for blk in iter(lambda: fh.read(1 << 20), b""):
                    h.update(blk)
            return h.hexdigest()
        except Exception as e:
            return f"unavailable: {e}"
    provenance = {
        "created_at": _dt.datetime.now().astimezone().isoformat(),
        "argv": sys.argv,
        "hostname": _sock.gethostname(),
        "python": sys.version.split()[0],
        "torch": torch.__version__,
        "cuda_device": (torch.cuda.get_device_name(0)
                         if torch.cuda.is_available() else None),
        "n_interactions": {"train": len(train_inters), "valid": len(valid_inters),
                            "test": len(test_inters)},
        "data_sha256": {
            "train_csv": _sha256(train_csv), "valid_csv": _sha256(valid_csv),
            "test_csv": _sha256(test_csv),
            "text_cache": _sha256(sbert_npy) if not args.no_sbert else None,
        },
        "best_test_epoch": best_test_epoch,
    }
    try:
        provenance["git_commit"] = _sp.check_output(
            ["git", "rev-parse", "HEAD"], cwd=str(ROOT), text=True).strip()
        provenance["git_branch"] = _sp.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=str(ROOT), text=True).strip()
        # dirty = any TRACKED file modified (untracked outputs don't count)
        provenance["git_dirty_tracked"] = bool(_sp.check_output(
            ["git", "status", "--porcelain", "-uno"], cwd=str(ROOT), text=True).strip())
    except Exception as e:
        provenance["git_commit"] = f"unavailable: {e}"

    out = {
        "category": args.category, "config": vars(args),
        "n_users": n_users, "n_items": n_items, "n_params": n_params,
        "provenance": provenance,
        "history": history,
        "zfusion_sweep": zfusion_sweep,
        "best_val_NDCG10": best_val_ndcg,
        "best_test": best_test_metrics,
        "learned_niche_share_beta": learned_niche_beta,
        "learned_js_shrink_c": learned_js_c,
        "learned_heat_target_T": learned_heat_T,
        "learned_conn_gate_alpha": learned_conn_gate_alpha,
        "learned_conn_gate_slope": learned_conn_gate_slope,
        "spectral_effective_rank": spectral_eff_rank,
        "spectral_bbp_rho_by_tercile": spectral_bbp_rho,
    }
    with out_path.open("w") as f:
        json.dump(out, f, indent=2)
    print(f"\nwrote {out_path}")
    # Per-user records sidecar (Codex fix#5): dataset, seed, user_id, target,
    # rank0, ndcg10, hr10, rr, pop_bucket — for bootstrap/tie/rank diagnostics.
    if best_test_user_records is not None:
        import gzip as _gz
        rec_path = Path(str(out_path).replace(".json", "") + ".users.jsonl.gz")
        ur = best_test_user_records
        with _gz.open(rec_path, "wt", encoding="utf-8") as fh:
            for i in range(len(ur["user_id"])):
                fh.write(json.dumps({
                    "dataset": args.category, "seed": args.seed,
                    "user_id": ur["user_id"][i],
                    "target_item_id": ur["target_item_id"][i],
                    "rank0": ur["rank0"][i], "ndcg10": ur["ndcg10"][i],
                    "hr10": ur["hr10"][i], "rr": ur["rr"][i],
                    "pop_bucket": ur["pop_bucket"][i]}) + "\n")
        print(f"wrote {rec_path} ({len(ur['user_id']):,} per-user records, best epoch {best_test_epoch})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
