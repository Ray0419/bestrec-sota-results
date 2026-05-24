"""CDR-CL: CDR with the CLCRec contrastive encoder as the LC2C signal.

This variant takes the production ``CDR_validated`` blend from
``run_poc_cdr_books.py`` and swaps the Ridge-based LC2C component for the
faithful CLCRec contrastive encoder.

Concretely, for each outer fold:
    Stage 1: EASE on warm items (unchanged warm-warm component).
    Stage 2: BPR on warm interactions -> (U_BPR, V_BPR).
    Stage 3: CLCRec encoder g_phi: SBERT -> R^k aligned with V_BPR.
    Stage 4: Per-user z-normalised blend
                cold_blend = alpha * cd_cold + (1 - alpha) * lc_cold
             where
                cd_cold[u, j] = _z(Xw[u] @ S_content[warm, j_cold])
                lc_cold[u, j] = _z(U_BPR[u] @ g_phi(SBERT[j_cold]))
             alpha is selected on an inner-fold item validation split.

Everything else mirrors ``run_poc_cdr_books.py``: same warm matrix
construction, same alpha grid, same eval_full protocol.
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
from scipy.sparse import csr_matrix
from scipy.stats import wilcoxon

from ease_efficient import ease_fast
from run_cold_item import DATASET_KCORE, HP, make_item_kfold
from run_faithful_clcrec import (
    BPR_EPOCHS,
    encode_all,
    train_bpr,
    train_clcrec_encoder,
)
from v5_utils import NUM_FOLDS, ROOT, TOP_K, content_sim_matrix, kcore_filter, reindex

CDR_ALPHA_GRID = [0.0, 0.1, 0.2, 0.25, 0.3, 0.4, 0.5, 0.75, 1.0]
SEED = 20260521

# Fixed CLCRec hyperparameters chosen from the faithful CLCRec inner-validation
# sweep on Beauty + Fashion (tau=0.5, lr=1e-3, h=256 is the modal winner).
# CDR-CL inherits them rather than re-sweeping per fold; the alpha-blend grid
# already absorbs the variance.
DEFAULT_CLC_TAU = 0.5
DEFAULT_CLC_LR = 1e-3
DEFAULT_CLC_HIDDEN = 256


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


def _z(x, eps=1e-8):
    m = x.mean(axis=1, keepdims=True)
    s = np.maximum(x.std(axis=1, keepdims=True), eps)
    return (x - m) / s


def make_score_cdr_cl(
    Xw, B_warm, U_bpr, z_cold,
    warm_indices, cold_indices, S_content, n_items, alpha,
):
    """CDR-CL scoring: warm = EASE; cold = alpha * content_direct + (1-alpha) * CLCRec.

    U_bpr: (n_users, d) user CF embeddings from BPR.
    z_cold: (n_cold, d) encoder-predicted CF embeddings for cold items.
    """
    S_w_c = S_content[np.ix_(warm_indices, cold_indices)].astype(np.float32)

    def f(uids):
        warm_scores = Xw[uids] @ B_warm
        cd_cold = _z(Xw[uids] @ S_w_c)
        lc_cold = _z(U_bpr[uids] @ z_cold.T)
        cold_blend = alpha * cd_cold + (1.0 - alpha) * lc_cold
        out = np.empty((len(uids), n_items), dtype=np.float32)
        out[:, warm_indices] = warm_scores
        out[:, cold_indices] = cold_blend
        return out

    return f


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


def select_alpha(
    dataset, outer_train, outer_cold_items, S_content, sbert_all,
    n_users, n_items, rng, seed, fold_id, bpr_epochs,
):
    outer_warm = sorted(set(range(n_items)) - set(outer_cold_items))
    shuf = np.array(outer_warm, dtype=np.int32)
    rng.shuffle(shuf)
    n_val = max(1, int(0.2 * len(shuf)))
    val_items = set(shuf[:n_val].tolist())
    val_inters = [x for x in outer_train if int(x["item_id"]) in val_items]
    if not val_inters:
        return 0.25, {}
    inner_cold = sorted(set(outer_cold_items) | val_items)
    inner_warm = np.array(sorted(set(range(n_items)) - set(inner_cold)), dtype=np.int32)
    inner_train = [x for x in outer_train if int(x["item_id"]) not in val_items]
    X_in, Xw_in = build_warm(inner_train, n_users, inner_warm)
    S_w_in = S_content[np.ix_(inner_warm, inner_warm)]
    lam, beta = HP[dataset]
    B_in = ease_fast(X_in, lam=lam, beta=beta, S_content=S_w_in, dtype=np.float32)
    # CLCRec encoder on the inner fold (uses BPR on inner-warm interactions).
    U_in, V_in, _ = train_bpr(
        inner_train, inner_warm, n_users, seed,
        n_epochs=max(40, bpr_epochs // 2),
    )
    model, _ = train_clcrec_encoder(
        sbert_all[inner_warm], V_in, seed,
        tau=DEFAULT_CLC_TAU, lr=DEFAULT_CLC_LR, hidden=DEFAULT_CLC_HIDDEN,
        epochs=max(20, 30),
    )
    cold_arr = np.array(sorted(inner_cold), dtype=np.int32)
    z_cold = encode_all(model, sbert_all[cold_arr])
    scores = {}
    for a in CDR_ALPHA_GRID:
        sf = make_score_cdr_cl(
            Xw_in, B_in, U_in, z_cold,
            inner_warm, cold_arr, S_content, n_items, alpha=a,
        )
        summary, _, _ = eval_full(sf, inner_train, val_inters, n_items)
        scores[float(a)] = summary["NDCG@10"]
    del X_in, Xw_in, B_in, model
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    return max(scores, key=scores.get), scores


def append_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, sort_keys=True) + "\n")


def run(dataset, seeds, jsonl_path):
    print(f"\n{'#'*70}\n# CDR-CL: {dataset.upper()}\n{'#'*70}")
    interactions, n_users, n_items, item_title_emb = load_dataset(dataset)
    sbert_all = item_title_emb.cpu().numpy().astype(np.float32) if hasattr(item_title_emb, "cpu") else np.asarray(item_title_emb, dtype=np.float32)
    S_content = content_sim_matrix(item_title_emb, dtype=np.float32)
    lam, beta = HP[dataset]
    k = DATASET_KCORE[dataset]
    bpr_epochs = BPR_EPOCHS.get(dataset, 200)
    print(f"  n_users={n_users:,}  n_items={n_items:,}  k={k}  lambda={lam}  beta={beta}  BPR_epochs={bpr_epochs}")
    perfold = []
    per_user_all = defaultdict(list)
    selected_alphas = []
    if jsonl_path.exists():
        jsonl_path.unlink()

    for seed in seeds:
        splits = make_item_kfold(interactions, n_items, n_splits=NUM_FOLDS, seed=seed)
        for fold_id, (tr, te, cold) in enumerate(splits):
            t_fold = time.time()
            train_inters = [interactions[i] for i in tr]
            test_inters = [interactions[i] for i in te]
            warm_idx = np.array(sorted(set(range(n_items)) - set(cold)), dtype=np.int32)
            cold_idx = np.array(sorted(cold), dtype=np.int32)
            X_sparse, Xw = build_warm(train_inters, n_users, warm_idx)
            S_warm = S_content[np.ix_(warm_idx, warm_idx)]
            B_warm = ease_fast(X_sparse, lam=lam, beta=beta, S_content=S_warm, dtype=np.float32)

            # Inner-validation alpha selection (also trains an inner BPR + encoder)
            val_rng = np.random.RandomState((seed * 1000 + fold_id + 7) & 0xFFFFFFFF)
            a, val_scores = select_alpha(
                dataset, train_inters, set(cold), S_content, sbert_all,
                n_users, n_items, val_rng, seed, fold_id, bpr_epochs,
            )
            selected_alphas.append({
                "seed": seed, "fold_id": fold_id, "alpha": a,
                "val_scores": val_scores,
            })

            # Outer BPR + CLCRec encoder (fresh, on outer-warm)
            U_out, V_warm, bpr_loss = train_bpr(
                train_inters, warm_idx, n_users, seed,
                n_epochs=bpr_epochs,
            )
            model, _ = train_clcrec_encoder(
                sbert_all[warm_idx], V_warm, seed,
                tau=DEFAULT_CLC_TAU, lr=DEFAULT_CLC_LR, hidden=DEFAULT_CLC_HIDDEN,
            )
            z_cold = encode_all(model, sbert_all[cold_idx])
            sf = make_score_cdr_cl(
                Xw, B_warm, U_out, z_cold,
                warm_idx, cold_idx, S_content, n_items, alpha=a,
            )
            summary, pu, rows = eval_full(sf, train_inters, test_inters, n_items)
            for r in rows:
                r.update({
                    "dataset": dataset, "seed": seed, "fold_id": fold_id,
                    "method": "cdr_cl", "alpha": float(a),
                    "candidate_scope": "full_catalog",
                })
            append_jsonl(jsonl_path, rows)
            perfold.append(summary["NDCG@10"])
            for u, vs in pu.items():
                per_user_all[u].append(vs)
            dt = time.time() - t_fold
            print(f"  seed={seed} fold={fold_id} alpha={a:.2f}  NDCG@10={summary['NDCG@10']:.4f}  "
                  f"HR@10={summary['HR@10']:.4f}  BPR_loss={bpr_loss:.4f}  [{dt:.1f}s]")
            del X_sparse, Xw, B_warm, S_warm, U_out, V_warm, model
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    return {
        "perfold_ndcg10": list(map(float, perfold)),
        "mean_ndcg10": float(np.mean(perfold)) if perfold else 0.0,
        "std_ndcg10": float(np.std(perfold)) if perfold else 0.0,
        "per_user_ndcg10": {int(u): float(np.mean(vs)) for u, vs in per_user_all.items()},
        "selected_alphas": selected_alphas,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("datasets", nargs="*", default=["beauty"])
    ap.add_argument("--seeds", default=str(SEED))
    ap.add_argument("--out", default="results_cdr_cl.json")
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
            "method": "cdr_cl",
            "status": "algorithm",
            "datasets": {},
        }
    payload["seeds"] = seeds
    for ds in args.datasets:
        jsonl_path = Path(__file__).parent / f"results_cdr_cl_records_{ds}.jsonl"
        payload["datasets"][ds] = run(ds, seeds, jsonl_path)
        with open(out, "w") as f:
            json.dump(payload, f, indent=2)
        print(f"\n=== {ds.upper()} ===\nperfold: {payload['datasets'][ds]['perfold_ndcg10']}\n"
              f"mean+/-std: {payload['datasets'][ds]['mean_ndcg10']:.4f} +/- {payload['datasets'][ds]['std_ndcg10']:.4f}")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
