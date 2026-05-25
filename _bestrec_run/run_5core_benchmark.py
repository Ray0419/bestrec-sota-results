"""Run our methods on the STANDARD Amazon Reviews 2023 5-core benchmark
(produced by `_bestrec_run/preprocess_5core_standard.py`).

This is the protocol TIGER, LIGER, BLaIR all use:
  - 5-core filtering (recursive)
  - Leave-last-out split (last interaction per user = test, 2nd-to-last = valid, rest = train)
  - Evaluation: rank held-out test item against full catalog, mask training items
  - Headline metrics: NDCG@10, HR@10, MRR

This script focuses on the WARM-LOO protocol (where TIGER/LIGER/BLaIR
have published numbers). Cold-item-specific methods like CDR_validated are
not directly comparable here — they're applied separately on cold splits.

We benchmark these methods on the 5-core split:
  - popularity (trivial baseline)
  - content_direct (sum of SBERT cosines over user history)
  - ease_pure (EASE without content prior)
  - ease_sbert (EASE+SBERT — our headline warm method)

Usage:
    uv run python run_5core_benchmark.py Video_Games --encode-titles
    uv run python run_5core_benchmark.py Video_Games  # uses cached embeddings

The SBERT encoding is done once and cached to disk.
"""
from __future__ import annotations

import argparse
import csv
import gc
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
from scipy.sparse import csr_matrix

from ease_efficient import ease_fast

ROOT = Path(__file__).resolve().parent.parent
SPLIT_DIR = ROOT / "data_5core" / "5core" / "last_out"
META_PATHS = {
    "Video_Games":              ROOT / "data_raw_proper" / "video_games" / "meta_Video_Games.jsonl",
    "Beauty_and_Personal_Care": ROOT / "data_raw_proper" / "beauty_and_pc" / "meta_Beauty_and_Personal_Care.jsonl",
}
EMB_CACHE_DIR = ROOT / "cache_5core"


def load_split_csv(path: Path) -> list[tuple]:
    """Load a CSV with columns: user_id,parent_asin,rating,timestamp."""
    rows = []
    with path.open("r", encoding="utf-8") as fp:
        rdr = csv.DictReader(fp)
        for r in rdr:
            rows.append((r["user_id"], r["parent_asin"],
                          float(r["rating"]), int(r["timestamp"])))
    return rows


def load_titles(meta_path: Path, asin_set: set[str]) -> dict[str, str]:
    """Load item titles from the metadata jsonl, restricted to a given set of parent_asins."""
    titles = {}
    with meta_path.open("r", encoding="utf-8") as fp:
        for line in fp:
            try:
                d = json.loads(line.strip())
            except json.JSONDecodeError:
                continue
            pa = d.get("parent_asin")
            if pa is None or pa not in asin_set:
                continue
            title = d.get("title") or ""
            if isinstance(title, list):
                title = " ".join(str(x) for x in title)
            titles[pa] = str(title).strip()
    return titles


def encode_titles_sbert(titles_list: list[str], device: str = "cuda" if torch.cuda.is_available() else "cpu") -> np.ndarray:
    """Encode item titles with all-MiniLM-L6-v2 SBERT. Returns float32 array (n_items, 384)."""
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", device=device)
    embeddings = model.encode(titles_list, batch_size=256, show_progress_bar=True,
                                 convert_to_numpy=True, normalize_embeddings=False)
    return embeddings.astype(np.float32)


def reindex(train_rows, valid_rows, test_rows):
    """Return contiguous integer IDs for users and items based on the union of all splits."""
    all_rows = train_rows + valid_rows + test_rows
    users = sorted({r[0] for r in all_rows})
    items = sorted({r[1] for r in all_rows})
    u2idx = {u: i for i, u in enumerate(users)}
    i2idx = {a: j for j, a in enumerate(items)}
    def cvt(rows):
        return [(u2idx[u], i2idx[a], r, t) for u, a, r, t in rows]
    return cvt(train_rows), cvt(valid_rows), cvt(test_rows), users, items


def build_train_matrix(train_inters, n_users, n_items):
    rows = np.array([t[0] for t in train_inters], dtype=np.int64)
    cols = np.array([t[1] for t in train_inters], dtype=np.int64)
    vals = np.ones(len(rows), dtype=np.float32)
    return csr_matrix((vals, (rows, cols)), shape=(n_users, n_items))


