# -*- coding: utf-8 -*-
"""E-E: build AlphaFuse-format datasets from OUR exact AR2023 5-core LLOO split.

Reads ONLY committed/available inputs (our export JSONL + the frozen MiniLM title
cache) and writes the exact file contract AlphaFuse's train.py expects, so we can
run AlphaFuse ON OUR DATA (apples-to-apples with our own numbers). It makes NO
claim and computes NO test metric -- it is data prep.

Contract (verified from ee_baselines/AlphaFuse/{train.py, models/backbone_SASRec.py,
models/embedding.py}); see ADAPTER_SPEC.md:
  train_data.df / val_data.df / test_data.df : pandas pickles, columns
      seq (list[int], LEFT-padded to L with pad=item_num), len_seq (int),
      next (single int target).  Backbone reads the LAST position (ff_out[:,-1])
      and masks positions == item_num, so histories are LEFT-padded.
  data_statis.df : pandas pickle, one row, columns seq_size (=L), item_num (=n).
  <lm>_emb.pickle : pandas Series of n float32 vectors (element i = item i),
      read by AlphaFuse via pd.read_pickle + np.stack.  AlphaFuse appends its own
      padding row (index item_num), so we ship EXACTLY n rows.

Embedding re-index join (load-bearing): our cache sbert_titles_<cat>.npy is
(n,384) keyed by asin2idx_<cat>.json (parent_asin->0..n-1), NOT export order, so
we re-index export_id -> parent_asin -> asin2idx row.  A naive [:n] slice would
silently mis-pair every item.

Output dir: ee_baselines/ours_DiT/data/ourdata/<cat>/  -- chosen so AlphaFuse's
hardcoded  data_directory = '../ours_DiT/data/' + args.data  resolves with
--data ourdata/<cat>  and NO patch to train.py.

Train-row expansion: 'prefix' (default; the DreamRec/DiffuRec family norm --
one row per (prefix -> next) step) or 'lastonly' (one row per user).  The exact
convention AlphaFuse shipped lives in their offline data-prep (Google-Drive
pickles), not their code; 'prefix' is the disclosed default until confirmed
against one downloaded sample train_data.df (ADAPTER_SPEC.md open item).

Usage:
  python ee_baselines/build_alphafuse_dataset.py --category Video_Games --maxlen 50
  python ee_baselines/build_alphafuse_dataset.py --category Video_Games --validate-only
"""
import argparse
import io
import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORT = os.path.join(ROOT, "ee_baselines", "export")
CACHE = os.path.join(ROOT, "cache_5core")
OUTBASE = os.path.join(ROOT, "ee_baselines", "ours_DiT", "data", "ourdata")


def out_dir(cat):
    return os.path.join(OUTBASE, cat)


def load_export(cat):
    seqs = []
    with io.open(os.path.join(EXPORT, cat, f"{cat}.sequences.jsonl"),
                 encoding="utf-8") as f:
        for line in f:
            seqs.append(json.loads(line))
    asins = []
    with io.open(os.path.join(EXPORT, cat, f"{cat}.items.jsonl"),
                 encoding="utf-8") as f:
        for line in f:
            j = json.loads(line)
            asins.append(j["parent_asin"])  # index = export item id
    return seqs, asins


def build_embeddings(cat, asins):
    """Re-index our MiniLM cache into export item-id order via asin2idx."""
    sbert = np.load(os.path.join(CACHE, f"sbert_titles_{cat}.npy"))
    a2i = json.load(io.open(os.path.join(CACHE, f"asin2idx_{cat}.json"),
                            encoding="utf-8"))
    n, dim = len(asins), sbert.shape[1]
    if sbert.shape[0] != n:
        raise SystemExit(f"cache rows {sbert.shape[0]} != n_items {n}")
    E = np.empty((n, dim), dtype=np.float32)
    for it in range(n):
        E[it] = sbert[a2i[asins[it]]]  # KeyError => hard fail, never guess
    return E


def left_pad(hist, L, pad):
    h = list(hist)[-L:]
    return [pad] * (L - len(h)) + h, len(h)


def make_rows(seqs, L, pad, train_mode):
    tr, va, te = [], [], []
    for d in seqs:
        T = d["train"]          # chronological train history
        v = d["valid"][0]       # single LLOO val target
        t = d["test"][0]        # single LLOO test target
        # val: predict v from full train history
        s, ln = left_pad(T, L, pad)
        va.append((s, ln, int(v)))
        # test: predict t from train+valid history
        s, ln = left_pad(T + [v], L, pad)
        te.append((s, ln, int(t)))
        # train: per-prefix (default) or last-only
        if train_mode == "lastonly":
            if len(T) >= 2:
                s, ln = left_pad(T[:-1], L, pad)
                tr.append((s, ln, int(T[-1])))
        else:  # prefix expansion: (T[:k] -> T[k]) for k=1..len(T)-1
            for k in range(1, len(T)):
                s, ln = left_pad(T[:k], L, pad)
                tr.append((s, ln, int(T[k])))
    return tr, va, te


