"""Faithful CLCRec baseline (Wei et al., MM 2021).

The simplified proxy in ``run_all_confirmatory.make_contrastive_cold_full``
uses SVD reference factors and a hybrid MSE+CE loss. This module implements
the more faithful three-stage protocol:

  Stage 1: BPR-trained user/item CF embeddings on warm interactions only.
           Adam, latent_dim=64, lr=1e-3, batch=1024, 200 epochs.
  Stage 2: Content encoder g_phi: SBERT(384) -> hidden -> 64 (MLP, ReLU, dropout).
  Stage 3: InfoNCE training of g_phi to align g_phi(SBERT_j) with V_j_BPR.
           Loss = -log( exp(<g_phi(SBERT_j), V_j>/tau) / sum_k exp(<g_phi(SBERT_j), V_k>/tau) )
           with in-batch negatives + random extra negatives.

Inference: score(u, j_cold) = U_u_BPR . g_phi(SBERT_j_cold).
           For warm: score = U_u_BPR . V_j_BPR (so we get a proper warm CF score
           too, used only when filling the score matrix at warm positions).

Hyperparameter sweep on an inner item-held-out 20% validation set per outer
fold: tau in {0.07, 0.1, 0.2, 0.5}, lr in {1e-3, 5e-4}, hidden in {128, 256}.
The grid is intentionally compact to stay within budget.

Full-catalog cold evaluation reuses the protocol from
``run_poc_cdr_books.py::eval_full``. Per-pair JSONL records are written so the
artifact matches the schema of the SOTA confirmatory run.
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
import torch.nn.functional as F
from scipy.sparse import csr_matrix
from scipy.stats import wilcoxon

from run_cold_item import DATASET_KCORE, make_item_kfold
from v5_utils import NUM_FOLDS, ROOT, TOP_K, kcore_filter, reindex


DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Compact HP grid kept under budget. tau is the contrastive temperature, lr is
# Adam learning rate for the content encoder, hidden is the MLP hidden width.
TAU_GRID = [0.07, 0.1, 0.2, 0.5]
LR_GRID = [1e-3, 5e-4]
HIDDEN_GRID = [128, 256]

# CF / BPR config
BPR_DIM = 64
BPR_LR = 1e-3
BPR_BATCH = 1024
BPR_EPOCHS = {"beauty": 200, "fashion": 200, "instruments": 80, "books": 40}
BPR_WD = 1e-5

# CLCRec encoder config
CLC_EPOCHS = 60
CLC_BATCH = 256
CLC_DROPOUT = 0.2
CLC_EXTRA_NEG = 256   # uniformly sampled additional negatives per batch
# Scoring: dot product can suffer from warm/cold magnitude mismatch in
# full-catalog eval. We follow the standard contrastive-recsys practice of
# L2-normalising the target CF vectors before the InfoNCE loss and using
# cosine similarity for inference. This keeps the algorithm faithful to
# CLCRec (which normalises in its loss) while giving a fair full-catalog
# ranking signal.
NORMALIZE = True

SEED = 20260521


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
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
        if p is None:
            continue
        rows.append(int(x["user_id"]))
        cols.append(p)
    X_sparse = csr_matrix(
        (np.ones(len(rows), dtype=np.float32), (rows, cols)),
        shape=(n_users, len(warm_indices)),
    )
    return X_sparse, X_sparse.toarray().astype(np.float32)


# ---------------------------------------------------------------------------
# Stage 1: BPR matrix factorisation on warm interactions
# ---------------------------------------------------------------------------
def train_bpr(
    train_inters,
    warm_indices,
    n_users,
    seed,
    *,
    dim=BPR_DIM,
    lr=BPR_LR,
    batch_size=BPR_BATCH,
    n_epochs=200,
    weight_decay=BPR_WD,
    verbose=False,
):
    """Train BPR-MF on warm interactions and return (U_warm, V_warm)
    as numpy arrays. V_warm is indexed by warm position (not global id).
    """
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

    warm_pos = {int(it): i for i, it in enumerate(warm_indices)}
    pairs = []
    user_pos_sets = defaultdict(set)
    for inter in train_inters:
        wp = warm_pos.get(int(inter["item_id"]))
        if wp is None:
            continue
        u = int(inter["user_id"])
        pairs.append((u, wp))
        user_pos_sets[u].add(wp)
    if not pairs:
        return (
            np.zeros((n_users, dim), dtype=np.float32),
            np.zeros((len(warm_indices), dim), dtype=np.float32),
        )

    n_warm = len(warm_indices)
    pairs_arr = np.array(pairs, dtype=np.int64)
    n_pairs = len(pairs_arr)
    rng = np.random.RandomState(seed)

    U = torch.empty((n_users, dim), device=DEVICE).normal_(0.0, 0.01)
    V = torch.empty((n_warm, dim), device=DEVICE).normal_(0.0, 0.01)
    U.requires_grad_(True)
    V.requires_grad_(True)
    opt = torch.optim.Adam([U, V], lr=lr, weight_decay=weight_decay)

    user_pos_lists = {u: np.fromiter(s, dtype=np.int64) for u, s in user_pos_sets.items()}

    last_loss = None
    for ep in range(n_epochs):
        perm = rng.permutation(n_pairs)
        total_loss = 0.0
        n_batches = 0
        for start in range(0, n_pairs, batch_size):
            idx = perm[start:start + batch_size]
            users = pairs_arr[idx, 0]
            pos_items = pairs_arr[idx, 1]
            # Sample one negative per pair uniformly from items not in the user history.
            neg_items = rng.randint(0, n_warm, size=len(users))
            # Quick correction pass
            for j in range(len(users)):
                u = int(users[j])
                tries = 0
                lst = user_pos_lists.get(u)
                while lst is not None and neg_items[j] in lst and tries < 5:
                    neg_items[j] = rng.randint(0, n_warm)
                    tries += 1
            u_t = torch.from_numpy(users).to(DEVICE)
            p_t = torch.from_numpy(pos_items).to(DEVICE)
            n_t = torch.from_numpy(neg_items).to(DEVICE)
            u_emb = U[u_t]
            p_emb = V[p_t]
            n_emb = V[n_t]
            pos_score = (u_emb * p_emb).sum(dim=1)
            neg_score = (u_emb * n_emb).sum(dim=1)
            loss = -F.logsigmoid(pos_score - neg_score).mean()
            opt.zero_grad()
            loss.backward()
            opt.step()
            total_loss += float(loss.item())
            n_batches += 1
        last_loss = total_loss / max(1, n_batches)
        if verbose and (ep < 3 or (ep + 1) % 50 == 0):
            print(f"      BPR epoch {ep + 1}/{n_epochs} loss={last_loss:.4f}")
    return U.detach().cpu().numpy().astype(np.float32), V.detach().cpu().numpy().astype(np.float32), last_loss


# ---------------------------------------------------------------------------
# Stage 2/3: content encoder + InfoNCE training
# ---------------------------------------------------------------------------
class ContentEncoder(torch.nn.Module):
    def __init__(self, in_dim, hidden, out_dim, dropout=CLC_DROPOUT):
        super().__init__()
        self.net = torch.nn.Sequential(
            torch.nn.Linear(in_dim, hidden),
            torch.nn.ReLU(),
            torch.nn.Dropout(dropout),
            torch.nn.Linear(hidden, out_dim),
        )

    def forward(self, x):
        return self.net(x)


def train_clcrec_encoder(
    sbert_warm,
    V_warm,
    seed,
    *,
    tau,
    lr,
    hidden,
    epochs=CLC_EPOCHS,
    batch_size=CLC_BATCH,
    extra_neg=CLC_EXTRA_NEG,
):
    """Train g_phi to match V_warm via InfoNCE.

    Positive: (sbert_j, V_j). Negatives: other items in the same batch plus
    ``extra_neg`` random items from the warm pool (to keep the negative bank
    well-populated even for small datasets).
    """
    torch.manual_seed(seed + 23)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed + 23)

    n_warm = sbert_warm.shape[0]
    in_dim = sbert_warm.shape[1]
    out_dim = V_warm.shape[1]
    model = ContentEncoder(in_dim, hidden, out_dim).to(DEVICE)
    opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-5)
    sbert_t = torch.from_numpy(sbert_warm).to(DEVICE)
    V_raw = torch.from_numpy(V_warm).to(DEVICE)
    V_t = F.normalize(V_raw, dim=1) if NORMALIZE else V_raw

    rng = np.random.RandomState(seed + 23)
    for ep in range(epochs):
        perm = rng.permutation(n_warm)
        for start in range(0, n_warm, batch_size):
            idx = perm[start:start + batch_size]
            if len(idx) < 2:
                continue
            idx_t = torch.from_numpy(idx).long().to(DEVICE)
            z = model(sbert_t[idx_t])
            if NORMALIZE:
                z = F.normalize(z, dim=1)
            v_pos = V_t[idx_t]
            # In-batch negatives are everything in the batch except the diagonal.
            # Extra random negatives are drawn from the full warm pool.
            if extra_neg > 0 and n_warm > 0:
                neg_idx = rng.randint(0, n_warm, size=min(extra_neg, n_warm))
                neg_idx_t = torch.from_numpy(neg_idx).long().to(DEVICE)
                v_neg = V_t[neg_idx_t]
                v_bank = torch.cat([v_pos, v_neg], dim=0)
            else:
                v_bank = v_pos
            # Logits = (B, D) @ (D, K) / tau
            logits = z @ v_bank.T / tau
            labels = torch.arange(len(idx), device=DEVICE)
            loss = F.cross_entropy(logits, labels)
            opt.zero_grad()
            loss.backward()
            opt.step()
    model.eval()
    with torch.no_grad():
        z_warm = model(sbert_t)
        if NORMALIZE:
            z_warm = F.normalize(z_warm, dim=1)
        z_warm = z_warm.cpu().numpy().astype(np.float32)
    return model, z_warm


def encode_all(model, sbert_all):
    model.eval()
    with torch.no_grad():
        z = model(torch.from_numpy(sbert_all).to(DEVICE))
        if NORMALIZE:
            z = F.normalize(z, dim=1)
        z = z.cpu().numpy().astype(np.float32)
    return z


# ---------------------------------------------------------------------------
# Inference: full-catalog score function
# ---------------------------------------------------------------------------
def make_score_clcrec(U_full, V_full_items, n_items):
    """U_full: (n_users, d). V_full_items: (n_items, d). Returns scoring fn."""
    def f(uids):
        u = U_full[uids]
        return (u @ V_full_items.T).astype(np.float32)
    return f


# ---------------------------------------------------------------------------
# Eval (full catalog)
# ---------------------------------------------------------------------------
def eval_full(score_fn, train_inters, test_inters, n_items, batch_size=192):
    ut = defaultdict(set)
    uts = defaultdict(list)
    for x in train_inters:
        ut[int(x["user_id"])].add(int(x["item_id"]))
    for x in test_inters:
        uts[int(x["user_id"])].append(int(x["item_id"]))
    users = sorted(u for u in uts if uts[u] and ut[u])
    ndcg = []
    hr = []
    rr = []
    per_user_ndcg = defaultdict(list)
    per_pair_rows = []
    for s in range(0, len(users), batch_size):
        batch = users[s:s + batch_size]
        scores = score_fn(np.array(batch, dtype=np.int32)).astype(np.float32, copy=True)
        for k, u in enumerate(batch):
            if ut[u]:
                scores[k, list(ut[u])] = -np.inf
            for tgt in uts[u]:
                ts = scores[k, tgt]
                r0 = int((scores[k] > ts).sum())
                h = 1.0 if r0 < TOP_K else 0.0
                n_ = 1.0 / math.log2(r0 + 2) if r0 < TOP_K else 0.0
                r_ = 1.0 / (r0 + 1)
                ndcg.append(n_)
                hr.append(h)
                rr.append(r_)
                per_user_ndcg[int(u)].append(n_)
                per_pair_rows.append(
                    {
                        "user_id": int(u),
                        "target_item_id": int(tgt),
                        "ndcg10": float(n_),
                        "hr10": float(h),
                        "rr": float(r_),
                    }
                )
    summary = {
        "NDCG@10": float(np.mean(ndcg)) if ndcg else 0.0,
        "HR@10": float(np.mean(hr)) if hr else 0.0,
        "MRR": float(np.mean(rr)) if rr else 0.0,
        "n_eval": len(per_pair_rows),
    }
    per_user = {u: float(np.mean(vs)) for u, vs in per_user_ndcg.items()}
    return summary, per_user, per_pair_rows


# ---------------------------------------------------------------------------
# Inner-validation hyperparameter sweep
# ---------------------------------------------------------------------------
def select_hp(
    dataset,
    outer_train,
    outer_cold_items,
    sbert_all,
    n_users,
    n_items,
    seed,
    fold_id,
    *,
    bpr_epochs,
):
    """Hold out 20% of outer-warm items as inner cold for HP selection."""
    outer_warm = sorted(set(range(n_items)) - set(outer_cold_items))
    rng = np.random.RandomState((seed * 1000 + fold_id + 41) & 0xFFFFFFFF)
    shuf = np.array(outer_warm, dtype=np.int32)
    rng.shuffle(shuf)
    n_val = max(1, int(0.2 * len(shuf)))
    val_items = set(shuf[:n_val].tolist())
    val_inters = [x for x in outer_train if int(x["item_id"]) in val_items]
    if not val_inters:
        return {"tau": 0.1, "lr": 1e-3, "hidden": 128, "val_scores": {}}
    inner_cold = sorted(set(outer_cold_items) | val_items)
    inner_warm = np.array(sorted(set(range(n_items)) - set(inner_cold)), dtype=np.int32)
    inner_train = [x for x in outer_train if int(x["item_id"]) not in val_items]
    # Train BPR once on the inner-warm subset (re-used across HP combos).
    U_in, V_in, _ = train_bpr(
        inner_train, inner_warm, n_users, seed,
        n_epochs=max(40, bpr_epochs // 2),
    )
    sbert_warm = sbert_all[inner_warm]
    cold_arr = np.array(sorted(inner_cold), dtype=np.int32)
    val_scores = {}
    best_key, best_score = None, -1.0
    for tau in TAU_GRID:
        for lr in LR_GRID:
            for hidden in HIDDEN_GRID:
                model, _ = train_clcrec_encoder(
                    sbert_warm, V_in, seed,
                    tau=tau, lr=lr, hidden=hidden,
                    epochs=max(20, CLC_EPOCHS // 2),
                )
                # Build a full V matrix for inner fold: V_warm = BPR, V_cold = encoder
                V_full = np.zeros((n_items, V_in.shape[1]), dtype=np.float32)
                if NORMALIZE:
                    V_in_norm = V_in / np.maximum(np.linalg.norm(V_in, axis=1, keepdims=True), 1e-12)
                    V_full[inner_warm] = V_in_norm
                else:
                    V_full[inner_warm] = V_in
                z_cold = encode_all(model, sbert_all[cold_arr])
                V_full[cold_arr] = z_cold
                score_fn = make_score_clcrec(U_in, V_full, n_items)
                summary, _, _ = eval_full(score_fn, inner_train, val_inters, n_items)
                key = f"tau={tau:.2f}_lr={lr:.0e}_h={hidden}"
                val_scores[key] = summary["NDCG@10"]
                if summary["NDCG@10"] > best_score:
                    best_score = summary["NDCG@10"]
                    best_key = (tau, lr, hidden)
                del model, V_full
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
    tau, lr, hidden = best_key
    return {
        "tau": float(tau),
        "lr": float(lr),
        "hidden": int(hidden),
        "best_val_ndcg10": float(best_score),
        "val_scores": val_scores,
    }


# ---------------------------------------------------------------------------
# Per-fold driver
# ---------------------------------------------------------------------------
def append_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, sort_keys=True) + "\n")


def run(dataset, seeds, jsonl_path, sweep_hp=True):
    print(f"\n{'#'*70}\n# Faithful CLCRec: {dataset.upper()}\n{'#'*70}")
    interactions, n_users, n_items, emb_t = load_dataset(dataset)
    sbert_all = emb_t.cpu().numpy().astype(np.float32) if hasattr(emb_t, "cpu") else np.asarray(emb_t, dtype=np.float32)
    k = DATASET_KCORE[dataset]
    bpr_epochs = BPR_EPOCHS.get(dataset, 200)
    print(f"  n_users={n_users:,}  n_items={n_items:,}  k={k}  BPR_epochs={bpr_epochs}")

    perfold = []
    per_user_all = defaultdict(list)
    selected_hps = []
    bpr_losses = []
    if jsonl_path.exists():
        jsonl_path.unlink()

    for seed in seeds:
        splits = make_item_kfold(interactions, n_items, n_splits=NUM_FOLDS, seed=seed)
        for fold_id, (tr, te, cold) in enumerate(splits):
            t0 = time.time()
            train_inters = [interactions[i] for i in tr]
            test_inters = [interactions[i] for i in te]
            warm_idx = np.array(sorted(set(range(n_items)) - set(cold)), dtype=np.int32)
            cold_idx = np.array(sorted(cold), dtype=np.int32)

            # HP selection
            if sweep_hp:
                t_sel = time.time()
                hp = select_hp(
                    dataset, train_inters, set(cold), sbert_all,
                    n_users, n_items, seed, fold_id, bpr_epochs=bpr_epochs,
                )
                hp["seed"] = seed
                hp["fold_id"] = fold_id
                hp["sel_seconds"] = time.time() - t_sel
                selected_hps.append(hp)
                tau, lr, hidden = hp["tau"], hp["lr"], hp["hidden"]
                print(f"    HP sel: tau={tau} lr={lr} h={hidden}  [{hp['sel_seconds']:.1f}s]")
            else:
                # Defaults derived from the inner-validation sweep on Beauty
                # and Fashion: tau=0.5 wins consistently. lr=1e-3, h=256 is the
                # modal pick. These are reused without re-sweeping on larger
                # datasets to stay within budget.
                tau, lr, hidden = 0.5, 1e-3, 256
                selected_hps.append({
                    "seed": seed, "fold_id": fold_id,
                    "tau": tau, "lr": lr, "hidden": hidden,
                    "note": "no_sweep_uses_modal_winner_from_beauty_fashion",
                })

            # Outer BPR + encoder
            U_out, V_warm, bpr_loss = train_bpr(
                train_inters, warm_idx, n_users, seed,
                n_epochs=bpr_epochs,
            )
            bpr_losses.append({"seed": seed, "fold_id": fold_id, "loss": bpr_loss})
            model, _ = train_clcrec_encoder(
                sbert_all[warm_idx], V_warm, seed,
                tau=tau, lr=lr, hidden=hidden,
            )
            V_full = np.zeros((n_items, V_warm.shape[1]), dtype=np.float32)
            if NORMALIZE:
                V_warm_norm = V_warm / np.maximum(np.linalg.norm(V_warm, axis=1, keepdims=True), 1e-12)
                V_full[warm_idx] = V_warm_norm
            else:
                V_full[warm_idx] = V_warm
            V_full[cold_idx] = encode_all(model, sbert_all[cold_idx])
            score_fn = make_score_clcrec(U_out, V_full, n_items)

            summary, pu, rows = eval_full(score_fn, train_inters, test_inters, n_items)
            for r in rows:
                r.update({
                    "dataset": dataset, "seed": seed, "fold_id": fold_id,
                    "method": "faithful_clcrec",
                    "candidate_scope": "full_catalog",
                })
            append_jsonl(jsonl_path, rows)
            perfold.append(summary["NDCG@10"])
            for u, vs in pu.items():
                per_user_all[u].append(vs)
            dt = time.time() - t0
            print(f"  seed={seed} fold={fold_id}  NDCG@10={summary['NDCG@10']:.4f}  "
                  f"HR@10={summary['HR@10']:.4f}  n={summary['n_eval']:,}  "
                  f"BPR_loss={bpr_loss:.4f}  [{dt:.1f}s]")
            del U_out, V_warm, V_full, model
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    return {
        "perfold_ndcg10": list(map(float, perfold)),
        "mean_ndcg10": float(np.mean(perfold)) if perfold else 0.0,
        "std_ndcg10": float(np.std(perfold)) if perfold else 0.0,
        "per_user_ndcg10": {int(u): float(np.mean(vs)) for u, vs in per_user_all.items()},
        "selected_hps": selected_hps,
        "bpr_losses": bpr_losses,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("datasets", nargs="*", default=["beauty"])
    ap.add_argument("--seeds", default=str(SEED))
    ap.add_argument("--out", default="results_faithful_clcrec.json")
    ap.add_argument("--no-sweep", action="store_true", help="Use default HPs without inner validation sweep")
    args = ap.parse_args()
    seeds = [int(s) for s in args.seeds.split(",")]
    out = Path(__file__).parent / args.out
    if out.exists():
        try:
            payload = json.load(open(out))
        except Exception:
            payload = {"datasets": {}}
    else:
        payload = {
            "schema_version": 1,
            "candidate_scope": "full_catalog",
            "method": "faithful_clcrec",
            "status": "baseline",
            "datasets": {},
        }
    payload["seeds"] = seeds
    payload["sweep_hp"] = not args.no_sweep
    for ds in args.datasets:
        jsonl_path = Path(__file__).parent / f"results_faithful_clcrec_records_{ds}.jsonl"
        payload["datasets"][ds] = run(ds, seeds, jsonl_path, sweep_hp=not args.no_sweep)
        with open(out, "w") as f:
            json.dump(payload, f, indent=2)
        print(f"\n=== {ds.upper()} ===\nperfold: {payload['datasets'][ds]['perfold_ndcg10']}\n"
              f"mean+/-std: {payload['datasets'][ds]['mean_ndcg10']:.4f} +/- {payload['datasets'][ds]['std_ndcg10']:.4f}\n"
              f"records: {jsonl_path}")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
