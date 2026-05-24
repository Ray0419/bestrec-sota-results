"""Faithful BLaIR baseline (Hou et al., 2024) using the OFFICIAL pre-trained
checkpoint ``hyp1231/blair-roberta-base`` from HuggingFace.

This replaces the simplified ``blair_text`` proxy in
``run_all_confirmatory.make_blair_text_full`` which uses cached SBERT
(all-MiniLM-L6-v2) title embeddings. The proxy is honest about its fidelity
("frozen_sbert_dual_encoder_profile_not_official_blair_checkpoint"); this
script provides the strict-confirmatory-grade same-split comparator.

Algorithm (single-tower BLaIR retrieval):

  Step 1: Encode each item title with BLaIR. Following the official model
          card, use last_hidden_state[:, 0] (CLS pooling) and L2-normalise.
          The official BLaIR was trained contrastively on (item metadata,
          user-review) pairs from Amazon Reviews 2023, so the item-tower
          encoding alone carries CF-aware semantics. Cache to
          cache/<dataset>/v5/item_title_blair_k{K}_dedup.pt.
  Step 2: For each user u in the training set, compute their profile as the
          L2-normalised mean of BLaIR embeddings over u's training items
          (single-tower retrieval; same fashion as BLaIR's retrieval setup
          for cold-start when no user-review history is available -- title
          only, the simplest faithful instantiation).
  Step 3: score(u, j) = cosine(profile_u, BLaIR_j) for every item j (warm
          and cold). For users with no training items the profile is zero
          and produces uniform zero scores.

Honest deviations from the paper:

  * BLaIR is bi-encoder (language-context tower + item-metadata tower)
    trained on (item metadata, user review) pairs. The paper's strongest
    recommendation results use additional user/review context as input to
    the language tower. We use a single-tower setup here because the
    confirmatory baseline_audit slot only requires a "same-split full-catalog
    retrieval comparator using the official BLaIR encoder" -- not a full
    fine-tune. Both towers in BLaIR share weights at inference, so encoding
    the item title with the same checkpoint and pooling identically is
    faithful to the released model.
  * We use item TITLE only. BLaIR's pretraining used title + features +
    description; our cached item_metadata only consistently has ``title``
    across the four datasets, so we limit to that. This matches what the
    simplified proxy used so the comparison is apples-to-apples on input
    text.
  * No item-side aggregation over review text. The official BLaIR
    HuggingFace model treats encoding as stateless text-to-vector, which
    is exactly what we use.

Eval protocol: full-catalog cold-item, same as
``run_poc_cdr_books.py::eval_full``. Multi-seed.

Run:

  _bestrec_run/.venv/Scripts/python _bestrec_run/run_faithful_blair.py \
      beauty fashion instruments books \
      --seeds 20260521,20260522,20260523
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
import traceback
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import torch
from scipy.sparse import csr_matrix
from scipy.stats import wilcoxon

from run_cold_item import DATASET_KCORE, make_item_kfold
from v5_utils import NUM_FOLDS, ROOT, TOP_K, kcore_filter, reindex


DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Primary checkpoint: official BLaIR base. Fallback: stronger general-purpose
# encoder if download fails for some reason. Both are exposed in the result
# payload so the audit cannot be ambiguous.
BLAIR_CHECKPOINT = "hyp1231/blair-roberta-base"
FALLBACK_CHECKPOINT = "sentence-transformers/all-mpnet-base-v2"
MAX_TEXT_LEN = 512
ENCODE_BATCH = 32

SEED = 20260521


# ---------------------------------------------------------------------------
# Dataset loader (item TITLE list + interaction list, NOT cached SBERT)
# ---------------------------------------------------------------------------
def load_dataset(dataset):
    cache_dir = Path(ROOT) / "cache" / dataset
    data = pickle.load(open(cache_dir / "raw_data_dedup.pkl", "rb"))
    filtered = kcore_filter(data["interactions"], DATASET_KCORE[dataset])
    interactions, meta, n_users, n_items, _ = reindex(filtered, data["item_metadata"])
    titles = []
    for i in range(n_items):
        m = meta.get(i, {})
        t = m.get("title", "") or ""
        titles.append(t if t else "unknown")
    return interactions, titles, n_users, n_items


# ---------------------------------------------------------------------------
# BLaIR encoder
# ---------------------------------------------------------------------------
def _maybe_load_checkpoint(checkpoint_id):
    """Try loading a HF model + tokenizer. Returns (tokenizer, model, info)
    or (None, None, error_string).
    """
    try:
        from transformers import AutoModel, AutoTokenizer
        tok = AutoTokenizer.from_pretrained(checkpoint_id)
        model = AutoModel.from_pretrained(checkpoint_id)
        return tok, model.eval().to(DEVICE), {
            "checkpoint": checkpoint_id,
            "hidden_size": int(model.config.hidden_size),
            "status": "loaded",
        }
    except Exception as exc:
        return None, None, {
            "checkpoint": checkpoint_id,
            "status": "failed",
            "error": "".join(traceback.format_exception_only(type(exc), exc)).strip(),
        }


def load_encoder():
    """Load BLaIR if possible, otherwise fall back to mpnet-base-v2.
    Returns (encoder_fn, model_card) where encoder_fn: list[str] -> np.ndarray.
    """
    tok, model, info = _maybe_load_checkpoint(BLAIR_CHECKPOINT)
    used = info["checkpoint"]
    faithful = True
    if tok is None:
        print(f"  ! BLaIR load failed: {info.get('error')}")
        print(f"  ! Falling back to {FALLBACK_CHECKPOINT}")
        tok, model, info = _maybe_load_checkpoint(FALLBACK_CHECKPOINT)
        used = info["checkpoint"]
        faithful = False
        if tok is None:
            raise RuntimeError(f"both BLaIR and fallback failed: {info}")

    def encode(texts):
        """CLS-pool + L2-normalise, as per the official BLaIR model card."""
        out_chunks = []
        for s in range(0, len(texts), ENCODE_BATCH):
            chunk = [t if t else "unknown" for t in texts[s:s + ENCODE_BATCH]]
            enc = tok(chunk, padding=True, truncation=True,
                      max_length=MAX_TEXT_LEN, return_tensors="pt")
            enc = {k: v.to(DEVICE) for k, v in enc.items()}
            with torch.no_grad():
                hs = model(**enc, return_dict=True).last_hidden_state
            v = hs[:, 0]
            v = torch.nn.functional.normalize(v, dim=1)
            out_chunks.append(v.cpu().numpy().astype(np.float32))
        return np.concatenate(out_chunks, axis=0)

    return encode, {
        "checkpoint": used,
        "hidden_size": info.get("hidden_size"),
        "pooling": "cls_then_l2_normalize",
        "max_length": MAX_TEXT_LEN,
        "is_official_blair": faithful,
        "fidelity": ("official_blair_roberta_base_checkpoint_title_only_single_tower"
                     if faithful else
                     "fallback_mpnet_base_v2_blair_failed"),
        "fallback_used": not faithful,
    }


def get_or_build_blair_embeddings(dataset, encoder, titles, force=False):
    """Compute or load cached BLaIR item embeddings."""
    cache_path = (Path(ROOT) / "cache" / dataset / "v5"
                  / f"item_title_blair_k{DATASET_KCORE[dataset]}_dedup.pt")
    if cache_path.exists() and not force:
        try:
            cached = torch.load(cache_path, weights_only=True)
            if cached.shape[0] == len(titles):
                return cached.cpu().numpy().astype(np.float32), str(cache_path), "cached"
        except Exception:
            pass
    print(f"  encoding {len(titles)} titles with BLaIR ({dataset})...")
    t0 = time.time()
    emb = encoder(titles)
    print(f"    done in {time.time() - t0:.1f}s, shape {emb.shape}")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(torch.from_numpy(emb), cache_path)
    return emb, str(cache_path), "freshly_encoded"


# ---------------------------------------------------------------------------
# Retrieval scorer (full catalog)
# ---------------------------------------------------------------------------
def build_warm_sparse(train_inters, n_users, warm_indices):
    pos = {int(it): i for i, it in enumerate(warm_indices)}
    rows, cols = [], []
    for x in train_inters:
        p = pos.get(int(x["item_id"]))
        if p is None:
            continue
        rows.append(int(x["user_id"]))
        cols.append(p)
    X = csr_matrix(
        (np.ones(len(rows), dtype=np.float32), (rows, cols)),
        shape=(n_users, len(warm_indices)),
    )
    return X, X.toarray().astype(np.float32)


def make_score_blair_full(Xw, warm_indices, blair_emb, n_items):
    """BLaIR retrieval scorer.

    profile_u = L2-norm( mean_{j in u_train} BLaIR_j )    (warm-only training items)
    score(u, j) = cosine(profile_u, BLaIR_j)                (j over the full catalog)
    """
    # blair_emb already L2-normalised, but we re-normalise after mean.
    emb_warm = blair_emb[warm_indices]
    user_counts = np.maximum(Xw.sum(axis=1, keepdims=True), 1.0).astype(np.float32)

    def score(user_ids):
        profile = (Xw[user_ids] @ emb_warm) / user_counts[user_ids]
        norms = np.maximum(np.linalg.norm(profile, axis=1, keepdims=True), 1e-12)
        profile = profile / norms
        return (profile @ blair_emb.T).astype(np.float32)

    return score


# ---------------------------------------------------------------------------
# Full-catalog evaluator (same protocol as run_poc_cdr_books.eval_full)
# ---------------------------------------------------------------------------
def eval_full(score_fn, train_inters, test_inters, n_items, batch_size=192):
    ut = defaultdict(set)
    uts = defaultdict(list)
    for x in train_inters:
        ut[int(x["user_id"])].add(int(x["item_id"]))
    for x in test_inters:
        uts[int(x["user_id"])].append(int(x["item_id"]))
    users = sorted(u for u in uts if uts[u] and ut[u])
    ndcg, hr, rr = [], [], []
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
                per_pair_rows.append({
                    "user_id": int(u),
                    "target_item_id": int(tgt),
                    "ndcg10": float(n_),
                    "hr10": float(h),
                    "rr": float(r_),
                })
    summary = {
        "NDCG@10": float(np.mean(ndcg)) if ndcg else 0.0,
        "HR@10": float(np.mean(hr)) if hr else 0.0,
        "MRR": float(np.mean(rr)) if rr else 0.0,
        "n_eval": len(per_pair_rows),
    }
    per_user = {u: float(np.mean(vs)) for u, vs in per_user_ndcg.items()}
    return summary, per_user, per_pair_rows


# ---------------------------------------------------------------------------
# JSONL helper
# ---------------------------------------------------------------------------
def append_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, sort_keys=True) + "\n")


# ---------------------------------------------------------------------------
# Per-dataset driver
# ---------------------------------------------------------------------------
def run(dataset, seeds, jsonl_path, encoder, model_card):
    print(f"\n{'#'*70}\n# Faithful BLaIR: {dataset.upper()}\n{'#'*70}")
    interactions, titles, n_users, n_items = load_dataset(dataset)
    print(f"  n_users={n_users:,}  n_items={n_items:,}  k={DATASET_KCORE[dataset]}")

    # 1) BLaIR item embeddings (cached per dataset)
    blair_emb, cache_path, cache_source = get_or_build_blair_embeddings(
        dataset, encoder, titles)
    print(f"  embedding cache: {cache_source}  shape={blair_emb.shape}")

    # 2) per-(seed, fold) eval
    perfold = []
    per_user_all = defaultdict(list)
    fold_summaries = []

    if jsonl_path.exists():
        jsonl_path.unlink()

    for seed in seeds:
        splits = make_item_kfold(interactions, n_items, n_splits=NUM_FOLDS, seed=seed)
        for fold_id, (tr, te, cold) in enumerate(splits):
            t0 = time.time()
            train_inters = [interactions[i] for i in tr]
            test_inters = [interactions[i] for i in te]
            warm_idx = np.array(sorted(set(range(n_items)) - set(cold)), dtype=np.int32)
            _, Xw = build_warm_sparse(train_inters, n_users, warm_idx)
            score_fn = make_score_blair_full(Xw, warm_idx, blair_emb, n_items)
            summary, pu, rows = eval_full(score_fn, train_inters, test_inters, n_items)
            for r in rows:
                r.update({
                    "dataset": dataset,
                    "seed": seed,
                    "fold_id": fold_id,
                    "method": "faithful_blair",
                    "candidate_scope": "full_catalog",
                })
            append_jsonl(jsonl_path, rows)
            perfold.append(summary["NDCG@10"])
            for u, vs in pu.items():
                per_user_all[u].append(vs)
            fold_summaries.append({
                "seed": int(seed),
                "fold_id": int(fold_id),
                "n_cold_items": int(len(cold)),
                "NDCG@10": summary["NDCG@10"],
                "HR@10": summary["HR@10"],
                "MRR": summary["MRR"],
                "n_eval": summary["n_eval"],
            })
            dt = time.time() - t0
            print(f"  seed={seed} fold={fold_id}  "
                  f"NDCG@10={summary['NDCG@10']:.4f}  HR@10={summary['HR@10']:.4f}  "
                  f"MRR={summary['MRR']:.4f}  n={summary['n_eval']:,}  [{dt:.1f}s]")
            del Xw
            gc.collect()

    mean = float(np.mean(perfold)) if perfold else 0.0
    std = float(np.std(perfold)) if perfold else 0.0
    return {
        "method": "faithful_blair",
        "candidate_scope": "full_catalog",
        "encoder": model_card,
        "embedding_cache_path": cache_path,
        "n_users": int(n_users),
        "n_items": int(n_items),
        "k_core": int(DATASET_KCORE[dataset]),
        "perfold_ndcg10": list(map(float, perfold)),
        "fold_summaries": fold_summaries,
        "mean_ndcg10": mean,
        "std_ndcg10": std,
        "per_user_ndcg10": {int(u): float(np.mean(vs)) for u, vs in per_user_all.items()},
    }


# ---------------------------------------------------------------------------
# Significance helper (Wilcoxon per-user) -- optional, comparison-only
# ---------------------------------------------------------------------------
def per_user_means_from_jsonl(path):
    by_user = defaultdict(list)
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            by_user[int(r["user_id"])].append(float(r["ndcg10"]))
    return {u: float(np.mean(vs)) for u, vs in by_user.items()}


def wilcoxon_one_sided(target_means, baseline_means, name):
    common = sorted(set(target_means) & set(baseline_means))
    if not common:
        return {"comparison": name, "n_users": 0, "p_raw": 1.0,
                "delta": 0.0, "cand_mean": 0.0, "base_mean": 0.0}
    diffs = np.array([target_means[u] - baseline_means[u] for u in common])
    if np.allclose(diffs, 0):
        p = 1.0
    else:
        p = float(wilcoxon(diffs, alternative="greater", zero_method="wilcox").pvalue)
    return {
        "comparison": name,
        "n_users": int(len(common)),
        "cand_mean": float(np.mean([target_means[u] for u in common])),
        "base_mean": float(np.mean([baseline_means[u] for u in common])),
        "delta": float(np.mean(diffs)),
        "p_raw": p,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("datasets", nargs="*", default=["beauty"])
    ap.add_argument("--seeds", default=str(SEED))
    ap.add_argument("--out", default="results_faithful_blair.json")
    ap.add_argument("--encoder-only", action="store_true",
                    help="Just verify the encoder loads and write encoder card; skip eval.")
    args = ap.parse_args()
    seeds_list = [int(s) for s in args.seeds.split(",")]
    out = Path(__file__).parent / args.out

    # Load encoder once and reuse across datasets.
    print(f"Loading BLaIR encoder ({BLAIR_CHECKPOINT})...")
    encoder, model_card = load_encoder()
    print(f"  encoder loaded: {model_card}")
    if args.encoder_only:
        out.write_text(json.dumps({"encoder": model_card}, indent=2), encoding="utf-8")
        print(f"wrote encoder-only payload to {out}")
        return

    if out.exists():
        try:
            payload = json.load(open(out))
        except Exception:
            payload = {"datasets": {}}
    else:
        payload = {
            "schema_version": 1,
            "candidate_scope": "full_catalog",
            "method": "faithful_blair",
            "status": ("baseline_faithful" if model_card.get("is_official_blair")
                       else "baseline_substitute"),
            "datasets": {},
        }
    payload["encoder"] = model_card
    payload["seeds"] = [int(s) for s in seeds_list]
    payload["blair_checkpoint"] = BLAIR_CHECKPOINT
    payload["fallback_checkpoint"] = FALLBACK_CHECKPOINT
    payload["citation"] = ("Hou et al., 2024. Bridging Language and Items for "
                            "Retrieval and Recommendation. arXiv:2403.03952. "
                            "Checkpoint: https://huggingface.co/hyp1231/blair-roberta-base")
    payload["deviations_from_paper"] = [
        "Single-tower encoding: we re-use the same BLaIR encoder to compute both "
        "item-side embeddings (item title) and user profiles (mean of user's "
        "training item embeddings). The paper's full retrieval setup also "
        "supports a separate language-context tower; we use title-only because "
        "the cached metadata in this repo only consistently includes ``title``.",
        "Item TITLE only: no item description / features / reviews are "
        "concatenated, matching the simplified blair_text proxy's input.",
        "User profile = L2-normalised mean of item embeddings over training "
        "items (no review-text profile).",
    ]
    payload["protocol_match_source"] = "run_poc_cdr_books.py::eval_full (full-catalog cold-item)"

    for ds in args.datasets:
        jsonl_path = Path(__file__).parent / f"results_faithful_blair_perpair_{ds}.jsonl"
        result = run(ds, seeds_list, jsonl_path, encoder, model_card)
        result["records_jsonl"] = str(jsonl_path)
        payload["datasets"][ds] = result
        with open(out, "w") as f:
            json.dump(payload, f, indent=2)
        print(f"\n=== {ds.upper()} ===")
        print(f"perfold NDCG@10 = {result['perfold_ndcg10']}")
        print(f"mean +/- std    = {result['mean_ndcg10']:.4f} +/- {result['std_ndcg10']:.4f}")
        print(f"records         = {jsonl_path}")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