def to_df(rows):
    return pd.DataFrame({"seq": [r[0] for r in rows],
                         "len_seq": [r[1] for r in rows],
                         "next": [r[2] for r in rows]})


def validate(cat, L):
    """Re-read via AlphaFuse's exact load path and assert every invariant."""
    d = out_dir(cat)
    statis = pd.read_pickle(os.path.join(d, "data_statis.df"))
    item_num = int(statis["item_num"][0])
    seq_size = int(statis["seq_size"][0])
    emb = pd.read_pickle(os.path.join(d, "minilm_emb.pickle"))
    emb_arr = np.stack(emb)  # AlphaFuse does exactly this
    assert seq_size == L, (seq_size, L)
    assert len(emb) == item_num, (len(emb), item_num)
    assert emb_arr.shape == (item_num, 384), emb_arr.shape
    assert emb_arr.dtype == np.float32, emb_arr.dtype
    pad = item_num
    total = {}
    for split in ("train", "val", "test"):
        df = pd.read_pickle(os.path.join(d, f"{split}_data.df"))
        total[split] = len(df)
        seqs = df["seq"].tolist()
        nxt = df["next"].tolist()
        lens = df["len_seq"].tolist()
        for i in range(0, len(seqs), max(1, len(seqs) // 500)):  # sample ~500
            s = seqs[i]
            assert len(s) == L, (split, len(s))
            # values in [0, item_num] (item_num == pad); next strictly < item_num
            assert all(0 <= x <= pad for x in s), split
            assert 0 <= nxt[i] < item_num, (split, nxt[i])
            # LEFT-pad property: pads only form a prefix (no pad after a real id)
            seen_real = False
            for x in s:
                if x == pad:
                    assert not seen_real, f"{split}: pad AFTER real id (not left-padded)"
                else:
                    seen_real = True
            # len_seq consistency
            real = sum(1 for x in s if x != pad)
            assert real == min(lens[i], L), (split, real, lens[i])
            # last position must be a real item when history non-empty
            assert s[-1] != pad, f"{split}: last position is pad"
    return item_num, seq_size, emb_arr.shape, total


def spot_check_alignment(cat, asins):
    """Independently re-derive 20 embedding rows and confirm they match."""
    sbert = np.load(os.path.join(CACHE, f"sbert_titles_{cat}.npy"))
    a2i = json.load(io.open(os.path.join(CACHE, f"asin2idx_{cat}.json"),
                            encoding="utf-8"))
    emb = np.stack(pd.read_pickle(os.path.join(out_dir(cat), "minilm_emb.pickle")))
    n = len(asins)
    idxs = list(range(0, n, max(1, n // 20)))[:20]
    for it in idxs:
        if not np.array_equal(emb[it], sbert[a2i[asins[it]]]):
            raise SystemExit(f"ALIGNMENT MISMATCH at export item {it}")
    return len(idxs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--category", default="Video_Games")
    ap.add_argument("--maxlen", type=int, default=50)
    ap.add_argument("--train-mode", choices=["prefix", "lastonly"],
                    default="prefix")
    ap.add_argument("--validate-only", action="store_true")
    args = ap.parse_args()
    cat, L = args.category, args.maxlen

    if not os.path.exists(os.path.join(EXPORT, cat, f"{cat}.sequences.jsonl")):
        raise SystemExit(f"no export for {cat}; run export_ar2023_for_baselines.py first")

    seqs, asins = load_export(cat)
    n_items = len(asins)
    pad = n_items

    if not args.validate_only:
        E = build_embeddings(cat, asins)
        assert E.shape == (n_items, 384), E.shape
        tr, va, te = make_rows(seqs, L, pad, args.train_mode)
        d = out_dir(cat)
        os.makedirs(d, exist_ok=True)
        to_df(tr).to_pickle(os.path.join(d, "train_data.df"))
        to_df(va).to_pickle(os.path.join(d, "val_data.df"))
        to_df(te).to_pickle(os.path.join(d, "test_data.df"))
        pd.DataFrame({"seq_size": [L], "item_num": [n_items]}).to_pickle(
            os.path.join(d, "data_statis.df"))
        pd.Series(list(E)).to_pickle(os.path.join(d, "minilm_emb.pickle"))
        print(f"wrote {cat}: users={len(seqs):,} items={n_items:,} L={L} "
              f"train_mode={args.train_mode} -> {d}")

    item_num, seq_size, eshape, total = validate(cat, L)
    nchk = spot_check_alignment(cat, asins)
    print(f"VALIDATE OK  item_num={item_num:,} seq_size={seq_size} "
          f"emb={eshape} rows: train={total['train']:,} val={total['val']:,} "
          f"test={total['test']:,}  alignment spot-checks={nchk} PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
