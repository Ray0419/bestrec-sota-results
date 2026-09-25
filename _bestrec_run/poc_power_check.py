# -*- coding: utf-8 -*-
"""Power check: eval targets per dose group for PREREG_DOSE_RESPONSE_V1."""
import json
import os
import sys

import numpy as np

sys.path.insert(0, r"C:\Users\rayxc\Documents\R\_bestrec_run")
import run_sasrec_sbert as rsp  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
capset_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    HERE, "poc_out", "smoke_multi.json.capset.json")

cat = "Musical_Instruments"
tr = rsp.load_split_csv(rsp.SPLIT_DIR / f"{cat}.train.csv")
va = rsp.load_split_csv(rsp.SPLIT_DIR / f"{cat}.valid.csv")
te = rsp.load_split_csv(rsp.SPLIT_DIR / f"{cat}.test.csv")
_, _, test_inters, _, item_list = rsp.reindex(tr, va, te)
cs = json.load(open(capset_path, encoding="utf-8"))
tgt = np.array([i for _, i, _, _ in test_inters])
print(f"total test targets: {len(tgt):,}  n_items={len(item_list):,}")
for g, items in cs["groups"].items():
    n = int(np.isin(tgt, np.array(items)).sum())
    print(f"  group {g:>8}: {len(items):>4} items, {n:>6,} eval targets "
          f"({100*n/len(tgt):.2f}%)")
