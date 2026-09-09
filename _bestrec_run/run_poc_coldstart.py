# -*- coding: utf-8 -*-
"""POC runner v2 for RESEARCH_QUESTIONS_COLDSTART.md (read-only vs main repo).

POC-A  observational degree-response curve, TFV2 VG text (seeds 20260841-48)
       vs idonly (20260851-58). Arms are NOT initialization-paired (different
       seed ranges) -> treated as two independent 8-seed samples per degree
       bucket; identical frozen eval users/targets across arms.
POC-0  EB premise diagnostics on the trained TEXT-arm table using the
       EFFECTIVE item embedding E = item_emb + proj(sbert) [+ TAPE recon],
       which is the object the model actually scores with.

Also validates the degree join against the trainer's own pop_bucket terciles.
Writes only to <this dir>/poc_out/.
"""
import csv
import glob
import gzip
import json
import os
import re
import sys
from collections import defaultdict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import poc_eb_core as eb  # noqa: E402

MAIN = r"C:\Users\rayxc\Documents\R"
RUN = os.path.join(MAIN, "_bestrec_run")
SPLIT = os.path.join(MAIN, "data_5core", "5core", "last_out")
CACHE = os.path.join(MAIN, "cache_5core")
OUT_DIR = os.path.join(HERE, "poc_out")
os.makedirs(OUT_DIR, exist_ok=True)

DEG_EDGES = [(0, 0), (1, 2), (3, 5), (6, 10), (11, 20), (21, 50), (51, 150),
             (151, 500), (501, 10 ** 9)]


def item_degrees(category):
    with open(os.path.join(CACHE, f"asin2idx_{category}.json"), encoding="utf-8") as f:
        asin2idx = json.load(f)
    n_items = max(asin2idx.values()) + 1
    deg = np.zeros(n_items, dtype=np.int64)
    path = os.path.join(SPLIT, f"{category}.train.csv")
    with open(path, encoding="utf-8", newline="") as f:
        rdr = csv.reader(f)
        header = next(rdr)
        ii = header.index("parent_asin")
        for row in rdr:
            idx = asin2idx.get(row[ii])
            if idx is not None:
                deg[idx] += 1
    return deg


def degree_terciles(deg):
    """Replicate trainer logic: stable argsort by train freq, equal-count thirds."""
    order = np.argsort(deg, kind="stable")
    n = len(deg)
    t1, t2 = n // 3, 2 * n // 3
    bucket = np.empty(n, dtype=np.int64)
    bucket[order[:t1]] = 0
    bucket[order[t1:t2]] = 1
    bucket[order[t2:]] = 2
    return bucket


def bucket_of(k):
    for b, (lo, hi) in enumerate(DEG_EDGES):
        if lo <= k <= hi:
            return b
    return None


def load_sidecar(path):
    rec = []
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            rec.append((int(r["target_item_id"]), float(r["ndcg10"]),
                        int(r.get("pop_bucket", -1))))
    return rec


def arm_bucket_means(paths, deg, tercile, join_check):
    """Per seed: mean ndcg10 per degree bucket. Also tercile agreement check."""
    per_seed = []
    for p in sorted(paths):
        rows = load_sidecar(p)
        acc = defaultdict(list)
        agree = total = 0
        for tgt, nd, pb in rows:
            if tgt >= len(deg):
                continue
            b = bucket_of(int(deg[tgt]))
            if b is not None:
                acc[b].append(nd)
            if pb >= 0:
                total += 1
                agree += int(tercile[tgt] == pb)
        if join_check and total:
            join_check.append(agree / total)
        per_seed.append({b: (float(np.mean(v)), len(v)) for b, v in acc.items()})
    return per_seed


def welch(a, b):
    a, b = np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64)
    va, vb = a.var(ddof=1) / len(a), b.var(ddof=1) / len(b)
    se = float(np.sqrt(va + vb))
    return float(a.mean() - b.mean()), se


def poc_a(deg, tercile):
    tpaths = [p for p in glob.glob(os.path.join(RUN, "results_TFV2_VG_text_seed*.users.jsonl.gz"))
              if ".final." not in p]
    ipaths = [p for p in glob.glob(os.path.join(RUN, "results_TFV2_VG_idonly_seed*.users.jsonl.gz"))
              if ".final." not in p]
    join_check = []
    t_seed = arm_bucket_means(tpaths, deg, tercile, join_check)
    i_seed = arm_bucket_means(ipaths, deg, tercile, join_check)
    out = {"n_text_seeds": len(t_seed), "n_id_seeds": len(i_seed),
           "tercile_join_agreement": float(np.mean(join_check)) if join_check else None,
           "note": "arms not initialization-paired (different seed ranges); "
                   "Welch across per-seed bucket means", "buckets": {}}
    for b, (lo, hi) in enumerate(DEG_EDGES):
        tv = [s[b][0] for s in t_seed if b in s]
        iv = [s[b][0] for s in i_seed if b in s]
        ns = [s[b][1] for s in t_seed if b in s]
        if len(tv) >= 2 and len(iv) >= 2:
            d, se = welch(tv, iv)
            out["buckets"][f"k{lo}-{hi}"] = {
                "text_mean": float(np.mean(tv)), "id_mean": float(np.mean(iv)),
                "delta": d, "welch_se": se,
                "rel_delta_pct": 100.0 * d / max(np.mean(iv), 1e-12),
                "n_eval_users_per_seed": float(np.mean(ns))}
    return out


