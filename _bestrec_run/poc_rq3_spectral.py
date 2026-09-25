# -*- coding: utf-8 -*-
"""RQ3: bias-vs-variance decomposition of cold rows + degree-aware spectral
denoising, on trained tables. CPU/numpy, no eval pass (diagnostic stage).

Stage (a) diagnose: is the low-degree row error a BIAS (systematic shift, e.g.
suppression by negative sampling) or VARIANCE (noise ~ sigma^2/k)? Uses the
5 same-config COLDFUSE seeds as an ensemble: for each item row, across-seed
mean (after orthogonal Procrustes alignment to a reference seed) = the stable
component; across-seed scatter = variance. Then measure, per degree bucket:
  - across-seed variance  (should fall like 1/k if the textbook model holds)
  - alignment of the seed-mean row with the global "suppression axis"
    (the mean direction of k<=2 rows) = the bias signature.

Stage (b) correct (spectral): compare homoscedastic Gavish-Donoho shrinkage
(the documented-failed GD1 control) against degree-whitened shrinkage on the
reconstruction of held-out warm rows -- a proxy risk that needs no eval pass.
"""
import glob
import json
import os

import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
MAIN_RUN = r"C:\Users\rayxc\Documents\R\_bestrec_run"
OUT = os.path.join(HERE, "poc_out")
os.makedirs(OUT, exist_ok=True)
DEG_EDGES = [(0, 0), (1, 2), (3, 5), (6, 10), (11, 20), (21, 50), (51, 150),
             (151, 500), (501, 10 ** 9)]


def item_degrees_from_split(category="Video_Games"):
    import csv
    with open(os.path.join(r"C:\Users\rayxc\Documents\R\cache_5core",
                           f"asin2idx_{category}.json"), encoding="utf-8") as f:
        asin2idx = json.load(f)
    n_items = max(asin2idx.values()) + 1
    deg = np.zeros(n_items, dtype=np.int64)
    with open(os.path.join(r"C:\Users\rayxc\Documents\R\data_5core\5core\last_out",
                           f"{category}.train.csv"), encoding="utf-8", newline="") as f:
        rdr = csv.reader(f)
        hdr = next(rdr)
        ii = hdr.index("parent_asin")
        for row in rdr:
            idx = asin2idx.get(row[ii])
            if idx is not None:
                deg[idx] += 1
    return deg


def load_tables(pattern, n_items):
    out = []
    for p in sorted(glob.glob(pattern)):
        sd = torch.load(p, map_location="cpu", weights_only=False)["state_dict"]
        out.append((os.path.basename(p),
                    sd["item_emb.weight"].numpy().astype(np.float64)[:n_items]))
    return out


def procrustes(A, B, w=None):
    """Orthogonal R minimizing ||A R - B||_F (optionally weighted by w rows)."""
    if w is not None:
        A = A * w[:, None]
        B = B * w[:, None]
    U, _, Vt = np.linalg.svd(A.T @ B)
    return U @ Vt


def gd_shrink(S, beta):
    """Gavish-Donoho optimal shrinker with the median-based noise estimate
    (mirrors the trainer's GD1 code path)."""
    omega = 0.56 * beta ** 3 - 0.95 * beta ** 2 + 1.82 * beta + 1.43
    tau = omega * np.median(S)
    y = S / max(tau / (1.0 + np.sqrt(beta)), 1e-12)
    out = np.zeros_like(S)
    ok = y > 1.0 + np.sqrt(beta)
    yo = y[ok]
    out[ok] = np.sqrt(np.maximum((yo ** 2 - beta - 1) ** 2 - 4 * beta, 0.0)) / yo
    return out * (tau / (1.0 + np.sqrt(beta))), tau


