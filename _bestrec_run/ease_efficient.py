"""Efficient EASE for large item catalogs.

Uses:
- Sparse X for storage
- float32 for in-memory matrices
- scipy.linalg.cho_solve for symmetric positive-definite Gram (fast)
- Block-wise scoring to avoid materializing full (n_users x n_items) score matrix
"""
import numpy as np
from scipy.sparse import csr_matrix
from scipy.linalg import cho_factor, cho_solve, solve


def ease_fast(X_sparse, lam, S_content=None, beta=0.0, dtype=np.float32):
    """Closed-form EASE using Cholesky decomposition.

    Args:
        X_sparse: scipy.sparse.csr_matrix (n_users, n_items)
        lam: L2 regularization (acts like ridge)
        S_content: dense (n_items, n_items) content similarity, or None
        beta: weight of content similarity
        dtype: float32 saves memory at minor numeric cost

    Returns:
        B: dense (n_items, n_items) item-item similarity matrix (float32)
    """
    # X^T X via sparse multiply -> dense (n_items, n_items)
    G = (X_sparse.T @ X_sparse).toarray().astype(dtype)
    if beta > 0 and S_content is not None:
        G += dtype(beta) * S_content.astype(dtype, copy=False)
    n_items = G.shape[0]
    G += dtype(lam) * np.eye(n_items, dtype=dtype)

    # Cholesky: G = L L^T -> P = G^-1.
    # When S_content is added to G with high beta, G can become indefinite
    # (cosine sim has negative eigenvalues with zero diagonal). Fall back to LU.
    try:
        c, low = cho_factor(G, lower=True, check_finite=False)
        P = cho_solve((c, low), np.eye(n_items, dtype=dtype), check_finite=False)
    except np.linalg.LinAlgError:
        try:
            P = solve(G, np.eye(n_items, dtype=dtype), assume_a='gen', check_finite=False)
        except np.linalg.LinAlgError:
            # Last resort: pseudo-inverse (slower)
            P = np.linalg.pinv(G).astype(dtype)

    diagP = np.diag(P).copy()
    diagP[np.abs(diagP) < 1e-12] = 1e-12
    B = -P / diagP[None, :]
    np.fill_diagonal(B, 0.0)
    return B


def score_users(X_sparse, B, user_ids):
    """Score a set of users against all items.

    scores[k] = X[user_ids[k]] @ B
    """
    # X_sparse is (n_users, n_items); B is (n_items, n_items)
    # We want scores: (len(user_ids), n_items)
    Xu = X_sparse[user_ids]      # sparse (len(user_ids), n_items)
    return (Xu @ B).astype(np.float32)