def effective_embedding(sd, payload, S, n_items):
    V = sd["item_emb.weight"].numpy().astype(np.float64)[:n_items]
    E = V.copy()
    parts = {"item_emb": V}
    if "sbert_proj.weight" in sd:
        P = sd["sbert_proj.weight"].numpy().astype(np.float64)
        proj = S @ P.T
        E = E + proj
        parts["proj_text"] = proj
    # TAPE reconstruction if present
    li = 0
    while f"proto_emb.{li}.weight" in sd:
        key_a = None
        pa = payload.get("proto_assign")
        if isinstance(pa, (list, tuple)) and li < len(pa):
            key_a = pa[li]
        if key_a is None and f"proto_assign_{li}" in sd:
            key_a = sd[f"proto_assign_{li}"]
        if key_a is None:
            break
        A = key_a.numpy().astype(np.float64)[:n_items]
        Pl = sd[f"proto_emb.{li}.weight"].numpy().astype(np.float64)
        E = E + A @ Pl
        parts[f"tape_{li}"] = A @ Pl
        li += 1
    return E, V, parts


def poc_0(ckpt_path, sbert_npy, deg):
    import torch
    payload = torch.load(ckpt_path, map_location="cpu", weights_only=True)
    sd = payload["state_dict"] if "state_dict" in payload else payload
    n_items = len(deg)
    S = np.load(os.path.join(CACHE, sbert_npy)).astype(np.float64)[:n_items]
    E, V, parts = effective_embedding(sd, payload, S, n_items)
    rep = {"ckpt": os.path.basename(ckpt_path), "n_items": n_items,
           "channels": sorted(parts.keys())}
    # never-trained-row contrast: raw ID rows at k=0 vs warm
    z = deg == 0
    warm = deg >= 50
    rep["id_row_norm_k0"] = float(np.linalg.norm(V[z], axis=1).mean()) if z.any() else None
    rep["id_row_norm_warm"] = float(np.linalg.norm(V[warm], axis=1).mean())
    rep["n_deg0"] = int(z.sum())
    # diagnostics on the EFFECTIVE embedding with a cross-fitted text prior
    M = eb.fit_prior_mean(S, E, deg, warm_min=20, n_folds=5)
    rep["prior_ridge_on_effective"] = eb.precision_dependence_report(E, M, deg)
    mm = eb.fit_moment_model(E, M, deg)
    r = mm["resid2"]
    curve = []
    for lo, hi in DEG_EDGES:
        m = (deg >= lo) & (deg <= hi)
        if m.sum() >= 20:
            curve.append({"bucket": f"k{lo}-{hi}", "n": int(m.sum()),
                          "mean_resid2": float(r[m].mean())})
    rep["resid2_by_degree_effective"] = curve
    return rep


def main():
    category = "Video_Games"
    deg = item_degrees(category)
    tercile = degree_terciles(deg)
    print(f"== {category}: n_items={len(deg)} deg0={int((deg == 0).sum())} "
          f"deg<=5={int((deg <= 5).sum())} p50={int(np.median(deg))}")

    out = {"category": category,
           "degree_summary": {"n_items": int(len(deg)), "n_deg0": int((deg == 0).sum()),
                              "n_le_5": int((deg <= 5).sum()),
                              "median": int(np.median(deg)), "max": int(deg.max())}}

    print("== POC-A: TFV2 text (8 seeds) vs idonly (8 seeds), by target degree")
    out["poc_a"] = poc_a(deg, tercile)
    print(f"   tercile join agreement vs trainer pop_bucket: "
          f"{out['poc_a']['tercile_join_agreement']}")
    for kb, st in out["poc_a"]["buckets"].items():
        print(f"   {kb:>12}  text={st['text_mean']:.5f} id={st['id_mean']:.5f} "
              f"d={st['delta']:+.5f}+-{st['welch_se']:.5f} "
              f"({st['rel_delta_pct']:+.1f}%)  n~{st['n_eval_users_per_seed']:.0f}")

    print("== POC-0 v2: effective-embedding EB diagnostics (text arm)")
    ckpts = sorted(glob.glob(os.path.join(RUN, "results_VG_COLDFUSE_base_seed*.best.pt")))
    if ckpts:
        out["poc_0"] = poc_0(ckpts[0], f"sbert_titles_{category}.npy", deg)
        d = out["poc_0"]["prior_ridge_on_effective"]
        print(f"   channels: {out['poc_0']['channels']}  n_deg0={out['poc_0']['n_deg0']}")
        print(f"   ID-row norm k=0: {out['poc_0']['id_row_norm_k0']:.4f} vs warm: "
              f"{out['poc_0']['id_row_norm_warm']:.4f}")
        print(f"   spearman(k,||E||)={d['spearman_k_vs_norm']:+.3f}  "
              f"1/k-law binned R2={d['binned_r2_of_1_over_k_law']:.3f}")
        print(f"   sigma2={d['sigma2']:.5g} tau2={d['tau2_global']:.5g}  alpha(k): "
              + "  ".join(f"k={k}:{v:.2f}" for k, v in d["alpha_at_k"].items()))
        for c in out["poc_0"]["resid2_by_degree_effective"]:
            print(f"      {c['bucket']:>12}  resid2={c['mean_resid2']:.5f}  n={c['n']}")
    else:
        out["poc_0"] = {"error": "no checkpoint"}

    dst = os.path.join(OUT_DIR, "poc_coldstart_VG.json")
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print("== written:", dst)


if __name__ == "__main__":
    main()
