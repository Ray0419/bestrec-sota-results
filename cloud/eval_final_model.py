# -*- coding: utf-8 -*-
"""Sequestered single test evaluation of ONE trained base model (E-B and any
--no-test-eval campaign). Streams test once, four-bin accounting, prints NO
metric values (adjudicator is the first reader). Records the sha256 of the
embedding cache the model was trained with (control-arm provenance).

Usage: python cloud/eval_final_model.py <base_run.json> [--out o]
"""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "_bestrec_run"))
import run_sasrec_sbert as rsp
from fuse_ease_eval import build_model_from_config
from fuse_cold_confirm2 import stream_eval

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_json")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    base = json.load(open(args.run_json, encoding="utf-8"))
    cfg = base["config"]
    category = cfg["category"]
    print(f"=== final eval (sequestered): {category} seed {cfg['seed']} ===",
          flush=True)

    train_rows = rsp.load_split_csv(rsp.SPLIT_DIR / f"{category}.train.csv")
    valid_rows = rsp.load_split_csv(rsp.SPLIT_DIR / f"{category}.valid.csv")
    test_rows = rsp.load_split_csv(rsp.SPLIT_DIR / f"{category}.test.csv")
    train_inters, valid_inters, test_inters, user_list, item_list = rsp.reindex(
        train_rows, valid_rows, test_rows)
    n_items = len(item_list)
    pad_id = n_items
    user_seqs = rsp.build_user_sequences(train_inters)
    user_times = (rsp.build_user_time_sequences(train_inters)
                  if cfg.get("time_bias") else None)
    val_extra, val_extra_times = {}, {}
    for u, i, _, t in valid_inters:
        val_extra.setdefault(u, []).append(i)
        val_extra_times.setdefault(u, []).append(t // 1000)
    test_dict = {u: i for u, i, _, _ in test_inters}
    test_users = sorted(test_dict.keys())

    freq = np.zeros(n_items, dtype=np.int64)
    for _, i, _, _ in train_inters:
        freq[i] += 1
    bin4 = np.where(freq == 0, 0,
                    np.where(freq <= 5, 1,
                             np.where(freq <= 20, 2, 3))).astype(np.int64)

    enc_cache = cfg.get("encoder_cache")
    sbert_npy = (Path(enc_cache) if enc_cache
                 else rsp.EMB_CACHE_DIR / f"sbert_titles_{category}.npy")
    cache_sha = hashlib.sha256(open(sbert_npy, "rb").read()).hexdigest()
    Eraw = np.load(sbert_npy).astype(np.float32)[:n_items]

    ckpt = torch.load(Path(args.run_json).with_suffix(".best.pt"),
                      map_location="cpu", weights_only=False)
    proto_assign = [t.to(DEVICE) for t in ckpt.get("proto_assign", [])] or None
    model = build_model_from_config(cfg, n_items, pad_id, Eraw, proto_assign)
    model.load_state_dict(ckpt["state_dict"], strict=False)
    model.to(DEVICE).eval()

    tres, pu = stream_eval(model, test_users, user_seqs, val_extra, user_times,
                           val_extra_times, cfg, pad_id, n_items, {}, None,
                           0.0, [{"name": "REF", "kind": "ref", "emb": None,
                                  "profile": None, "wvec": None}],
                           bin4, test_dict, collect_per_user=True, silent=True)
    print("  test pass complete (values sequestered)", flush=True)

    out = Path(args.out) if args.out else Path(args.run_json).with_name(
        Path(args.run_json).stem + ".finaleval.json")
    json.dump({"category": category, "seed": cfg["seed"],
               "encoder_cache": str(sbert_npy), "cache_sha256": cache_sha,
               "best_ckpt_sha256": base.get("best_ckpt_sha256"),
               "test": tres["REF"]},
              open(out, "w", encoding="utf-8"), indent=1)
    tb = np.array([bin4[test_dict[u]] for u in test_users], dtype=np.int64)
    np.savez_compressed(str(out)[:-5] + ".perusers.npz",
                        users=np.array(test_users, dtype=np.int64),
                        target_bin4=tb, ref_ndcg=pu["REF"])
    print(f"wrote {out} (metrics sequestered)", flush=True)
    return 0


if __name__ == "__main__":
    sys.stderr.write("VOID: E-B / PREREG_TEXTPERM_V1 is tombstoned (audit "
                     "2026-07-24); this evaluator hard-refuses. A corrected "
                     "PREREG_TEXTPERM_V2 in a new namespace is required.\n")
    sys.exit(3)
