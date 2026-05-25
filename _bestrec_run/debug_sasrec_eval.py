"""Diagnostic: check whether SASRec eval is computing the right rank.
Suspicion: NDCG=0.99 implies the test item is in top-10 in 99% of users,
but training loss=6.65 implies the model is far from perfect. Something
is off in the eval.
"""
from __future__ import annotations

import csv
import math
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import torch

from run_sasrec_sbert import (
    load_split_csv, reindex, build_user_sequences,
    SASRecSBERT, SASRecDataset, collate_batch,
)
from torch.utils.data import DataLoader

ROOT = Path(__file__).resolve().parent.parent
SPLIT_DIR = ROOT / "data_5core" / "5core" / "last_out"
EMB_CACHE_DIR = ROOT / "cache_5core"

CATEGORY = "Video_Games"
MAX_SEQ_LEN = 50
N_EPOCHS = 1
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Load splits
train_rows = load_split_csv(SPLIT_DIR / f"{CATEGORY}.train.csv")
valid_rows = load_split_csv(SPLIT_DIR / f"{CATEGORY}.valid.csv")
test_rows = load_split_csv(SPLIT_DIR / f"{CATEGORY}.test.csv")
train_inters, valid_inters, test_inters, user_list, item_list = reindex(
    train_rows, valid_rows, test_rows)
n_users, n_items = len(user_list), len(item_list)
pad_id = n_items
print(f"n_users={n_users:,}  n_items={n_items:,}  pad_id={pad_id}")

# Build user training sequences
user_seqs = build_user_sequences(train_inters)
print(f"built sequences for {len(user_seqs):,} users")

# Test for leakage: are any test items in the corresponding user's training set?
test_dict = {u: i for u, i, _, _ in test_inters}
n_leak = 0
for u, tgt in test_dict.items():
    if u in user_seqs and tgt in user_seqs[u]:
        n_leak += 1
print(f"leakage check: {n_leak} users have test item in their training sequence (should be 0)")

# Load SBERT
sbert_emb = np.load(EMB_CACHE_DIR / f"sbert_titles_{CATEGORY}.npy").astype(np.float32)
print(f"sbert shape: {sbert_emb.shape}")

# Build model
model = SASRecSBERT(n_items=n_items, pad_id=pad_id, max_seq_len=MAX_SEQ_LEN,
                     d_model=64, n_layers=2, n_heads=2, dropout=0.2,
                     sbert_emb=sbert_emb).to(DEVICE)
n_params = sum(p.numel() for p in model.parameters())
print(f"n_params: {n_params:,}")

# Quick train: 1 epoch
dataset = SASRecDataset(user_seqs, MAX_SEQ_LEN, n_items, pad_id)
loader = DataLoader(dataset, batch_size=256, shuffle=True, num_workers=0,
                     collate_fn=collate_batch)
opt = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-5)
import torch.nn.functional as F
import time
print(f"\ntraining 1 epoch...")
model.train()
t0 = time.time()
losses = []
for inputs, targets in loader:
    inputs = inputs.to(DEVICE); targets = targets.to(DEVICE)
    logits = model(inputs)
    B, L, n_it = logits.shape
    loss = F.cross_entropy(logits.reshape(B*L, n_it), targets.reshape(B*L),
                             ignore_index=pad_id)
    opt.zero_grad(); loss.backward(); opt.step()
    losses.append(loss.item())
print(f"  epoch loss: {np.mean(losses):.4f}  in {time.time()-t0:.1f}s")

# Diagnostic eval on first 20 users with explicit prints
print(f"\n=== Diagnostic eval on first 20 users ===")
model.eval()
sample_users = sorted(test_dict.keys())[:20]
with torch.no_grad():
    for u in sample_users:
        # Build single-user input
        items = user_seqs.get(u, [])
        if not items: continue
        input_ids = torch.full((1, MAX_SEQ_LEN), pad_id, dtype=torch.long, device=DEVICE)
        truncated = items[-MAX_SEQ_LEN:]
        input_ids[0, -len(truncated):] = torch.tensor(truncated, dtype=torch.long, device=DEVICE)

        logits = model(input_ids)  # (1, L, n_items)
        final = logits[0, -1, :].clone()  # (n_items,)
        # Don't mask yet — check raw rank first
        tgt = test_dict[u]
        raw_tgt_score = final[tgt].item()
        raw_rank = int((final > raw_tgt_score).sum().item())

        # Now mask training items
        final[items] = -float('inf')
        masked_tgt_score = final[tgt].item()
        masked_rank = int((final > masked_tgt_score).sum().item())

        # Top-5 items by score (masked) for inspection
        topk = torch.topk(final, 5)
        top_ids = topk.indices.cpu().tolist()
        top_scores = topk.values.cpu().tolist()

        is_tgt_in_train = tgt in items
        print(f"u={u:>5d} hist_len={len(items):>3d} tgt={tgt:>6d} "
              f"raw_rank={raw_rank:>6d} masked_rank={masked_rank:>6d} "
              f"in_train={is_tgt_in_train}  top5=[{','.join(map(str,top_ids))}] (scores: {[f'{s:.2f}' for s in top_scores]})")