def main():
    deg = item_degrees_from_split()
    n_items = len(deg)
    tabs = load_tables(os.path.join(MAIN_RUN, "results_VG_COLDFUSE_base_seed*.best.pt"),
                       n_items)
    print(f"loaded {len(tabs)} VG tables; n_items={n_items}")
    ref = tabs[0][1]
    warm = deg >= 21
    aligned = [ref]
    for name, T in tabs[1:]:
        R = procrustes(T, ref, w=(warm.astype(np.float64)))
        aligned.append(T @ R)
    A = np.stack(aligned, axis=0)                    # (S, N, d)
    mean_row = A.mean(axis=0)
    var_row = ((A - mean_row[None]) ** 2).sum(axis=2).mean(axis=0)   # per item

    # suppression axis: mean direction of very-low-degree rows (post-alignment)
    low = (deg >= 1) & (deg <= 2)
    sup = mean_row[low].mean(axis=0)
    sup = sup / max(np.linalg.norm(sup), 1e-12)
    warm_mu = mean_row[warm].mean(axis=0)

    rep = {"n_seeds": len(tabs), "buckets": []}
    print(f"\n{'bucket':>12} {'n':>6} {'across-seed var':>16} {'||mean row||':>13} "
          f"{'proj on sup-axis':>17} {'cos(row, warm_mu)':>18}")
    for lo, hi in DEG_EDGES:
        m = (deg >= lo) & (deg <= hi)
        if m.sum() < 20:
            continue
        rows = mean_row[m]
        nrm = np.linalg.norm(rows, axis=1)
        proj = rows @ sup
        cos_warm = (rows @ warm_mu) / (nrm * np.linalg.norm(warm_mu) + 1e-12)
        b = {"bucket": f"k{lo}-{hi}", "n": int(m.sum()),
             "across_seed_var": float(var_row[m].mean()),
             "mean_norm": float(nrm.mean()),
             "proj_on_suppression_axis": float(proj.mean()),
             "cos_to_warm_mean": float(cos_warm.mean())}
        rep["buckets"].append(b)
        print(f"{b['bucket']:>12} {b['n']:>6} {b['across_seed_var']:>16.6f} "
              f"{b['mean_norm']:>13.4f} {b['proj_on_suppression_axis']:>17.4f} "
              f"{b['cos_to_warm_mean']:>18.4f}")

    # bias vs variance ratio: how much of the low-k row is the shared (bias)
    # component vs seed-specific scatter
    print("\nbias/variance split (low-k rows):")
    for lo, hi in ((1, 2), (3, 5), (6, 10), (21, 50), (151, 500)):
        m = (deg >= lo) & (deg <= hi)
        if m.sum() < 20:
            continue
        shared = (mean_row[m] ** 2).sum(axis=1).mean()
        scatter = var_row[m].mean()
        print(f"  k{lo}-{hi:<4} shared^2={shared:.5f}  scatter={scatter:.5f}  "
              f"shared/(shared+scatter)={shared/(shared+scatter):.3f}")
        for b in rep["buckets"]:
            if b["bucket"] == f"k{lo}-{hi}":
                b["shared_sq"] = float(shared)
                b["shared_frac"] = float(shared / (shared + scatter))

    # (b) spectral: hold out warm rows, compare denoisers by reconstruction of
    # the seed-mean (the "true" row proxy) from a single seed's table
    single = aligned[0]
    target = mean_row
    d = single.shape[1]
    res_spec = {}
    for mode in ("none", "gd_homo", "gd_whitened"):
        X = single.copy()
        if mode != "none":
            w = np.ones(n_items)
            if mode == "gd_whitened":
                kk = np.maximum(deg, 1).astype(np.float64)
                w = np.sqrt(kk / kk.mean())
            Xw = X * w[:, None]
            U, S, Vt = np.linalg.svd(Xw, full_matrices=False)
            beta = d / n_items
            S2, tau = gd_shrink(S, beta)
            X = ((U * S2) @ Vt) / w[:, None]
        err = ((X - target) ** 2).sum(axis=1)
        res_spec[mode] = {"overall": float(err.mean())}
        for lo, hi in ((1, 2), (3, 5), (6, 10), (21, 50)):
            m = (deg >= lo) & (deg <= hi)
            res_spec[mode][f"k{lo}-{hi}"] = float(err[m].mean())
    rep["spectral_recon_err"] = res_spec
    print("\nreconstruction error vs seed-mean (lower is better):")
    hdr = ["overall", "k1-2", "k3-5", "k6-10", "k21-50"]
    print(f"{'mode':>13} " + " ".join(f"{h:>10}" for h in hdr))
    for mode, r in res_spec.items():
        print(f"{mode:>13} " + " ".join(f"{r[h]:>10.5f}" for h in hdr))

    dst = os.path.join(OUT, "rq3_spectral_diag.json")
    json.dump(rep, open(dst, "w", encoding="utf-8"), indent=1)
    print(f"\nwrote {dst}")


if __name__ == "__main__":
    main()
