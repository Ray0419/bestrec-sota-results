"""Minimal TIGER-style sequential recommender: RQ-VAE semantic IDs +
autoregressive Transformer decoder over those IDs.

TIGER (Rajput et al., NeurIPS 2023) decomposes each item into a sequence of
discrete "semantic ID" tokens via RQ-VAE on item content embeddings, then
trains a Transformer decoder to generate the next item's semantic ID tokens
autoregressively from the user's history (also in token form).

Why this might beat our SASRec-SBERT (0.054 on Video_Games / 0.018 on
Beauty_and_PC):
  - Vocab is tiny (4 codebooks * 256 codes = 1024 tokens) so we can use
    FULL softmax even on Beauty_and_PC — no sampled-softmax variance.
  - Each item produces multiple training tokens (4 per item), giving 4x
    denser gradient signal per training example.
  - Semantic IDs cluster similar items, so cold items inherit gradients
    from popular items with similar text.

Architecture (intentionally small to keep iteration fast):
  - RQ-VAE: encoder 384->256->32 latent, 4 residual VQ layers (256 codes
    each, d_code=32), decoder 32->256->384. EMA codebook updates.
  - Token Transformer: 2-layer decoder, d_model=64, 2 heads. Vocab is the
    union of 4 codebooks: each codeword has a unique global ID in [0, 1024).
    Sequence positions also encode WHICH layer this token is (0,1,2,3 mod 4).
  - Loss: standard next-token cross-entropy with full softmax (1024 vocab).
  - Inference: for each candidate item, compute log p(its 4 tokens | history).
    Rank items by score. Mask training items.

Usage:
    uv run python run_tiger_minimal.py Video_Games --rqvae-epochs 30 --epochs 30
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

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader

ROOT = Path(__file__).resolve().parent.parent
SPLIT_DIR = ROOT / "data_5core" / "5core" / "last_out"
EMB_CACHE_DIR = ROOT / "cache_5core"

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


# ---------------------------------------------------------------------------
# Data loading (matches run_sasrec_sbert.py / run_5core_benchmark.py)
# ---------------------------------------------------------------------------

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
    by_user = defaultdict(list)
    for u, i, _, t in train_inters:
        by_user[u].append((t, i))
    user_seqs = {}
    for u, lst in by_user.items():
        lst.sort()
        user_seqs[u] = [i for (_, i) in lst]
    return user_seqs


# ---------------------------------------------------------------------------
# RQ-VAE: residual vector quantization
# ---------------------------------------------------------------------------

class ResidualVQ(nn.Module):
    """L residual VQ layers, each with K codes of dim d_code, EMA updates.
    Forward: input x (B, d_code) -> quantized (B, d_code) + indices (B, L).

    Codebook initialization is deferred to first batch via `init_from_data()`
    (kmeans-style: sample latent vectors). This avoids codebook collapse
    that plain random init produces when latent-vector magnitudes differ from
    init std.
    """
    def __init__(self, d_code, n_layers=4, n_codes=256, ema_decay=0.99,
                  commitment_cost=0.25):
        super().__init__()
        self.n_layers = n_layers
        self.n_codes = n_codes
        self.d_code = d_code
        self.commitment_cost = commitment_cost
        self.ema_decay = ema_decay
        # Codebook per layer (n_layers, n_codes, d_code) — small random init,
        # overwritten by init_from_data() before training.
        self.register_buffer("codebooks", torch.randn(n_layers, n_codes, d_code) * 0.5)
        # EMA stats
        self.register_buffer("ema_cluster_size", torch.ones(n_layers, n_codes))
        self.register_buffer("ema_w", self.codebooks.clone())
        self.register_buffer("initialised", torch.zeros(1, dtype=torch.bool))

    @torch.no_grad()
    def init_from_data(self, z_sample):
        """Initialise codebooks by passing z_sample through residual stages and
        sampling random latent vectors at each stage. z_sample shape (N, d_code).
        N should be >= n_codes per layer for good coverage."""
        N = z_sample.shape[0]
        residual = z_sample.clone()
        for l in range(self.n_layers):
            # Sample n_codes random rows of residual as initial codebook
            if N >= self.n_codes:
                idx = torch.randperm(N, device=residual.device)[:self.n_codes]
            else:
                # Repeat with noise if not enough samples
                idx = torch.randint(0, N, (self.n_codes,), device=residual.device)
            self.codebooks[l] = residual[idx].clone() + 0.001 * torch.randn_like(self.codebooks[l])
            self.ema_w[l] = self.codebooks[l].clone()
            self.ema_cluster_size[l].fill_(1.0)
            # Update residual for next layer
            q, _ = self.quantize_layer(residual, l)
            residual = residual - q
        self.initialised.fill_(True)

    @torch.no_grad()
    def reset_dead_codes(self, z_sample):
        """For each layer, replace under-used codes with random samples from
        the current residual at that layer. Call periodically."""
        residual = z_sample.clone()
        for l in range(self.n_layers):
            # A code is "dead" if its EMA cluster size < threshold (e.g. 0.5)
            dead = self.ema_cluster_size[l] < 0.5
            n_dead = dead.sum().item()
            if n_dead > 0:
                idx_replace = torch.randperm(residual.shape[0], device=residual.device)[:n_dead]
                self.codebooks[l][dead] = residual[idx_replace] + 0.001 * torch.randn(n_dead, self.d_code, device=residual.device)
                self.ema_w[l][dead] = self.codebooks[l][dead].clone()
                self.ema_cluster_size[l][dead] = 1.0
            q, _ = self.quantize_layer(residual, l)
            residual = residual - q

    def quantize_layer(self, x, layer_idx):
        """x: (B, d_code). Returns (quantized (B,d_code), indices (B,))."""
        cb = self.codebooks[layer_idx]            # (K, d)
        # Compute L2 distances
        d2 = (x ** 2).sum(-1, keepdim=True) + (cb ** 2).sum(-1) - 2 * (x @ cb.T)
        idx = d2.argmin(-1)                       # (B,)
        q = cb[idx]                                # (B, d)
        return q, idx

    def forward(self, z):
        """z: (B, d_code). Returns (z_q (B,d_code), all_indices (B, L), commit_loss)."""
        residual = z
        z_q = torch.zeros_like(z)
        all_idx = []
        commit_loss = 0.0
        for l in range(self.n_layers):
            q, idx = self.quantize_layer(residual, l)
            # Straight-through estimator: gradient flows from z_q back to residual
            q_st = residual + (q - residual).detach()
            z_q = z_q + q_st
            commit_loss = commit_loss + F.mse_loss(residual, q.detach())
            residual = residual - q.detach()
            all_idx.append(idx)
        return z_q, torch.stack(all_idx, dim=1), commit_loss

    @torch.no_grad()
    def ema_update(self, z, indices):
        """EMA codebook update.
        z: (B, d_code). indices: (B, L). Uses residual-at-layer-l for codebook l."""
        residual = z.clone()
        for l in range(self.n_layers):
            idx = indices[:, l]                     # (B,)
            one_hot = F.one_hot(idx, self.n_codes).float()  # (B, K)
            cluster_size = one_hot.sum(0)            # (K,)
            dw = one_hot.T @ residual                # (K, d)

            self.ema_cluster_size[l].mul_(self.ema_decay).add_(cluster_size, alpha=1 - self.ema_decay)
            self.ema_w[l].mul_(self.ema_decay).add_(dw, alpha=1 - self.ema_decay)

            # Laplace smoothing
            n = self.ema_cluster_size[l].sum()
            cluster_size_smooth = (self.ema_cluster_size[l] + 1e-5) / (n + self.n_codes * 1e-5) * n
            normalised = self.ema_w[l] / cluster_size_smooth.unsqueeze(-1)
            self.codebooks[l] = normalised

            # Update residual for next layer using the SELECTED (non-EMA) codeword
            q = self.codebooks[l][idx]
            residual = residual - q


class RQVAE(nn.Module):
    def __init__(self, in_dim=384, hidden=256, d_code=32, n_layers=4, n_codes=256):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(in_dim, hidden), nn.GELU(),
            nn.Linear(hidden, d_code),
        )
        self.decoder = nn.Sequential(
            nn.Linear(d_code, hidden), nn.GELU(),
            nn.Linear(hidden, in_dim),
        )
        self.vq = ResidualVQ(d_code=d_code, n_layers=n_layers, n_codes=n_codes)

    def forward(self, x):
        z = self.encoder(x)                         # (B, d_code)
        z_q, idx, commit = self.vq(z)
        x_recon = self.decoder(z_q)
        return x_recon, z, z_q, idx, commit


def train_rqvae(embeddings: np.ndarray, n_epochs=30, batch_size=512, lr=1e-3,
                  d_code=32, n_codebooks=4, codebook_size=256, hidden=256,
                  commitment_cost=0.25, seed=0, dead_code_reset_every=5,
                  encoder_pretrain_epochs=2):
    """Train RQ-VAE on item embeddings. Returns (model, semantic_ids array (N, n_codebooks)).

    Key technique to avoid codebook collapse:
      1. Pretrain ENCODER+DECODER for a few epochs WITHOUT quantization (uses
         the encoder's z directly through the decoder). This stabilises the
         latent distribution.
      2. Initialise codebooks from a sample of the encoder's z outputs.
      3. Reset dead codes every `dead_code_reset_every` epochs."""
    torch.manual_seed(seed); np.random.seed(seed)
    n_items, in_dim = embeddings.shape
    model = RQVAE(in_dim=in_dim, hidden=hidden, d_code=d_code,
                    n_layers=n_codebooks, n_codes=codebook_size).to(DEVICE)
    model.vq.commitment_cost = commitment_cost
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    emb_t = torch.from_numpy(embeddings.astype(np.float32)).to(DEVICE)

    print(f"  RQ-VAE: {n_items:,} items, d_code={d_code}, {n_codebooks} codebooks of {codebook_size} codes")
    print(f"  RQ-VAE: pretrain {encoder_pretrain_epochs} epochs (no quantization), then {n_epochs - encoder_pretrain_epochs} with quantization")
    t0 = time.time()

    # Phase 1: pretrain encoder + decoder WITHOUT quantization to stabilise z
    for epoch in range(1, encoder_pretrain_epochs + 1):
        perm = torch.randperm(n_items, device=DEVICE)
        recons, n_batches = 0.0, 0
        for s in range(0, n_items, batch_size):
            batch_idx = perm[s:s + batch_size]
            x = emb_t[batch_idx]
            z = model.encoder(x)
            x_recon = model.decoder(z)
            loss = F.mse_loss(x_recon, x)
            opt.zero_grad(); loss.backward(); opt.step()
            recons += loss.item(); n_batches += 1
        print(f"    pretrain epoch {epoch}: recon={recons/n_batches:.4f}  [{time.time()-t0:.1f}s]")

    # Phase 2: initialise codebooks from a SAMPLE of encoder outputs
    with torch.no_grad():
        n_samples = min(n_items, max(codebook_size * 8, 2048))
        sample_idx = torch.randperm(n_items, device=DEVICE)[:n_samples]
        z_sample = model.encoder(emb_t[sample_idx])
        model.vq.init_from_data(z_sample)
    print(f"    codebooks initialised from {n_samples:,} encoder samples")

    # Phase 3: train with quantization
    for epoch in range(encoder_pretrain_epochs + 1, n_epochs + 1):
        perm = torch.randperm(n_items, device=DEVICE)
        recons, commits, n_batches = 0.0, 0.0, 0
        for s in range(0, n_items, batch_size):
            batch_idx = perm[s:s + batch_size]
            x = emb_t[batch_idx]                    # (B, in_dim)
            x_recon, z, z_q, idx, commit = model(x)
            recon = F.mse_loss(x_recon, x)
            loss = recon + commitment_cost * commit
            opt.zero_grad(); loss.backward(); opt.step()
            # EMA codebook update with the current encoder z + the indices we just used
            with torch.no_grad():
                model.vq.ema_update(z.detach(), idx)
            recons += recon.item(); commits += commit.item(); n_batches += 1
        # Dead-code reset every N epochs
        if dead_code_reset_every and epoch % dead_code_reset_every == 0 and epoch < n_epochs:
            with torch.no_grad():
                n_samples = min(n_items, codebook_size * 4)
                sample_idx = torch.randperm(n_items, device=DEVICE)[:n_samples]
                z_sample = model.encoder(emb_t[sample_idx])
                before = sum((model.vq.ema_cluster_size[l] < 0.5).sum().item() for l in range(n_codebooks))
                model.vq.reset_dead_codes(z_sample)
                if before > 0:
                    print(f"    epoch {epoch}: reset {before} dead codes")
        if epoch % 10 == 0 or epoch == n_epochs:
            print(f"    epoch {epoch:>3d}: recon={recons/n_batches:.4f}  commit={commits/n_batches:.4f}  [{time.time()-t0:.1f}s]")

    # Final encode all items
    model.eval()
    with torch.no_grad():
        z = model.encoder(emb_t)
        _, semantic_ids, _ = model.vq(z)
    sid = semantic_ids.cpu().numpy()                # (n_items, n_codebooks)

    # Diagnostic: utilisation per layer
    print(f"  RQ-VAE diagnostic:")
    for l in range(n_codebooks):
        uniq = len(set(sid[:, l].tolist()))
        print(f"    layer {l}: {uniq}/{codebook_size} unique codes used "
              f"({uniq/codebook_size*100:.0f}%)")
    # Distinct full IDs
    sid_tuples = set(tuple(row) for row in sid)
    print(f"    distinct full semantic IDs: {len(sid_tuples):,} / {n_items:,} items")
    return model, sid


# ---------------------------------------------------------------------------
# Token transformer over semantic IDs
# ---------------------------------------------------------------------------

class TokenTransformer(nn.Module):
    """Autoregressive Transformer over a flat token sequence.
    Each user history is a sequence of (item_1 tokens) + (item_2 tokens) + ...
    where each item contributes n_codebooks tokens.

    Tokens are encoded with a single Embedding table over the UNIONED vocab
    (n_codebooks * codebook_size). The LAYER of each token (which codebook it
    belongs to) is encoded by a separate small embedding added to the token.

    max_tokens = (max_items + 1) * n_codebooks  — the +1 gives space for
    beam expansion tokens during eval.
    """
    def __init__(self, n_codebooks=4, codebook_size=256, max_items=50,
                  d_model=64, n_layers=2, n_heads=2, dropout=0.2):
        super().__init__()
        self.n_codebooks = n_codebooks
        self.codebook_size = codebook_size
        self.vocab_size = n_codebooks * codebook_size + 1  # +1 for pad
        self.pad_id = self.vocab_size - 1
        self.max_items = max_items
        # +1 extra item slot for beam-expansion tokens at eval time
        self.max_tokens = (max_items + 1) * n_codebooks
        self.d_model = d_model

        self.tok_emb = nn.Embedding(self.vocab_size, d_model, padding_idx=self.pad_id)
        self.layer_emb = nn.Embedding(n_codebooks, d_model)
        self.pos_emb = nn.Embedding(self.max_tokens, d_model)
        nn.init.normal_(self.tok_emb.weight, std=0.02)
        nn.init.normal_(self.layer_emb.weight, std=0.02)
        nn.init.normal_(self.pos_emb.weight, std=0.02)
        self.drop = nn.Dropout(dropout)

        layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=n_heads, dim_feedforward=4 * d_model,
            dropout=dropout, activation="gelu", batch_first=True, norm_first=True)
        self.transformer = nn.TransformerEncoder(layer, num_layers=n_layers)
        self.ln_final = nn.LayerNorm(d_model)
        # Output: scores over vocab (1024+1 = 1025). Tied to tok_emb in forward.

    def forward(self, token_ids):
        """token_ids: (B, T) where T = max_items * n_codebooks.
        Returns logits (B, T, vocab_size)."""
        B, T = token_ids.shape
        device = token_ids.device

        # Layer index for each token (mod n_codebooks)
        positions = torch.arange(T, device=device)
        layer_idx = positions % self.n_codebooks       # (T,)

        x = self.tok_emb(token_ids)                    # (B, T, d)
        x = x + self.layer_emb(layer_idx).unsqueeze(0).expand(B, -1, -1)
        x = x + self.pos_emb(positions).unsqueeze(0).expand(B, -1, -1)
        x = self.drop(x)

        causal = torch.triu(torch.ones(T, T, dtype=torch.bool, device=device), diagonal=1)
        h = self.transformer(x, mask=causal)
        h = self.ln_final(h)                            # (B, T, d)

        # Logits via tied embedding (full softmax over 1025 vocab — small!)
        logits = h @ self.tok_emb.weight.T              # (B, T, vocab_size)
        return logits

    def encode(self, token_ids):
        """Return hidden states without computing logits."""
        B, T = token_ids.shape
        device = token_ids.device
        positions = torch.arange(T, device=device)
        layer_idx = positions % self.n_codebooks

        x = self.tok_emb(token_ids)
        x = x + self.layer_emb(layer_idx).unsqueeze(0).expand(B, -1, -1)
        x = x + self.pos_emb(positions).unsqueeze(0).expand(B, -1, -1)
        x = self.drop(x)
        causal = torch.triu(torch.ones(T, T, dtype=torch.bool, device=device), diagonal=1)
        h = self.transformer(x, mask=causal)
        h = self.ln_final(h)
        return h


def items_to_tokens(item_ids: list[int], sid: np.ndarray, codebook_size: int):
    """Convert item IDs to a flat token sequence using global token IDs.
    Token for codebook l, code c = l * codebook_size + c.
    Returns numpy int array of length n_codebooks * len(item_ids)."""
    sid_for_items = sid[item_ids]                       # (n_items, n_codebooks)
    n_cb = sid_for_items.shape[1]
    offsets = (np.arange(n_cb) * codebook_size).reshape(1, -1)
    global_tokens = sid_for_items + offsets             # (n_items, n_codebooks)
    return global_tokens.reshape(-1).astype(np.int64)


class TigerDataset(Dataset):
    def __init__(self, user_seqs, sid, codebook_size, max_items, pad_id):
        self.user_seqs = user_seqs
        self.sid = sid
        self.codebook_size = codebook_size
        self.n_codebooks = sid.shape[1]
        self.max_items = max_items
        # Match TokenTransformer.max_tokens (with +1 buffer)
        self.max_tokens = (max_items + 1) * self.n_codebooks
        self.pad_id = pad_id
        self.examples = [(u, seq) for u, seq in user_seqs.items() if len(seq) >= 2]

    def __len__(self):
        return len(self.examples)

    def __getitem__(self, idx):
        u, seq = self.examples[idx]
        # Truncate to most-recent max_items+1 items, then predict next from prefix
        if len(seq) > self.max_items + 1:
            seq = seq[-(self.max_items + 1):]
        # Convert ALL items in the sequence to tokens (including the last, which is the target)
        all_tokens = items_to_tokens(seq, self.sid, self.codebook_size)
        # input = all_tokens[:-n_codebooks], target = all_tokens[n_codebooks:]
        # That is: feed N items' tokens, predict next item's tokens.
        # Right-pad both to max_tokens.
        L = len(all_tokens) - self.n_codebooks  # number of "predicted-token" positions
        # Actually simplest: input is the first L_inp tokens, target shifted by 1
        # where L_inp = total - n_codebooks (we drop the last item's tokens from input;
        # we use them as target). But standard is: input = seq[:-1] (token), target = seq[1:].
        # Here we just shift by 1 token (not by 1 item) — this matches LM-style next-token
        # prediction and naturally handles the layer dimension via layer_emb.
        input_tokens = all_tokens[:-1].copy()
        target_tokens = all_tokens[1:].copy()
        # Right-pad
        L = len(input_tokens)
        pad_amount = self.max_tokens - L
        if pad_amount > 0:
            input_tokens = np.concatenate([input_tokens, np.full(pad_amount, self.pad_id, dtype=np.int64)])
            target_tokens = np.concatenate([target_tokens, np.full(pad_amount, self.pad_id, dtype=np.int64)])
        elif pad_amount < 0:
            # Sequence too long — truncate (shouldn't happen given our truncation above)
            input_tokens = input_tokens[:self.max_tokens]
            target_tokens = target_tokens[:self.max_tokens]
        return torch.from_numpy(input_tokens), torch.from_numpy(target_tokens)


def collate_batch(batch):
    inputs = torch.stack([b[0] for b in batch])
    targets = torch.stack([b[1] for b in batch])
    return inputs, targets


# ---------------------------------------------------------------------------
# Training & evaluation
# ---------------------------------------------------------------------------

def train_one_epoch(model, loader, opt, pad_id, device, grad_clip=5.0):
    model.train()
    total_loss = 0.0; n_batches = 0
    for inputs, targets in loader:
        inputs = inputs.to(device, non_blocking=True)
        targets = targets.to(device, non_blocking=True)
        logits = model(inputs)                          # (B, T, vocab)
        B, T, V = logits.shape
        loss = F.cross_entropy(logits.reshape(B*T, V), targets.reshape(B*T),
                                 ignore_index=pad_id)
        opt.zero_grad(); loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
        opt.step()
        total_loss += loss.item(); n_batches += 1
    return total_loss / max(1, n_batches)


def evaluate_beam(model, user_seqs, test_inters, sid, codebook_size, max_items,
                    pad_id, device, n_codebooks, beam_width=128, top_k=10,
                    batch_size=64, extra_history=None, subsample_users=None,
                    subsample_seed=0):
    """TIGER-style beam-search eval. For each user:
      1. Encode user's history (4*L tokens) via one forward pass.
      2. Beam search next n_codebooks tokens (greedy per layer, beam width K).
         At each layer l, score each candidate's l-th token via the model's
         prediction at the previous position. Keep top-K beams.
      3. After all n_codebooks layers, each beam is a complete semantic ID.
         Map each to the item with matching sid (if any).
      4. Rank items by joint log-prob within the beam; items NOT in the
         beam are ranked beyond top_k.

    NDCG@K is computed as 1/log2(rank+2) if the test item's rank within
    the beam < K, else 0."""
    model.eval()
    test_dict = {u: i for u, i, _, _ in test_inters}
    users = sorted(test_dict.keys())
    if subsample_users and subsample_users < len(users):
        rng = np.random.RandomState(subsample_seed)
        users = sorted(rng.choice(users, subsample_users, replace=False).tolist())
    extra = extra_history or {}
    n_eval = len(users)
    # match TokenTransformer.max_tokens (with +1 buffer for beam expansion)
    max_tokens = (max_items + 1) * n_codebooks
    ndcg, hr, rr = [], [], []
    print(f"  beam eval {n_eval:,} users in batches of {batch_size}, beam_width={beam_width}...")
    t0 = time.time()

    # Pre-compute item -> semantic_id_tuple lookup
    sid_to_items: dict[tuple, list[int]] = defaultdict(list)
    for i in range(sid.shape[0]):
        sid_to_items[tuple(sid[i].tolist())].append(i)

    # For each user batch
    with torch.no_grad():
        for s in range(0, n_eval, batch_size):
            batch_users = users[s:s + batch_size]
            B = len(batch_users)
            input_ids = torch.full((B, max_tokens), pad_id, dtype=torch.long, device=device)
            train_items_list = []
            real_tok_len = []
            for k, u in enumerate(batch_users):
                seq = list(user_seqs.get(u, []))
                if u in extra:
                    seq = seq + list(extra[u])
                train_items_list.append(seq)
                if not seq:
                    real_tok_len.append(0); continue
                seq_trunc = seq[-max_items:]
                tokens = items_to_tokens(seq_trunc, sid, codebook_size)
                L_tok = len(tokens)
                input_ids[k, :L_tok] = torch.from_numpy(tokens).to(device)
                real_tok_len.append(L_tok)

            # Initial encode of history
            h = model.encode(input_ids)              # (B, T, d)
            last_real_pos = torch.tensor([max(0, rl - 1) for rl in real_tok_len],
                                          device=device)
            last_h = h[torch.arange(B, device=device), last_real_pos, :]  # (B, d)

            # First layer (layer 0): score the 256 layer-0 tokens
            logits = last_h @ model.tok_emb.weight.T          # (B, vocab)
            log_probs = F.log_softmax(logits, dim=-1)         # (B, vocab)
            layer0_lp = log_probs[:, :codebook_size]          # (B, codebook_size)
            # Top-K layer-0 tokens
            k0 = min(beam_width, codebook_size)
            top0 = torch.topk(layer0_lp, k0, dim=-1)
            # beam_tokens: (B, k0) -- global token IDs (codebook 0 offset = 0)
            beam_tokens = top0.indices                         # (B, k0) layer-0 codes
            beam_logp = top0.values                            # (B, k0)
            # beam_seq tracks the actual code indices per layer (B, k0, layer)
            beam_seq = beam_tokens.unsqueeze(-1)               # (B, k0, 1) -- layer-0 codes

            # Layers 1..n_codebooks-1: expand each beam, score next token
            for layer in range(1, n_codebooks):
                K = beam_seq.shape[1]
                # Build expanded input for each (user, beam): history tokens + beam codes so far (with offsets)
                ext_input = input_ids.unsqueeze(1).expand(B, K, max_tokens).clone()  # (B, K, T)
                # For each user, place beam codes at positions real_tok_len[k]..real_tok_len[k]+layer-1
                # Need global token IDs from beam_seq: code_at_layer_l + l*codebook_size
                offsets = (torch.arange(layer, device=device) * codebook_size).view(1, 1, layer)
                beam_globals = beam_seq + offsets              # (B, K, layer) global tokens
                for k in range(B):
                    pos = real_tok_len[k]
                    if pos + layer > max_tokens:
                        continue
                    ext_input[k, :, pos:pos + layer] = beam_globals[k]
                ext_flat = ext_input.reshape(B * K, max_tokens)
                # One forward pass for B*K sequences
                h_ext = model.encode(ext_flat)                 # (B*K, T, d)
                # The hidden we need is at position real_tok_len[k] + layer - 1 (predicts the layer-th token)
                pred_pos_per_user = torch.tensor([max(0, rl - 1 + layer) for rl in real_tok_len],
                                                    device=device)
                pred_pos = pred_pos_per_user.unsqueeze(1).expand(B, K).reshape(-1)  # (B*K,)
                pred_h = h_ext[torch.arange(B * K, device=device), pred_pos, :]  # (B*K, d)
                logits_l = pred_h @ model.tok_emb.weight.T     # (B*K, vocab)
                log_probs_l = F.log_softmax(logits_l, dim=-1).view(B, K, -1)  # (B, K, vocab)
                # Restrict to layer-l tokens: indices [layer*codebook_size, (layer+1)*codebook_size)
                start = layer * codebook_size
                layer_lp = log_probs_l[:, :, start:start + codebook_size]  # (B, K, codebook_size)
                # Compute joint log-prob for each (beam, next_code): existing + new
                # joint shape: (B, K, codebook_size)
                joint = beam_logp.unsqueeze(-1) + layer_lp
                # Flatten and pick top beam_width across (K * codebook_size)
                Knext = min(beam_width, K * codebook_size)
                joint_flat = joint.view(B, -1)
                top_flat = torch.topk(joint_flat, Knext, dim=-1)
                top_logp = top_flat.values                     # (B, Knext)
                top_idx = top_flat.indices                     # (B, Knext)
                # Decode: prev_beam_idx, new_code
                prev_beam = top_idx // codebook_size            # (B, Knext)
                new_code = top_idx % codebook_size              # (B, Knext)
                # Update beam_seq, beam_logp
                # beam_seq[B, K, layer] -> beam_seq_new[B, Knext, layer+1]
                # gather from beam_seq using prev_beam, then concat new_code
                # gathered_seq[B, Knext, layer]
                gathered = torch.gather(
                    beam_seq, 1,
                    prev_beam.unsqueeze(-1).expand(B, Knext, layer)
                )
                beam_seq = torch.cat([gathered, new_code.unsqueeze(-1)], dim=-1)  # (B, Knext, layer+1)
                beam_logp = top_logp

            # beam_seq: (B, K, n_codebooks). Map each to item ID.
            beam_seq_np = beam_seq.cpu().numpy()
            beam_logp_np = beam_logp.cpu().numpy()
            for k, u in enumerate(batch_users):
                if real_tok_len[k] == 0:
                    ndcg.append(0.0); hr.append(0.0); rr.append(0.0); continue
                tgt_item = test_dict[u]
                tgt_sid = tuple(sid[tgt_item].tolist())
                user_train = set(train_items_list[k])
                # Walk through beam (already sorted by joint log-prob descending)
                # For each beam-tuple, look up items; sort items within same SID
                # arbitrarily but consistently (by item id ascending).
                rank = -1
                pos = 0
                seen_items_in_rank = set()
                for b in range(beam_seq_np.shape[1]):
                    sid_tuple = tuple(beam_seq_np[k, b].tolist())
                    items = sid_to_items.get(sid_tuple, [])
                    for it in sorted(items):
                        if it in user_train or it in seen_items_in_rank:
                            continue
                        seen_items_in_rank.add(it)
                        if it == tgt_item:
                            rank = pos
                            break
                        pos += 1
                    if rank != -1:
                        break
                # Compute metrics
                if rank == -1 or rank >= top_k:
                    ndcg.append(0.0); hr.append(0.0)
                    rr.append(1.0 / (rank + 1) if rank != -1 else 0.0)
                else:
                    ndcg.append(1.0 / math.log2(rank + 2)); hr.append(1.0)
                    rr.append(1.0 / (rank + 1))
            if (s // batch_size) % 20 == 0:
                print(f"    [{s + B:,}/{n_eval:,}  elapsed {time.time()-t0:.1f}s]")
    print(f"  beam eval done in {time.time()-t0:.1f}s")
    return {"NDCG@10": float(np.mean(ndcg)) if ndcg else 0.0,
            "HR@10":   float(np.mean(hr))   if hr   else 0.0,
            "MRR":     float(np.mean(rr))   if rr   else 0.0,
            "n_eval":  len(users)}


def evaluate(model, user_seqs, test_inters, sid, codebook_size, max_items,
              pad_id, device, n_codebooks, top_k=10, batch_size=256,
              extra_history=None):
    """For each test (u, target), encode user's history as tokens, then score
    every candidate item by P(item's tokens | history) = product over the 4
    next-token probabilities given the prefix.

    Trick to make this fast: we compute the hidden state h at the position
    where the user's history ends (i.e. after all input tokens of the prefix).
    Then we autoregressively step through the n_codebooks tokens of each
    candidate item, computing the log-probability at each step.

    BUT for full-catalog ranking that's expensive. A faster approximation:
    use just the FIRST-LAYER token probability (i.e. score item by p(t0 | hist))
    Note this is exact for codebook 0 but ignores codebooks 1,2,3.

    For now we use the EXACT product over all 4 tokens via per-item incremental
    decoding: feed the prefix + each candidate's first j tokens to get the
    distribution for token j+1. This is O(n_items * n_codebooks) hidden-state
    computations per user. With n_items=25K (Video_Games) this is ~100K
    forward passes per user — too slow.

    Production-realistic approximation used here:
      Score(item) = log p(token_0 | hist) + log p(token_1 | hist + token_0_of_item) + ...
    But the "hist + token_0_of_item" step requires a forward pass per (user, item).

    SIMPLER approximation we'll use: score = sum over j of log p(token_j | h_last)
    where h_last is the hidden state at the LAST POSITION of the user history.
    Effectively we treat the 4 tokens as if they were jointly conditioned on
    just the history (not on each other). This is biased but very fast — we
    can rank all n_items candidates in one forward pass.

    Sanity: this is essentially what SASRec does — score by dot product to a
    single hidden — but lifted into token space.
    """
    model.eval()
    test_dict = {u: i for u, i, _, _ in test_inters}
    users = sorted(test_dict.keys())
    extra = extra_history or {}
    ndcg, hr, rr = [], [], []
    n_eval = len(users)
    max_tokens = max_items * n_codebooks
    print(f"  evaluating {n_eval:,} users in batches of {batch_size}...")
    t0 = time.time()

    # Pre-compute global tokens for all items: (n_all_items, n_codebooks)
    n_all = sid.shape[0]
    offsets = (np.arange(n_codebooks) * codebook_size).reshape(1, -1)
    item_global_tokens = (sid + offsets).astype(np.int64)
    item_tokens_t = torch.from_numpy(item_global_tokens).to(device)  # (n_all, n_codebooks)

    with torch.no_grad():
        for s in range(0, n_eval, batch_size):
            batch_users = users[s:s + batch_size]
            B = len(batch_users)
            input_ids = torch.full((B, max_tokens), pad_id, dtype=torch.long, device=device)
            train_items_list = []
            real_tok_len = []
            for k, u in enumerate(batch_users):
                seq = list(user_seqs.get(u, []))
                if u in extra:
                    seq = seq + list(extra[u])
                train_items_list.append(seq)
                if not seq:
                    real_tok_len.append(0); continue
                seq_trunc = seq[-max_items:]
                tokens = items_to_tokens(seq_trunc, sid, codebook_size)
                L_tok = len(tokens)
                input_ids[k, :L_tok] = torch.from_numpy(tokens).to(device)
                real_tok_len.append(L_tok)

            # Get hidden states
            h = model.encode(input_ids)                  # (B, T, d)
            # Last real position's hidden — this is the position whose NEXT
            # token would be the first token of the next item.
            last_real_pos = torch.tensor([max(0, rl - 1) for rl in real_tok_len],
                                          device=device)
            last_h = h[torch.arange(B, device=device), last_real_pos, :]  # (B, d)

            # Score every item by sum_j log p(token_j of item | last_h).
            # NOTE: this ignores the autoregressive coupling between tokens
            # but is a fast approximation that lets us rank all n_all items
            # in one matmul.
            logits = last_h @ model.tok_emb.weight.T     # (B, vocab_size)
            log_probs = F.log_softmax(logits, dim=-1)    # (B, vocab_size)

            # For each user, sum log_probs of the candidate's n_codebooks tokens
            # item_tokens_t is (n_all, n_codebooks). Gather log_probs[i, item_tokens_t[j, l]]
            # final shape: (B, n_all)
            # Use gather: log_probs[:, item_tokens_t] -> (B, n_all, n_codebooks)
            scores = log_probs.gather(
                1, item_tokens_t.flatten().unsqueeze(0).expand(B, -1)
            ).view(B, n_all, n_codebooks).sum(dim=-1)    # (B, n_all)

            # Mask user's history items
            for k, items in enumerate(train_items_list):
                if items:
                    scores[k, items] = -float("inf")

            # Rank target
            for k, u in enumerate(batch_users):
                if real_tok_len[k] == 0:
                    ndcg.append(0.0); hr.append(0.0); rr.append(0.0); continue
                tgt = test_dict[u]
                tgt_score = scores[k, tgt].item()
                if math.isnan(tgt_score):
                    ndcg.append(0.0); hr.append(0.0); rr.append(0.0); continue
                rank0 = int((scores[k] > tgt_score).sum().item())
                if rank0 < top_k:
                    ndcg.append(1.0 / math.log2(rank0 + 2)); hr.append(1.0)
                else:
                    ndcg.append(0.0); hr.append(0.0)
                rr.append(1.0 / (rank0 + 1))
            if (s // batch_size) % 20 == 0:
                print(f"    [{s + B:,}/{n_eval:,}  elapsed {time.time()-t0:.1f}s]")
    print(f"  eval done in {time.time()-t0:.1f}s")
    return {"NDCG@10": float(np.mean(ndcg)) if ndcg else 0.0,
            "HR@10":   float(np.mean(hr))   if hr   else 0.0,
            "MRR":     float(np.mean(rr))   if rr   else 0.0,
            "n_eval":  len(users)}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("category")
    ap.add_argument("--rqvae-epochs", type=int, default=30)
    ap.add_argument("--rqvae-batch", type=int, default=512)
    ap.add_argument("--rqvae-lr", type=float, default=1e-3)
    ap.add_argument("--n-codebooks", type=int, default=4)
    ap.add_argument("--codebook-size", type=int, default=256)
    ap.add_argument("--d-code", type=int, default=32)
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--batch-size", type=int, default=256)
    ap.add_argument("--max-items", type=int, default=50)
    ap.add_argument("--d-model", type=int, default=64)
    ap.add_argument("--n-layers", type=int, default=2)
    ap.add_argument("--n-heads", type=int, default=2)
    ap.add_argument("--dropout", type=float, default=0.2)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--eval-every", type=int, default=5)
    ap.add_argument("--beam-width", type=int, default=128,
                     help="Beam search width at eval time")
    ap.add_argument("--eval-subsample", type=int, default=0,
                     help="Periodic eval uses this many random test users "
                          "(0 = full set). Final eval is always full.")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    out_path = Path(args.out) if args.out else (Path(__file__).parent /
                                                  f"results_tiger_minimal_{args.category}.json")

    print(f"=== {args.category}: load splits ===")
    train_rows = load_split_csv(SPLIT_DIR / f"{args.category}.train.csv")
    valid_rows = load_split_csv(SPLIT_DIR / f"{args.category}.valid.csv")
    test_rows = load_split_csv(SPLIT_DIR / f"{args.category}.test.csv")
    train_inters, valid_inters, test_inters, user_list, item_list = reindex(
        train_rows, valid_rows, test_rows)
    n_users, n_items = len(user_list), len(item_list)
    print(f"  n_users={n_users:,}  n_items={n_items:,}")
    user_seqs = build_user_sequences(train_inters)

    # Load SBERT embeddings
    sbert_npy = EMB_CACHE_DIR / f"sbert_titles_{args.category}.npy"
    sbert_emb = np.load(sbert_npy).astype(np.float32)
    print(f"  loaded SBERT {sbert_emb.shape} from {sbert_npy}")

    # Step 1: train RQ-VAE on item SBERT embeddings
    print(f"\n=== Train RQ-VAE ===")
    rqvae_model, sid = train_rqvae(
        sbert_emb,
        n_epochs=args.rqvae_epochs, batch_size=args.rqvae_batch, lr=args.rqvae_lr,
        d_code=args.d_code, n_codebooks=args.n_codebooks,
        codebook_size=args.codebook_size)

    # Step 2: build the token Transformer
    print(f"\n=== Build TokenTransformer (d={args.d_model}, layers={args.n_layers}, heads={args.n_heads}) ===")
    model = TokenTransformer(
        n_codebooks=args.n_codebooks, codebook_size=args.codebook_size,
        max_items=args.max_items, d_model=args.d_model,
        n_layers=args.n_layers, n_heads=args.n_heads,
        dropout=args.dropout).to(DEVICE)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"  total params: {n_params:,}")
    pad_id = model.pad_id

    # Step 3: training data and loop
    dataset = TigerDataset(user_seqs, sid, args.codebook_size, args.max_items, pad_id)
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True,
                          num_workers=0, collate_fn=collate_batch, drop_last=False)
    print(f"  {len(dataset):,} training examples / {len(loader):,} batches per epoch")

    opt = torch.optim.Adam(model.parameters(), lr=args.lr, weight_decay=1e-5)

    print(f"\n=== Train for {args.epochs} epochs ===")
    best_val_ndcg = 0.0
    best_test = None
    history = []
    valid_dict = {u: i for u, i, _, _ in valid_inters}
    test_extra = {u: [i] for u, i in valid_dict.items()}
    for epoch in range(1, args.epochs + 1):
        t0 = time.time()
        train_loss = train_one_epoch(model, loader, opt, pad_id, DEVICE)
        ep_time = time.time() - t0
        log = {"epoch": epoch, "train_loss": train_loss, "epoch_time_s": ep_time}
        if epoch % args.eval_every == 0 or epoch == args.epochs:
            # Periodic eval: subsample to keep wall time tractable on huge datasets
            subs = args.eval_subsample if epoch < args.epochs else 0  # final eval = full set
            val_metrics = evaluate_beam(model, user_seqs, valid_inters, sid,
                                          args.codebook_size, args.max_items, pad_id,
                                          DEVICE, args.n_codebooks,
                                          beam_width=args.beam_width,
                                          subsample_users=subs)
            test_metrics = evaluate_beam(model, user_seqs, test_inters, sid,
                                           args.codebook_size, args.max_items, pad_id,
                                           DEVICE, args.n_codebooks,
                                           beam_width=args.beam_width,
                                           extra_history=test_extra,
                                           subsample_users=subs)
            log["val"] = val_metrics; log["test"] = test_metrics
            print(f"  epoch {epoch:>3d}  loss={train_loss:.4f}  val_NDCG={val_metrics['NDCG@10']:.4f}  "
                  f"test_NDCG={test_metrics['NDCG@10']:.4f}  test_HR={test_metrics['HR@10']:.4f}  "
                  f"({ep_time:.1f}s)")
            if val_metrics["NDCG@10"] > best_val_ndcg:
                best_val_ndcg = val_metrics["NDCG@10"]
                best_test = test_metrics
        else:
            print(f"  epoch {epoch:>3d}  loss={train_loss:.4f}  ({ep_time:.1f}s)")
        history.append(log)

    print(f"\n=== Best by val NDCG@10 ===")
    print(f"  val={best_val_ndcg:.4f}  test={best_test}")
    out = {"category": args.category, "config": vars(args),
            "n_users": n_users, "n_items": n_items, "n_params": n_params,
            "history": history, "best_val_NDCG10": best_val_ndcg,
            "best_test": best_test}
    json.dump(out, out_path.open("w"), indent=2,
                default=lambda o: float(o) if hasattr(o, "item") else str(o))
    print(f"\nwrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
