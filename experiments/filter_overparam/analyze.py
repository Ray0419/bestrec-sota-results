"""Aggregate the FMLP-Rec filter-parameterisation ladder + measure filter redundancy.

  python analyze.py results <DATASET>...   -> per-arm test metrics, paired stats vs `full`
  python analyze.py filters <DATASET>      -> SVD/rank analysis of the learned `full` filter
"""
from __future__ import annotations

import ast
import glob
import math
import os
import re
import statistics as st
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.environ.get("BSAREC_DIR", os.path.join(_HERE, "BSARec")),
                   "src", "output")
ARMS = ["full", "rank1", "shared", "none"]
PARAMS = {"full": 6656, "rank1": 360, "shared": 104, "none": 0}


def final_test(path):
    """Last dict logged after the '---------------Test Score---------------' banner."""
    txt = open(path).read()
    if "Test Score" not in txt:
        return None
    tail = txt.split("Test Score")[-1]
    m = re.findall(r"\{[^}]*'HR@5'[^}]*\}", tail)
    if not m:
        return None
    d = ast.literal_eval(m[-1])
    return {k: float(v) for k, v in d.items() if k != "Epoch"}


def collect(dataset):
    res = {a: {} for a in ARMS}
    for p in sorted(glob.glob(f"{OUT}/LADDER_{dataset}_*.log")):
        mm = re.search(rf"LADDER_{dataset}_(\w+?)_s(\d+)\.log$", p)
        if not mm:
            continue
        arm, seed = mm.group(1), int(mm.group(2))
        r = final_test(p)
        if r:
            res[arm][seed] = r
    return res


def paired(a, b):
    d = [x - y for x, y in zip(a, b)]
    n = len(d)
    if n < 2:
        return None
    m, s = st.mean(d), st.stdev(d)
    se = s / math.sqrt(n)
    t = m / se if se else float("inf")
    # keyed by n (sample size), value is the two-sided .975 t-quantile at df=n-1
    crit = {2: 12.706, 3: 4.303, 4: 3.182, 5: 2.776, 6: 2.571, 7: 2.447,
            8: 2.365, 9: 2.306, 10: 2.262}.get(n, 1.96)
    return m, s, t, n - 1, (m - crit * se, m + crit * se), sum(1 for x in d if x > 0)


def do_results(datasets):
    for ds in datasets:
        res = collect(ds)
        seeds = sorted(set.intersection(*[set(res[a]) for a in ARMS if res[a]])
                       ) if all(res[a] for a in ARMS) else []
        print(f"\n{'='*76}\n{ds}   complete seeds: {seeds}\n{'='*76}")
        if not seeds:
            for a in ARMS:
                print(f"  {a:<7} finished seeds: {sorted(res[a])}")
            continue
        for metric in ("NDCG@10", "HR@10"):
            print(f"\n  --- {metric} ---")
            print(f"  {'arm':<7} {'params':>7}  {'mean':>8} {'sd':>8}   vs full: diff / t / CI95 / seeds+")
            base = [res["full"][s][metric] for s in seeds]
            for a in ARMS:
                v = [res[a][s][metric] for s in seeds]
                line = f"  {a:<7} {PARAMS[a]:>7}  {st.mean(v):>8.4f} {st.stdev(v) if len(v)>1 else 0:>8.4f}"
                if a != "full":
                    p = paired(v, base)
                    if p:
                        m, s, t, df, ci, pos = p
                        line += (f"   {m:+.4f} / t={t:+5.2f} /"
                                 f" [{ci[0]:+.4f},{ci[1]:+.4f}] / {pos}/{len(v)}")
                print(line)


def do_filters(dataset):
    import torch
    for p in sorted(glob.glob(f"{OUT}/LADDER_{dataset}_full_s*.pt")):
        sd = torch.load(p, map_location="cpu")
        sd = sd.get("state_dict", sd) if isinstance(sd, dict) else sd
        print(f"\n{os.path.basename(p)}")
        for k, v in sd.items():
            if "complex_weight" not in k:
                continue
            w = torch.view_as_complex(v)[0]          # [n_freq, d]
            mag = w.abs()
            sv = torch.linalg.svdvals(w)
            e = (sv ** 2)
            top1 = (e[0] / e.sum()).item()
            eff = (e.sum() ** 2 / (e ** 2).sum()).item()   # participation ratio
            # pairwise cosine between channel magnitude responses
            M = mag / (mag.norm(dim=0, keepdim=True) + 1e-9)
            C = (M.T @ M)
            off = C[~torch.eye(C.shape[0], dtype=bool)]
            print(f"  {k}")
            print(f"    shape={tuple(w.shape)}  top1_energy={top1:.4f}  "
                  f"eff_rank={eff:.2f}/{min(w.shape)}")
            print(f"    inter-channel |cos| mean={off.abs().mean():.4f} "
                  f"min={off.abs().min():.4f}")


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "results":
        do_results(sys.argv[2:])
    else:
        do_filters(sys.argv[2])