def eval_loo(score_fn, train_inters, test_inters, n_items, batch_size: int = 256,
              top_k: int = 10):
    """Standard leave-one-out evaluation. For each (user, test_item) pair, score against all items,
    mask the user's training items, report NDCG@top_k, HR@top_k, MRR."""
    user_train: dict[int, set] = defaultdict(set)
    for u, j, _, _ in train_inters:
        user_train[u].add(j)
    user_test: dict[int, int] = {}
    for u, j, _, _ in test_inters:
        if u in user_test:
            # multiple test items per user shouldn't happen in last-out, but tolerate
            continue
        user_test[u] = j

    users = sorted(user_test.keys())
    n_eval = len(users)
    ndcg, hr, rr = [], [], []
    print(f"  evaluating {n_eval:,} users in batches of {batch_size}...")
    t0 = time.time()
    for s in range(0, n_eval, batch_size):
        batch_users = users[s:s + batch_size]
        # Score all items for this batch
        sc = score_fn(np.array(batch_users, dtype=np.int64)).astype(np.float32, copy=True)
        for k, u in enumerate(batch_users):
            if user_train[u]:
                sc[k, list(user_train[u])] = -np.inf
            tgt = user_test[u]
            tgt_score = sc[k, tgt]
            rank0 = int((sc[k] > tgt_score).sum())
            if rank0 < top_k:
                ndcg.append(1.0 / math.log2(rank0 + 2))
                hr.append(1.0)
            else:
                ndcg.append(0.0); hr.append(0.0)
            rr.append(1.0 / (rank0 + 1))
        if (s // batch_size) % 20 == 0:
            print(f"    [{s + len(batch_users):,}/{n_eval:,}  elapsed {time.time()-t0:.1f}s]")
    print(f"  eval done in {time.time()-t0:.1f}s")
    return {
        "NDCG@10": float(np.mean(ndcg)),
        "HR@10":   float(np.mean(hr)),
        "MRR":     float(np.mean(rr)),
        "n_eval":  len(users),
    }


def make_popularity(train_inters, n_items):
    pop = np.zeros(n_items, dtype=np.float32)
    for _, j, _, _ in train_inters:
        pop[j] += 1.0
    def f(uids):
        return np.tile(pop, (len(uids), 1))
    return f


def make_content_direct(X_train_dense, S_content):
    def f(uids):
        return X_train_dense[uids] @ S_content
    return f


def make_ease(X_train_csr, lam, beta, S_content, dtype=np.float32):
    B = ease_fast(X_train_csr, lam=lam, beta=beta, S_content=S_content, dtype=dtype)
    X_dense = X_train_csr.toarray().astype(np.float32)
    def f(uids):
        return X_dense[uids] @ B
    return f, B


def content_sim_from_embeddings(emb: np.ndarray, dtype=np.float32) -> np.ndarray:
    """Compute (n_items, n_items) cosine sim from raw (unnormalized) SBERT embeddings."""
    norms = np.linalg.norm(emb, axis=1, keepdims=True)
    en = emb / np.maximum(norms, 1e-12)
    S = (en @ en.T).astype(dtype)
    np.fill_diagonal(S, 0.0)
    return S


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("category", help="Category name (Video_Games, Beauty_and_Personal_Care, ...)")
    ap.add_argument("--encode-titles", action="store_true",
                     help="(Re)encode item titles with SBERT and cache to disk")
    ap.add_argument("--lam", type=float, default=200.0)
    ap.add_argument("--beta", type=float, default=10.0)
    ap.add_argument("--out", default=None,
                     help="Results JSON output path")
    args = ap.parse_args()

    out_path = Path(args.out) if args.out else (Path(__file__).parent / f"results_5core_{args.category}.json")

    train_csv = SPLIT_DIR / f"{args.category}.train.csv"
    valid_csv = SPLIT_DIR / f"{args.category}.valid.csv"
    test_csv = SPLIT_DIR / f"{args.category}.test.csv"
    meta_path = META_PATHS.get(args.category)
    for p in (train_csv, valid_csv, test_csv):
        if not p.exists():
            print(f"ERROR: {p} not found. Run preprocess_5core_standard.py {args.category} first.")
            return 2
    if meta_path is None or not meta_path.exists():
        print(f"ERROR: metadata for {args.category} not at {meta_path}.")
        return 2

    print(f"\n=== {args.category}: Load splits ===")
    t0 = time.time()
    train_rows = load_split_csv(train_csv)
    valid_rows = load_split_csv(valid_csv)
    test_rows = load_split_csv(test_csv)
    print(f"  train={len(train_rows):,}  valid={len(valid_rows):,}  test={len(test_rows):,}  [{time.time()-t0:.1f}s]")

    train_inters, valid_inters, test_inters, user_list, item_list = reindex(train_rows, valid_rows, test_rows)
    n_users, n_items = len(user_list), len(item_list)
    print(f"  n_users={n_users:,}  n_items={n_items:,}")

    # Load and encode titles
    EMB_CACHE_DIR.mkdir(exist_ok=True)
    emb_path = EMB_CACHE_DIR / f"sbert_titles_{args.category}.npy"
    asin2idx_path = EMB_CACHE_DIR / f"asin2idx_{args.category}.json"
    if args.encode_titles or not emb_path.exists():
        print(f"\n=== {args.category}: Load titles from metadata ===")
        t0 = time.time()
        titles = load_titles(meta_path, set(item_list))
        print(f"  {len(titles):,} / {n_items:,} items have titles  [{time.time()-t0:.1f}s]")
        title_strings = [titles.get(asin, "") for asin in item_list]
        n_empty = sum(1 for t in title_strings if not t.strip())
        if n_empty:
            print(f"  WARN: {n_empty:,} items have empty title; using empty string")

        print(f"\n=== {args.category}: SBERT encoding ({n_items:,} items) ===")
        t0 = time.time()
        emb = encode_titles_sbert(title_strings)
        print(f"  encoded {n_items:,} items -> {emb.shape}  [{time.time()-t0:.1f}s]")
        np.save(emb_path, emb)
        with asin2idx_path.open("w") as fp:
            json.dump({a: i for i, a in enumerate(item_list)}, fp)
        print(f"  cached to {emb_path}")
    else:
        print(f"\n=== {args.category}: Loading cached SBERT embeddings ===")
        emb = np.load(emb_path)
        print(f"  loaded {emb.shape} from {emb_path}")
        # Sanity check: cached embeddings must align with current item_list
        cached_idx = json.load(asin2idx_path.open())
        if any(cached_idx.get(asin) != i for i, asin in enumerate(item_list)):
            print(f"  WARN: cached embeddings don't match current item_list order; re-encoding")
            return main()  # rerun with --encode-titles equivalent

    # Build content similarity (n_items × n_items)
    print(f"\n=== {args.category}: Content similarity matrix ===")
    t0 = time.time()
    S_content = content_sim_from_embeddings(emb)
    print(f"  S_content shape={S_content.shape}  [{time.time()-t0:.1f}s]")

    # Build training sparse matrix
    X_train_csr = build_train_matrix(train_inters, n_users, n_items)
    print(f"  X_train nnz={X_train_csr.nnz:,}")

    results = {"category": args.category, "n_users": n_users, "n_items": n_items,
                "n_train_inters": len(train_inters), "n_test": len(test_inters),
                "lam": args.lam, "beta": args.beta, "methods": {}}

    # 1) Popularity baseline
    print(f"\n=== Popularity baseline ===")
    t0 = time.time()
    sf = make_popularity(train_inters, n_items)
    pop_metrics = eval_loo(sf, train_inters, test_inters, n_items)
    pop_metrics["wall_time_s"] = time.time() - t0
    results["methods"]["popularity"] = pop_metrics
    print(f"  popularity: {pop_metrics}")

    # 2) Content-direct (X_train @ S_content)
    print(f"\n=== Content-direct baseline ===")
    t0 = time.time()
    X_train_dense = X_train_csr.toarray().astype(np.float32)
    sf = make_content_direct(X_train_dense, S_content)
    cd_metrics = eval_loo(sf, train_inters, test_inters, n_items)
    cd_metrics["wall_time_s"] = time.time() - t0
    results["methods"]["content_direct"] = cd_metrics
    print(f"  content_direct: {cd_metrics}")
    del X_train_dense; gc.collect()

    # 3) EASE pure
    print(f"\n=== EASE pure (beta=0) ===")
    t0 = time.time()
    sf, B_pure = make_ease(X_train_csr, lam=args.lam, beta=0.0, S_content=None)
    pure_metrics = eval_loo(sf, train_inters, test_inters, n_items)
    pure_metrics["wall_time_s"] = time.time() - t0
    results["methods"]["ease_pure"] = pure_metrics
    print(f"  ease_pure: {pure_metrics}")
    del B_pure; gc.collect()

    # 4) EASE + SBERT (our headline warm method)
    print(f"\n=== EASE + SBERT (lam={args.lam} beta={args.beta}) ===")
    t0 = time.time()
    sf, B = make_ease(X_train_csr, lam=args.lam, beta=args.beta, S_content=S_content)
    ease_metrics = eval_loo(sf, train_inters, test_inters, n_items)
    ease_metrics["wall_time_s"] = time.time() - t0
    results["methods"]["ease_sbert"] = ease_metrics
    print(f"  ease_sbert: {ease_metrics}")
    del B; gc.collect()

    # Write results
    with out_path.open("w") as f:
        json.dump(results, f, indent=2,
                   default=lambda o: float(o) if hasattr(o, "item") else str(o))
    print(f"\nwrote {out_path}")

    # Summary table
    print(f"\n=== {args.category} 5-core benchmark summary ===")
    print(f"{'Method':<20} {'NDCG@10':>10} {'HR@10':>10} {'MRR':>10}   {'sec':>8}")
    for name, m in results["methods"].items():
        print(f"  {name:<18}  {m['NDCG@10']:>9.4f}  {m['HR@10']:>9.4f}  {m['MRR']:>9.4f}   {m['wall_time_s']:>7.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
