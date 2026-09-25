"""POC core for RESEARCH_QUESTIONS_COLDSTART.md (RQ1/RQ3).

Path-free estimator math, numpy-only, so it can be wired to any checkpoint /
prototype / split layout once known. Three pieces:

  1. fit_prior_mean       - cross-fitted (ridge / WLS) text->embedding prior m(x_i)
                            (covariate-powered EB, Ignatiadis-Wager style)
  2. fit_moment_model     - method-of-moments fit of E||v_i - m_i||^2/d = tau^2 + sigma^2/k_i,
                            with a CLOSE-style per-degree-bin tau^2(k) upgrade
                            (Chen, Econometrica 2026: precision may predict parameters)
  3. posterior_map        - v_post = alpha * v + (1-alpha) * m,  alpha = tau^2/(tau^2 + sigma^2/k)
                            (k=0 -> pure text prior; no special case)
  4. whitened_spectral_shrink - RQ3: row-whiten by sqrt(k), Gavish-Donoho-style optimal
                            singular-value shrinkage on the whitened matrix, unwhiten.
                            (POC stand-in for eOptShrink; homoscedastic GD on the raw
                            table is the documented-failed GD1 control.)

All functions take/return float64 numpy arrays. No repo imports.
"""
from __future__ import annotations

import numpy as np


# ---------------------------------------------------------------------------
# 1. cross-fitted covariate prior  m(x_i)
# ---------------------------------------------------------------------------

def fit_prior_mean(T, V, k, warm_min=20, n_folds=5, ridge=1e-2, precision_weight=True,
                   seed=0):
    """Cross-fitted ridge prediction of embedding rows from text features.

    T: (N, d_t) text features (e.g. prototype vectors), V: (N, d) trained table,
    k: (N,) train degree. Fit only on warm items (k >= warm_min), but predict m
    for ALL items with the fold-held-out model (items outside every training
    subset - i.e. cold items - are predicted by the fold model they were
    assigned to, which never saw any item's fold-mates' rows).

    Returns M: (N, d) prior means.
    """
    T = np.asarray(T, dtype=np.float64)
    V = np.asarray(V, dtype=np.float64)
    k = np.asarray(k, dtype=np.float64)
    N, d_t = T.shape
    rng = np.random.default_rng(seed)
    fold = rng.integers(0, n_folds, size=N)
    M = np.empty_like(V)
    # bias column
    Tb = np.concatenate([T, np.ones((N, 1))], axis=1)
    for f in range(n_folds):
        tr = (fold != f) & (k >= warm_min)
        if tr.sum() < d_t + 1:  # degenerate fold: fall back to all warm items
            tr = (k >= warm_min)
        w = k[tr] if precision_weight else np.ones(tr.sum())
        Xw = Tb[tr] * np.sqrt(w)[:, None]
        Yw = V[tr] * np.sqrt(w)[:, None]
        A = Xw.T @ Xw + ridge * np.trace(Xw.T @ Xw) / Xw.shape[1] * np.eye(Xw.shape[1])
        W = np.linalg.solve(A, Xw.T @ Yw)          # (d_t+1, d)
        M[fold == f] = Tb[fold == f] @ W
    return M


# ---------------------------------------------------------------------------
# 2. moment model  E r_i = tau^2 + sigma^2 / k_i   (+ CLOSE-style binned tau)
# ---------------------------------------------------------------------------

def fit_moment_model(V, M, k, n_bins=8, k_min_fit=1):
    """Return dict with sigma2 (global), tau2_global, and tau2_of_k (per-item).

    Global fit: WLS of r_i on [1, 1/k_i] over items with k_i >= k_min_fit.
    CLOSE-lite: within log-degree bins b, tau2_b = max(mean_b(r) - sigma2 *
    mean_b(1/k), floor); per-item tau2 = bin value (piecewise-constant tau^2(k)).
    """
    V = np.asarray(V, dtype=np.float64)
    M = np.asarray(M, dtype=np.float64)
    k = np.asarray(k, dtype=np.float64)
    d = V.shape[1]
    r = ((V - M) ** 2).sum(axis=1) / d
    use = k >= k_min_fit
    X = np.stack([np.ones(use.sum()), 1.0 / k[use]], axis=1)
    # plain LS is fine at POC scale; guard against negative estimates
    beta, *_ = np.linalg.lstsq(X, r[use], rcond=None)
    tau2_global = max(float(beta[0]), 1e-12)
    sigma2 = max(float(beta[1]), 1e-12)

    # CLOSE-lite binned tau^2(k)
    tau2_i = np.full(V.shape[0], tau2_global)
    kk = k[use]
    edges = np.quantile(np.log1p(kk), np.linspace(0, 1, n_bins + 1))
    edges[-1] += 1e-9
    which = np.digitize(np.log1p(k), edges) - 1
    for b in range(n_bins):
        m_b = use & (which == b)
        if m_b.sum() >= 30:
            t2 = float(r[m_b].mean() - sigma2 * (1.0 / k[m_b]).mean())
            tau2_i[which == b] = max(t2, 1e-12)
    return {"sigma2": sigma2, "tau2_global": tau2_global, "tau2_i": tau2_i, "resid2": r}


def posterior_map(V, M, k, sigma2, tau2_i):
    """alpha_i = tau2_i / (tau2_i + sigma2/k_i); k=0 -> alpha=0 (pure prior)."""
    V = np.asarray(V, dtype=np.float64)
    M = np.asarray(M, dtype=np.float64)
    k = np.asarray(k, dtype=np.float64)
    tau2_i = np.broadcast_to(np.asarray(tau2_i, dtype=np.float64), (V.shape[0],))
    with np.errstate(divide="ignore"):
        noise = np.where(k > 0, sigma2 / np.maximum(k, 1e-12), np.inf)
    alpha = np.where(np.isinf(noise), 0.0, tau2_i / (tau2_i + noise))
    return alpha[:, None] * V + (1.0 - alpha[:, None]) * M, alpha


