# -*- coding: utf-8 -*-
"""PREREG_TEXTPERM_V1 control caches — DETERMINISTIC (frozen rng; NumPy
Philox is platform-stable, so every pod and the local adjudicator produce
byte-identical caches; the adjudicator re-derives and hash-matches them).

Per category (MI, VG):
  - permuted map A/B/C (rng 1001/1002/1003): title-embedding rows permuted
    WITHIN train-frequency bins (f0 / f1-5 / 6-20 / >20);
  - random (rng 2001): N(0,1) rows, matched shape/dtype.
Written to cache_5core/controls/<cat>__<kind>.npy with SHA-256 printed.
"""
import hashlib
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "_bestrec_run"))
import run_sasrec_sbert as rsp

CATS = ("Musical_Instruments", "Video_Games")
MAPS = {"permA": 1001, "permB": 1002, "permC": 1003}
RANDOM_SEED = 2001


def freq_bins(category, n_items):
    train = rsp.load_split_csv(rsp.SPLIT_DIR / f"{category}.train.csv")
    valid = rsp.load_split_csv(rsp.SPLIT_DIR / f"{category}.valid.csv")
    test = rsp.load_split_csv(rsp.SPLIT_DIR / f"{category}.test.csv")
    tr, _, _, _, item_list = rsp.reindex(train, valid, test)
    assert len(item_list) == n_items, (len(item_list), n_items)
    freq = np.zeros(n_items, dtype=np.int64)
    for _, i, _, _ in tr:
        freq[i] += 1
    return np.where(freq == 0, 0,
                    np.where(freq <= 5, 1,
                             np.where(freq <= 20, 2, 3))).astype(np.int64)


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main():
    out_dir = os.path.join(ROOT, "cache_5core", "controls")
    os.makedirs(out_dir, exist_ok=True)
    report = {}
    for cat in CATS:
        src = os.path.join(ROOT, "cache_5core", f"sbert_titles_{cat}.npy")
        E = np.load(src)
        # the trainer slices [:n_items]; derive n_items from the split
        train = rsp.load_split_csv(rsp.SPLIT_DIR / f"{cat}.train.csv")
        valid = rsp.load_split_csv(rsp.SPLIT_DIR / f"{cat}.valid.csv")
        test = rsp.load_split_csv(rsp.SPLIT_DIR / f"{cat}.test.csv")
        _, _, _, _, item_list = rsp.reindex(train, valid, test)
        n_items = len(item_list)
        bins = freq_bins(cat, n_items)
        for kind, seed in MAPS.items():
            rng = np.random.default_rng(seed)
            P = E.copy()
            for b in range(4):
                idx = np.where(bins == b)[0]
                P[idx] = P[rng.permutation(idx)]
            dst = os.path.join(out_dir, f"{cat}__{kind}.npy")
            if not os.path.exists(dst):
                np.save(dst + ".tmp.npy", P)
                os.replace(dst + ".tmp.npy", dst)
            report[f"{cat}__{kind}"] = sha(dst)
        # audit 2026-07-23 22:00: the random control MUST match the aligned
        # cache's row norm (canonical rows are L2-normalized to 1.0). An
        # un-normalized N(0,1) row has norm ~sqrt(d)~19.6, so the old cache
        # tested "semantic destruction PLUS a 19.6x scale intervention".
        # Row-normalize to isolate semantic content.
        rng = np.random.default_rng(RANDOM_SEED)
        Rm = rng.standard_normal(E.shape).astype(E.dtype)
        Rm /= np.clip(np.linalg.norm(Rm, axis=1, keepdims=True), 1e-8, None)
        dst = os.path.join(out_dir, f"{cat}__random.npy")
        if not os.path.exists(dst):
            np.save(dst + ".tmp.npy", Rm)
            os.replace(dst + ".tmp.npy", dst)
        report[f"{cat}__random"] = sha(dst)
    for k, v in sorted(report.items()):
        print(f"CACHE {k} sha256={v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
