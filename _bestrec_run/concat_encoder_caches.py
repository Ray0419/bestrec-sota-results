"""Concatenate multiple encoder caches (e.g. BLaIR 768-d + rich-text MiniLM 384-d)
into a single .npy cache. The resulting cache has dim = sum of input dims.

Both caches must share the same item ordering — they were both produced by
load_item_list() in encode_*_5core.py, which sorts by parent_asin, so they
align. We additionally verify the asin2idx jsons match.

Usage:
    uv run python concat_encoder_caches.py \\
        --inputs cache_5core/blair_titles_Beauty.npy cache_5core/richtext_titles_Beauty.npy \\
        --asin2idx cache_5core/asin2idx_blair_Beauty.json cache_5core/asin2idx_richtext_Beauty.json \\
        --out cache_5core/fusion_blair_richtext_Beauty.npy
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inputs", nargs="+", required=True,
                     help="Paths to input .npy caches to concatenate (in order)")
    ap.add_argument("--asin2idx", nargs="+", required=True,
                     help="Paths to corresponding asin2idx .json files for verification")
    ap.add_argument("--l2norm", action="store_true",
                     help="L2-normalize each input chunk before concatenation "
                          "(produces a unit-norm fusion vector if all inputs were normalized)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    assert len(args.inputs) == len(args.asin2idx), "must give one --asin2idx per --input"

    # Verify all asin2idx files match
    base_map = None
    for p in args.asin2idx:
        m = json.load(open(p, encoding="utf-8"))
        if base_map is None:
            base_map = m
        else:
            assert m == base_map, f"asin2idx mismatch: {p} differs from {args.asin2idx[0]}"
    n_items = len(base_map)
    print(f"asin2idx maps all match: {n_items:,} items")

    arrs = []
    for p in args.inputs:
        a = np.load(p)
        assert a.shape[0] == n_items, f"{p} has {a.shape[0]} items, expected {n_items}"
        if args.l2norm:
            norms = np.linalg.norm(a, axis=1, keepdims=True)
            a = a / np.maximum(norms, 1e-12)
        arrs.append(a.astype(np.float32))
        print(f"  loaded {p}  shape={a.shape}")

    fused = np.concatenate(arrs, axis=1)
    print(f"fused shape={fused.shape}")
    np.save(args.out, fused)
    print(f"wrote {args.out}  ({fused.shape}, {Path(args.out).stat().st_size/1e6:.1f} MB)")

    # Write a matching asin2idx (just copy the verified one)
    out_idx = Path(args.out).with_name("asin2idx_" + Path(args.out).stem + ".json")
    with out_idx.open("w") as fp:
        json.dump(base_map, fp)
    print(f"wrote {out_idx}")


if __name__ == "__main__":
    main()