# ---------------------------------------------------------------------------
# 3. RQ3: whitened optimal singular-value shrinkage (POC version)
# ---------------------------------------------------------------------------

def _gd_shrink_singular_values(s, beta, noise_sigma):
    """Optimal (Frobenius) shrinker for known noise level (Gavish-Donoho 2017 form).

    y = s / (noise_sigma * sqrt(max_dim)); values below bulk edge (1+sqrt(beta))
    -> 0; above: eta(y) = sqrt((y^2-beta-1)^2 - 4*beta) / y, rescaled back.
    """
    edge = 1.0 + np.sqrt(beta)
    y = s / noise_sigma
    out = np.zeros_like(s)
    ok = y > edge
    yo = y[ok]
    out[ok] = noise_sigma * np.sqrt(np.maximum((yo ** 2 - beta - 1.0) ** 2 - 4.0 * beta, 0.0)) / yo
    return out


def spectral_shrink(V, k=None, mode="whitened"):
    """Denoise the table by singular-value shrinkage.

    mode='raw'      : homoscedastic GD on V (the documented-failed GD1 control)
    mode='whitened' : rows scaled by sqrt(k_i / mean_k) first (heteroscedastic
                      noise -> approx homoscedastic), shrink, unscale.
    Noise level estimated from the median singular value (robust MP-median rule).
    Rows with k=0 are passed through untouched in whitened mode (no ID signal
    to denoise; posterior_map handles them instead).
    """
    V = np.asarray(V, dtype=np.float64)
    N, d = V.shape
    if mode == "whitened":
        if k is None:
            raise ValueError("whitened mode needs k")
        k = np.asarray(k, dtype=np.float64)
        pos = k > 0
        w = np.ones(N)
        w[pos] = np.sqrt(k[pos] / k[pos].mean())
        Vw = V * w[:, None]
    else:
        pos = np.ones(N, dtype=bool)
        w = np.ones(N)
        Vw = V
    U, s, Vt = np.linalg.svd(Vw[pos], full_matrices=False)
    n_eff = pos.sum()
    beta = d / n_eff if n_eff >= d else n_eff / d
    # median-based noise estimate: median singular value vs MP median
    mp_median = np.sqrt(n_eff) * (1.0 + np.sqrt(beta)) * 0.55  # coarse POC constant
    noise_sigma = np.median(s) / max(mp_median, 1e-12) * np.sqrt(n_eff)
    # normalize: work in units where noise singular values ~ sqrt(n_eff)*sigma_unit
    s_shr = _gd_shrink_singular_values(s, beta, noise_sigma)
    Vd = np.array(V, copy=True)
    Vd[pos] = (U * s_shr) @ Vt / w[pos, None]
    return Vd


# ---------------------------------------------------------------------------
# 4. POC-0 diagnostics
# ---------------------------------------------------------------------------

def precision_dependence_report(V, M, k):
    """Returns the POC-0 numbers: does degree predict the parameter (CLOSE premise),
    and does the 1/k moment law hold?

    - spearman(k, ||v||): precision-parameter dependence (Chen premise)
    - R^2 of r_i ~ 1/k_i on binned means: the heteroscedastic noise law
    """
    def _spearman(a, b):
        ra = np.argsort(np.argsort(a)).astype(np.float64)
        rb = np.argsort(np.argsort(b)).astype(np.float64)
        ra -= ra.mean(); rb -= rb.mean()
        return float((ra * rb).sum() / np.sqrt((ra ** 2).sum() * (rb ** 2).sum()))

    V = np.asarray(V, dtype=np.float64)
    k = np.asarray(k, dtype=np.float64)
    norms = np.linalg.norm(V, axis=1)
    rho_norm, p_norm = _spearman(k, norms), float("nan")
    mm = fit_moment_model(V, M, k)
    r = mm["resid2"]
    # binned check of linearity in 1/k
    use = k >= 1
    q = np.quantile(1.0 / k[use], np.linspace(0, 1, 13))
    q[-1] += 1e-12
    idx = np.digitize(1.0 / k[use], q) - 1
    xs, ys = [], []
    for b in range(12):
        m_b = idx == b
        if m_b.sum() >= 30:
            xs.append((1.0 / k[use])[m_b].mean())
            ys.append(r[use][m_b].mean())
    xs, ys = np.array(xs), np.array(ys)
    if len(xs) >= 3:
        A = np.stack([np.ones_like(xs), xs], axis=1)
        beta, *_ = np.linalg.lstsq(A, ys, rcond=None)
        pred = A @ beta
        ss_res = ((ys - pred) ** 2).sum()
        ss_tot = ((ys - ys.mean()) ** 2).sum()
        r2 = 1.0 - ss_res / max(ss_tot, 1e-30)
    else:
        r2 = float("nan")
    return {
        "spearman_k_vs_norm": float(rho_norm),
        "spearman_p": float(p_norm),
        "binned_r2_of_1_over_k_law": float(r2),
        "sigma2": mm["sigma2"],
        "tau2_global": mm["tau2_global"],
        "alpha_at_k": {int(kk): float(mm["tau2_global"] / (mm["tau2_global"] + mm["sigma2"] / kk))
                        for kk in (1, 2, 5, 10, 50, 200)},
    }
