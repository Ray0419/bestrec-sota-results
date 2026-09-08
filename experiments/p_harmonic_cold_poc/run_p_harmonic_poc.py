"""Exploratory vector-valued p-harmonic cold-item extension.

This proof of concept is isolated from the repository's frozen campaigns.  It
asks a narrow question: after hiding an item fold, can a nonlinear p-harmonic
extension on the frozen text graph improve *within-cold* ranking over ordinary
harmonic extension and the repository's existing content/LC2C mappings?

The within-cold candidate set is intentional.  It makes the experiment immune
to a uniform warm/cold pool offset; cross-pool integration must be evaluated in
a separate mixed-target temporal protocol.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import scipy
import sklearn
from scipy.sparse import coo_matrix, csr_matrix, diags
from scipy.sparse.linalg import spsolve
from sklearn.linear_model import Ridge
from sklearn.neighbors import NearestNeighbors


ROOT = Path(__file__).resolve().parents[2]
BESTREC = ROOT / "_bestrec_run"
sys.path.insert(0, str(BESTREC))

from ease_efficient import ease_fast  # noqa: E402
from run_cold_item import DATASET_KCORE, HP, make_item_kfold  # noqa: E402
from run_poc_new_coldstart import (  # noqa: E402
    build_warm_matrix,
    load_dataset,
    normalized_embeddings,
    user_train_test,
)
from v5_utils import NUM_FOLDS  # noqa: E402


OUTPUT_DIR = Path(__file__).resolve().parent
RESULTS_PATH = OUTPUT_DIR / "results.json"
TOP_K = 10
SEED = 20260805
GRAPH_K = 10
P_VALUES = (2.0, 4.0, 8.0)
IRLS_STEPS = 12
IRLS_EPS = 1e-5


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def text_graph(embeddings: np.ndarray, k: int) -> csr_matrix:
    """Symmetric nonnegative cosine kNN graph, without self edges."""
    n_items = embeddings.shape[0]
    n_neighbors = min(k + 1, n_items)
    knn = NearestNeighbors(n_neighbors=n_neighbors, metric="cosine", algorithm="brute")
    knn.fit(embeddings)
    distances, indices = knn.kneighbors(embeddings, return_distance=True)
    rows: list[int] = []
    cols: list[int] = []
    vals: list[float] = []
    for source in range(n_items):
        for distance, target in zip(distances[source], indices[source], strict=True):
            target_int = int(target)
            if target_int == source:
                continue
            similarity = max(0.0, 1.0 - float(distance))
            if similarity <= 0.0:
                continue
            rows.append(source)
            cols.append(target_int)
            vals.append(similarity)
    directed = coo_matrix((vals, (rows, cols)), shape=(n_items, n_items), dtype=np.float64).tocsr()
    graph = directed.maximum(directed.T).tocsr()
    graph.setdiag(0.0)
    graph.eliminate_zeros()
    return graph


def harmonic_solve(
    base_graph: csr_matrix,
    warm: np.ndarray,
    cold: np.ndarray,
    warm_values: np.ndarray,
    p: float,
    max_steps: int,
) -> tuple[np.ndarray, list[float]]:
    """Hard-boundary vector p-Laplacian solve by iteratively reweighted Laplacians."""
    n_items = base_graph.shape[0]
    values = np.zeros((n_items, warm_values.shape[1]), dtype=np.float64)
    values[warm] = warm_values.astype(np.float64, copy=False)
    base_coo = base_graph.tocoo()

    def solve_with(graph: csr_matrix) -> np.ndarray:
        degree = np.asarray(graph.sum(axis=1)).ravel()
        laplacian = diags(degree, format="csr") - graph
        l_cc = laplacian[cold][:, cold].tocsr()
        l_cw = laplacian[cold][:, warm].tocsr()
        # A tiny diagonal also defines a stable zero fallback for a component
        # with no path to any warm boundary node.
        l_cc = l_cc + diags(np.full(len(cold), 1e-8), format="csr")
        return np.asarray(spsolve(l_cc, -(l_cw @ values[warm])), dtype=np.float64)

    values[cold] = solve_with(base_graph)
    changes: list[float] = []
    if p == 2.0:
        return values[cold].astype(np.float32), changes

    for _ in range(max_steps):
        differences = values[base_coo.row] - values[base_coo.col]
        squared_norm = np.einsum("ij,ij->i", differences, differences)
        multiplier = np.power(squared_norm + IRLS_EPS, (p - 2.0) / 2.0)
        reweighted = coo_matrix(
            (base_coo.data * multiplier, (base_coo.row, base_coo.col)),
            shape=base_graph.shape,
            dtype=np.float64,
        ).tocsr()
        reweighted = ((reweighted + reweighted.T) * 0.5).tocsr()
        previous = values[cold].copy()
        values[cold] = solve_with(reweighted)
        relative_change = float(
            np.linalg.norm(values[cold] - previous) / max(np.linalg.norm(previous), 1e-12)
        )
        changes.append(relative_change)
        if relative_change < 1e-5:
            break
    return values[cold].astype(np.float32), changes


def evaluate_within_cold(
    cold_scores: np.ndarray,
    cold: np.ndarray,
    train_interactions: list[dict],
    test_interactions: list[dict],
) -> tuple[dict, list[dict]]:
    user_train, user_test = user_train_test(train_interactions, test_interactions)
    cold_pos = {int(item): index for index, item in enumerate(cold)}
    rows: list[dict] = []
    for user in sorted(user_test):
        if user not in user_train:
            continue
        scores = cold_scores[user]
        for target in user_test[user]:
            target_pos = cold_pos.get(int(target))
            if target_pos is None:
                continue
            target_score = float(scores[target_pos])
            greater = int(np.sum(scores > target_score))
            tie_before = int(np.sum((scores == target_score) & (cold < int(target))))
            rank0 = greater + tie_before
            ndcg = 1.0 / math.log2(rank0 + 2) if rank0 < TOP_K else 0.0
            rows.append({"user": int(user), "target": int(target), "ndcg10": ndcg})
    values = np.asarray([row["ndcg10"] for row in rows], dtype=np.float64)
    by_user: dict[int, list[float]] = defaultdict(list)
    for row in rows:
        by_user[row["user"]].append(row["ndcg10"])
    user_values = np.asarray([np.mean(v) for v in by_user.values()], dtype=np.float64)
    return {
        "n_events": int(len(rows)),
        "n_users": int(len(by_user)),
        "event_mean_ndcg10": float(values.mean()) if len(values) else float("nan"),
        "user_mean_ndcg10": float(user_values.mean()) if len(user_values) else float("nan"),
    }, rows


def run(dataset: str) -> dict:
    interactions, _, n_users, n_items, title_embeddings = load_dataset(dataset)
    embeddings = normalized_embeddings(title_embeddings)
    graph = text_graph(embeddings, GRAPH_K)
    lam, beta = HP[dataset]
    splits = make_item_kfold(interactions, n_items, n_splits=NUM_FOLDS, seed=SEED)
    fold_records: list[dict] = []
    started = time.perf_counter()

    for fold_id, (train_ids, test_ids, cold_items) in enumerate(splits):
        train = [interactions[index] for index in train_ids]
        test = [interactions[index] for index in test_ids]
        cold = np.asarray(sorted(cold_items), dtype=np.int32)
        warm = np.asarray(sorted(set(range(n_items)) - set(cold_items)), dtype=np.int32)
        x_sparse, x_warm = build_warm_matrix(train, n_users, warm)
        warm_similarity = (embeddings[warm] @ embeddings[warm].T).astype(np.float32)
        np.fill_diagonal(warm_similarity, 0.0)
        b_warm = ease_fast(
            x_sparse,
            lam=lam,
            S_content=warm_similarity,
            beta=beta,
            dtype=np.float32,
        )

        # Existing direct ridge LC2C baseline.
        ridge = Ridge(alpha=1.0)
        ridge.fit(embeddings[warm], b_warm.T.astype(np.float32))
        lc2c_values = (embeddings[cold] @ ridge.coef_.T.astype(np.float32)).astype(np.float32)
        content_values = (embeddings[cold] @ embeddings[warm].T).astype(np.float32)

        methods: dict[str, np.ndarray] = {
            "content_direct": x_warm @ content_values.T,
            "lc2c_ridge": x_warm @ lc2c_values.T,
        }
        convergence: dict[str, list[float]] = {}
        for p in P_VALUES:
            cold_values, changes = harmonic_solve(
                graph, warm, cold, b_warm.T, p=p, max_steps=IRLS_STEPS
            )
            name = f"p_harmonic_{p:g}"
            methods[name] = x_warm @ cold_values.T
            convergence[name] = changes

        method_metrics: dict[str, dict] = {}
        method_rows: dict[str, list[dict]] = {}
        for name, scores in methods.items():
            metrics, rows = evaluate_within_cold(scores, cold, train, test)
            method_metrics[name] = metrics
            method_rows[name] = rows
        fold_records.append({
            "fold": fold_id,
            "n_warm": int(len(warm)),
            "n_cold": int(len(cold)),
            "methods": method_metrics,
            "irls_relative_changes": convergence,
        })
        print(
            f"{dataset} fold={fold_id} "
            + " ".join(
                f"{name}={metrics['event_mean_ndcg10']:.5f}"
                for name, metrics in method_metrics.items()
            ),
            flush=True,
        )

    summary: dict[str, dict] = {}
    method_names = sorted(fold_records[0]["methods"])
    for name in method_names:
        event_scores = np.asarray(
            [fold["methods"][name]["event_mean_ndcg10"] for fold in fold_records]
        )
        user_scores = np.asarray(
            [fold["methods"][name]["user_mean_ndcg10"] for fold in fold_records]
        )
        summary[name] = {
            "mean_fold_event_ndcg10": float(event_scores.mean()),
            "std_fold_event_ndcg10": float(event_scores.std()),
            "mean_fold_user_ndcg10": float(user_scores.mean()),
        }

    cache_dir = Path(ROOT) / "cache" / dataset
    k_core = DATASET_KCORE[dataset]
    return {
        "classification": "exploratory proof of concept; not confirmatory or paper-bound",
        "question": "Does p>2 vector harmonic extension improve within-cold ordering over p=2 and existing mappings?",
        "dataset": dataset,
        "seed": SEED,
        "n_users": n_users,
        "n_items": n_items,
        "n_interactions": len(interactions),
        "n_folds": NUM_FOLDS,
        "graph_k": GRAPH_K,
        "p_values": list(P_VALUES),
        "irls_steps": IRLS_STEPS,
        "runtime_seconds": float(time.perf_counter() - started),
        "summary": summary,
        "folds": fold_records,
        "evaluation_contract": "Targets and candidates are cold items only; a pool-wide offset cannot change any rank.",
        "limitations": [
            "Random item folds are a cheap mapper test, not a deployment-realistic temporal evaluation.",
            "The boundary values are EASE coefficient columns, not latent ground-truth behavior.",
            "No hyperparameter was selected on a separate validation set; this is a falsification screen only.",
        ],
        "software": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "sklearn": sklearn.__version__,
        },
        "input_sha256": {
            "raw_data_dedup.pkl": sha256(cache_dir / "raw_data_dedup.pkl"),
            "title_embeddings": sha256(cache_dir / "v5" / f"item_title_k{k_core}_dedup.pt"),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("datasets", nargs="*", default=["beauty", "fashion"])
    args = parser.parse_args()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    all_results: dict[str, dict] = {}
    for dataset in args.datasets:
        all_results[dataset] = run(dataset)
    RESULTS_PATH.write_text(json.dumps(all_results, indent=2), encoding="utf-8")
    print(f"wrote {RESULTS_PATH}")


if __name__ == "__main__":
    main()
