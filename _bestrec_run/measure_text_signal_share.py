#!/usr/bin/env python
# READ-ONLY artifact (NO GPU, NO training, NO model-code edit). Grounds XF 2026-06-17-8.
# Per-popularity-tercile "text-signal share" s_text that PREDICTS the dataset-conditional tail law.
import csv, json, math
from pathlib import Path
from collections import defaultdict
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
SPLIT = ROOT / "data_5core" / "5core" / "last_out"
EMB   = ROOT / "cache_5core"
DATASETS = ["Video_Games", "Musical_Instruments", "Beauty_and_Personal_Care"]
RNG = np.random.default_rng(20260617); M = 40000; NPERM = 200
def rd(p):
    out = []
    with open(p, "r", encoding="utf-8") as fp:
        for r in csv.DictReader(fp):
            out.append((r["user_id"], r["parent_asin"], int(r["timestamp"])))
    return out
def z(v):
    v = v - v.mean(); s = v.std(); return v / s if s > 1e-12 else v
def r2(X, y):
    b, *_ = np.linalg.lstsq(X, y, rcond=None); res = y - X @ b
    sst = ((y - y.mean())**2).sum(); return 1.0 - (res**2).sum()/sst if sst > 0 else 0.0
def partition(y, x1, x2):
    yz, a, b = z(y), z(x1), z(x2); one = np.ones_like(yz)
    Rf = r2(np.column_stack([one, a, b]), yz)
    Rid = r2(np.column_stack([one, b]), yz); Rtx = r2(np.column_stack([one, a]), yz)
    pr_t = max(Rf - Rid, 0.0); pr_i = max(Rf - Rtx, 0.0)
    s = pr_t/(pr_t+pr_i) if (pr_t+pr_i) > 1e-12 else float("nan")
    ge = 1
    for _ in range(NPERM):
        if max(r2(np.column_stack([one, RNG.permutation(a), b]), yz) - Rid, 0.0) >= pr_t: ge += 1
    return dict(R_full=Rf, pr_text=pr_t, pr_id=pr_i, s_text=s, perm_p=ge/(NPERM+1))
def distinct(T, samp=2000, cstep=20000):
    n = T.shape[0]; idx = RNG.integers(0, n, min(samp, n)); Q = T[idx]; best = np.full(len(idx), -1.0)
    for c0 in range(0, n, cstep):
        S = Q @ T[c0:c0+cstep].T
        for k, i in enumerate(idx):
            if c0 <= i < c0+cstep: S[k, i-c0] = -1.0
        best = np.maximum(best, S.max(axis=1))
    return float(best.mean())
def analyze(ds):
    tr = rd(SPLIT/f"{ds}.train.csv"); asins = set(a for _, a, _ in tr)
    for sp in ("valid", "test"):
        for _, a, _ in rd(SPLIT/f"{ds}.{sp}.csv"): asins.add(a)
    items = sorted(asins); i2 = {a: j for j, a in enumerate(items)}; n = len(items)
    T = np.load(EMB/f"sbert_titles_{ds}.npy").astype(np.float32)[:n]
    T /= (np.linalg.norm(T, axis=1, keepdims=True) + 1e-8)
    seqs = defaultdict(list); iu = defaultdict(set); freq = np.zeros(n, np.int64)
    for u, a, t in tr:
        j = i2[a]; seqs[u].append((t, j)); iu[j].add(u); freq[j] += 1
    adj = defaultdict(int)
    for u, lst in seqs.items():
        lst.sort()
        for (_, p), (_, q) in zip(lst, lst[1:]):
            if p != q: adj[(p, q) if p < q else (q, p)] += 1
    Ntr = max(int(freq.sum()), 1); pf = freq/Ntr
    order = np.argsort(freq, kind="stable"); b1, b2 = n//3, 2*n//3
    strata = {"tail": order[:b1], "mid": order[b1:b2], "head": order[b2:], "all": order}
    def sample(pool):
        ii = pool[RNG.integers(0, len(pool), M)]; jj = pool[RNG.integers(0, len(pool), M)]
        keep = ii != jj; ii, jj = ii[keep], jj[keep]
        x1 = np.einsum("kd,kd->k", T[ii], T[jj]); x2 = np.empty(len(ii)); y = np.empty(len(ii))
        for k in range(len(ii)):
            i, j = int(ii[k]), int(jj[k]); A, B = iu[i], iu[j]
            inter = len(A & B) if A and B else 0
            x2[k] = inter/(len(A)+len(B)-inter) if inter else 0.0
            c = adj.get((i, j) if i < j else (j, i), 0)
            y[k] = math.log(((c+1e-9)/Ntr)/(pf[i]*pf[j]+1e-12)+1e-12)
        return y, x1, x2
    res = {nm: partition(*sample(pool)) for nm, pool in strata.items()}
    res["meta"] = dict(n_items=n, n_train=Ntr, users_per_item=round(len(seqs)/n, 3),
                       mean_top1_text_cos=distinct(T))
    return res
if __name__ == "__main__":
    out = {ds: analyze(ds) for ds in DATASETS}
    (ROOT/"_bestrec_run"/"results_TEXTSHARE_law.json").write_text(json.dumps(out, indent=2))
    for ds, r in out.items():
        print("%-26s s_text tail=%.3f (p=%.3f) mid=%.3f head=%.3f all=%.3f | upi=%.2f top1cos=%.3f"
              % (ds, r["tail"]["s_text"], r["tail"]["perm_p"], r["mid"]["s_text"],
                 r["head"]["s_text"], r["all"]["s_text"],
                 r["meta"]["users_per_item"], r["meta"]["mean_top1_text_cos"]))
