"""Exploratory Temporal-LC2C proof of concept on timestamped All_Beauty.

This script is intentionally isolated from every frozen campaign. It writes only
under ``_bestrec_run/poc_temporal_lc2c_v1`` and never reads a sealed endpoint.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import pickle
import platform
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import scipy
import sklearn
import torch
from scipy.sparse import csr_matrix
from sklearn.linear_model import Ridge

from ease_efficient import ease_fast


ROOT = Path(__file__).resolve().parent.parent
SPLIT_DIR = ROOT / "data_5core" / "5core" / "last_out"
OUTPUT_DIR = ROOT / "_bestrec_run" / "poc_temporal_lc2c_v1"
DATASET = "All_Beauty"
INNER_Q = 0.60
OUTER_Q = 0.75
KERNEL_WIDTH = 8
RIDGE_ALPHA = 1.0
EASE_LAMBDA = 100.0
EASE_BETA = 10.0
TOP_K = 10
BOOTSTRAP_REPS = 2000
SEED = 20260801


@dataclass(frozen=True)
class Event:
    user: int
    item: int
    timestamp: int


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_timestamped_catalog() -> tuple[list[Event], list[str], list[str]]:
    raw_rows: list[tuple[str, str, int]] = []
    paths: list[Path] = []
    for split in ("train", "valid", "test"):
        path = SPLIT_DIR / f"{DATASET}.{split}.csv"
        paths.append(path)
        with path.open("r", encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                raw_rows.append((row["user_id"], row["parent_asin"], int(row["timestamp"])))

    users = sorted({row[0] for row in raw_rows})
    items = sorted({row[1] for row in raw_rows})
    user_to_idx = {value: idx for idx, value in enumerate(users)}
    item_to_idx = {value: idx for idx, value in enumerate(items)}
    events = [Event(user_to_idx[u], item_to_idx[i], timestamp) for u, i, timestamp in raw_rows]
    events.sort(key=lambda row: (row.timestamp, row.user, row.item))
    return events, users, items


def load_matching_title_embeddings(items: list[str]) -> np.ndarray:
    cache_dir = ROOT / "cache" / "beauty"
    with (cache_dir / "raw_data_dedup.pkl").open("rb") as handle:
        legacy = pickle.load(handle)
    legacy_item_to_id = legacy["item2id"]
    missing = sorted(set(items) - set(legacy_item_to_id))
    if missing:
        raise RuntimeError(f"{len(missing)} All_Beauty items lack cached embeddings")

    embedding_path = cache_dir / "v5" / "item_title_k5_dedup.pt"
    cached = torch.load(embedding_path, map_location="cpu", weights_only=True).numpy().astype(np.float32)
    cache_order = sorted(items, key=lambda asin: int(legacy_item_to_id[asin]))
    if cached.shape[0] != len(cache_order):
        raise RuntimeError(
            f"embedding/catalog mismatch: {cached.shape[0]} rows versus {len(cache_order)} items"
        )
    cache_pos = {asin: idx for idx, asin in enumerate(cache_order)}
    aligned = cached[[cache_pos[asin] for asin in items]]
    norms = np.linalg.norm(aligned, axis=1, keepdims=True)
    return aligned / np.maximum(norms, 1e-12)


def first_times(events: list[Event], n_items: int) -> np.ndarray:
    values = np.full(n_items, np.iinfo(np.int64).max, dtype=np.int64)
    for event in events:
        values[event.item] = min(values[event.item], event.timestamp)
    return values


def quantile_cutoff(events: list[Event], quantile: float) -> int:
    times = np.asarray([event.timestamp for event in events], dtype=np.int64)
    return int(np.quantile(times, quantile, method="nearest"))


def make_kernel(decay: float | None) -> np.ndarray:
    if decay is None:
        return np.ones(KERNEL_WIDTH, dtype=np.float32)
    taps = np.power(np.float32(decay), np.arange(KERNEL_WIDTH, dtype=np.float32))
    return taps * (KERNEL_WIDTH / taps.sum())


KERNELS = {
    "boxcar8": make_kernel(None),
    "exp050": make_kernel(0.50),
    "exp070": make_kernel(0.70),
    "exp085": make_kernel(0.85),
    "exp095": make_kernel(0.95),
}


def ndcg_from_rank(rank0: int) -> float:
    return 1.0 / math.log2(rank0 + 2) if rank0 < TOP_K else 0.0


def deterministic_rank(scores: np.ndarray, candidate_ids: np.ndarray, target: int) -> int:
    target_pos = int(np.flatnonzero(candidate_ids == target)[0])
    target_score = float(scores[target_pos])
    greater = int(np.sum(scores > target_score))
    tie_before = int(np.sum((scores == target_score) & (candidate_ids < target)))
    return greater + tie_before


class StageModel:
    def __init__(
        self,
        events: list[Event],
        embeddings: np.ndarray,
        cutoff: int,
        stage_end: int | None,
    ) -> None:
        self.events = events
        self.embeddings = embeddings
        self.cutoff = cutoff
        self.stage_end = stage_end
        self.n_items = embeddings.shape[0]
        self.first = first_times(events, self.n_items)
        self.warm = np.flatnonzero(self.first <= cutoff).astype(np.int32)
        cold_mask = self.first > cutoff
        if stage_end is not None:
            cold_mask &= self.first <= stage_end
        self.cold = np.flatnonzero(cold_mask).astype(np.int32)
        self.warm_pos = {int(item): idx for idx, item in enumerate(self.warm)}
        self.cold_pos = {int(item): idx for idx, item in enumerate(self.cold)}

        train = [event for event in events if event.timestamp <= cutoff and event.item in self.warm_pos]
        rows = np.asarray([event.user for event in train], dtype=np.int32)
        cols = np.asarray([self.warm_pos[event.item] for event in train], dtype=np.int32)
        vals = np.ones(len(train), dtype=np.float32)
        n_users = max(event.user for event in events) + 1
        matrix = csr_matrix((vals, (rows, cols)), shape=(n_users, len(self.warm)))
        warm_similarity = (embeddings[self.warm] @ embeddings[self.warm].T).astype(np.float32)
        np.fill_diagonal(warm_similarity, 0.0)
        self.b_warm = ease_fast(
            matrix,
            lam=EASE_LAMBDA,
            S_content=warm_similarity,
            beta=EASE_BETA,
            dtype=np.float32,
        )

        ridge = Ridge(alpha=RIDGE_ALPHA)
        ridge.fit(embeddings[self.warm], self.b_warm.T.astype(np.float32))
        self.b_cold = (
            embeddings[self.cold] @ ridge.coef_.T.astype(np.float32)
        ).T.astype(np.float32)
        self.s_content_cold = (
            embeddings[self.warm] @ embeddings[self.cold].T
        ).astype(np.float32)

        histories: dict[int, list[Event]] = defaultdict(list)
        for event in events:
            histories[event.user].append(event)
        self.histories = histories

    def target_events(self) -> list[Event]:
        output: list[Event] = []
        cold_set = set(map(int, self.cold))
        for event in self.events:
            if event.timestamp <= self.cutoff or event.item not in cold_set:
                continue
            if self.stage_end is not None and event.timestamp > self.stage_end:
                continue
            prior = [row for row in self.histories[event.user] if row.timestamp < event.timestamp]
            if event.item in {row.item for row in prior}:
                continue
            if not any(row.item in self.warm_pos for row in prior):
                continue
            output.append(event)
        return output

    def history_vector(self, event: Event, kernel: np.ndarray) -> tuple[np.ndarray, set[int]]:
        prior_all = [row for row in self.histories[event.user] if row.timestamp < event.timestamp]
        prior_warm = [row.item for row in prior_all if row.item in self.warm_pos]
        recent = list(reversed(prior_warm[-len(kernel) :]))
        vector = np.zeros(len(self.warm), dtype=np.float32)
        for lag, item in enumerate(recent):
            vector[self.warm_pos[item]] += kernel[lag]
        return vector, {row.item for row in prior_all}

    def score_event(self, event: Event, kernel: np.ndarray) -> dict[str, dict[str, float]]:
        x, seen = self.history_vector(event, kernel)
        warm_scores = x @ self.b_warm
        lc2c_cold = x @ self.b_cold
        content_cold = x @ self.s_content_cold

        available_cold_mask = self.first[self.cold] <= event.timestamp
        available_cold = self.cold[available_cold_mask]
        if event.item not in set(map(int, available_cold)):
            raise RuntimeError("target is absent from its availability-aware cold pool")
        cold_positions = np.flatnonzero(available_cold_mask)
        cold_candidate_mask = np.asarray([int(item) not in seen for item in available_cold])
        cold_candidates = available_cold[cold_candidate_mask]
        selected_positions = cold_positions[cold_candidate_mask]

        warm_candidate_mask = np.asarray([int(item) not in seen for item in self.warm])
        warm_candidates = self.warm[warm_candidate_mask]
        warm_values = warm_scores[warm_candidate_mask]

        output: dict[str, dict[str, float]] = {}
        for method, cold_values_all in (("content", content_cold), ("lc2c", lc2c_cold)):
            cold_values = cold_values_all[selected_positions]
            cold_rank = deterministic_rank(cold_values, cold_candidates, event.item)

            raw_ids = np.concatenate([warm_candidates, cold_candidates])
            raw_scores = np.concatenate([warm_values, cold_values])
            raw_rank = deterministic_rank(raw_scores, raw_ids, event.item)

            available_values = cold_values_all[cold_positions]
            cold_mean = float(available_values.mean())
            cold_std = float(available_values.std())
            warm_mean = float(warm_scores.mean())
            warm_std = float(warm_scores.std())
            if cold_std < 1e-8:
                calibrated = np.full_like(cold_values, warm_mean)
            else:
                calibrated = (cold_values - cold_mean) / cold_std * warm_std + warm_mean
            pzc_scores = np.concatenate([warm_values, calibrated])
            pzc_rank = deterministic_rank(pzc_scores, raw_ids, event.item)

            output[method] = {
                "cold_ndcg10": ndcg_from_rank(cold_rank),
                "cold_rank": cold_rank + 1,
                "raw_full_ndcg10": ndcg_from_rank(raw_rank),
                "raw_full_rank": raw_rank + 1,
                "pzc_full_ndcg10": ndcg_from_rank(pzc_rank),
                "pzc_full_rank": pzc_rank + 1,
                "n_cold_candidates": int(len(cold_candidates)),
                "n_full_candidates": int(len(raw_ids)),
            }
        return output


def evaluate_stage(model: StageModel, kernels: dict[str, np.ndarray]) -> list[dict]:
    rows: list[dict] = []
    for event in model.target_events():
        record: dict = {
            "user": event.user,
            "item": event.item,
            "timestamp": event.timestamp,
        }
        for kernel_name, kernel in kernels.items():
            scored = model.score_event(event, kernel)
            for method, metrics in scored.items():
                for metric, value in metrics.items():
                    record[f"{method}_{kernel_name}_{metric}"] = value
        rows.append(record)
    return rows


def mean_metric(rows: list[dict], key: str) -> float:
    return float(np.mean([float(row[key]) for row in rows])) if rows else float("nan")


def aggregate_by_user(rows: list[dict], key: str) -> dict[int, float]:
    values: dict[int, list[float]] = defaultdict(list)
    for row in rows:
        values[int(row["user"])].append(float(row[key]))
    return {user: float(np.mean(user_values)) for user, user_values in values.items()}


def user_mean_metric(rows: list[dict], key: str) -> float:
    values = aggregate_by_user(rows, key)
    return float(np.mean(list(values.values()))) if values else float("nan")


def bootstrap_contrast(
    rows: list[dict],
    positive_key: str,
    negative_key: str,
    rng: np.random.Generator,
) -> dict:
    positive = aggregate_by_user(rows, positive_key)
    negative = aggregate_by_user(rows, negative_key)
    users = np.asarray(sorted(set(positive) & set(negative)), dtype=np.int32)
    differences = np.asarray([positive[int(user)] - negative[int(user)] for user in users])
    boot = np.empty(BOOTSTRAP_REPS, dtype=np.float64)
    for rep in range(BOOTSTRAP_REPS):
        sampled = rng.integers(0, len(users), size=len(users))
        boot[rep] = float(differences[sampled].mean())
    return {
        "n_users": int(len(users)),
        "mean": float(differences.mean()),
        "ci95_user_bootstrap": [float(np.quantile(boot, 0.025)), float(np.quantile(boot, 0.975))],
        "positive_user_fraction": float(np.mean(differences > 0)),
    }


def bootstrap_interaction(rows: list[dict], endpoint: str, selected: str, rng: np.random.Generator) -> dict:
    keys = {
        "lc_fir": f"lc2c_{selected}_{endpoint}",
        "lc_box": f"lc2c_boxcar8_{endpoint}",
        "cd_fir": f"content_{selected}_{endpoint}",
        "cd_box": f"content_boxcar8_{endpoint}",
    }
    by_key = {name: aggregate_by_user(rows, key) for name, key in keys.items()}
    users = np.asarray(sorted(set.intersection(*(set(value) for value in by_key.values()))), dtype=np.int32)
    values = np.asarray([
        (by_key["lc_fir"][int(user)] - by_key["lc_box"][int(user)])
        - (by_key["cd_fir"][int(user)] - by_key["cd_box"][int(user)])
        for user in users
    ])
    boot = np.empty(BOOTSTRAP_REPS, dtype=np.float64)
    for rep in range(BOOTSTRAP_REPS):
        sampled = rng.integers(0, len(users), size=len(users))
        boot[rep] = float(values[sampled].mean())
    return {
        "n_users": int(len(users)),
        "mean": float(values.mean()),
        "ci95_user_bootstrap": [float(np.quantile(boot, 0.025)), float(np.quantile(boot, 0.975))],
    }


def main() -> None:
    if (ROOT / "PAUSE_EXPERIMENTS").exists():
        raise SystemExit("PAUSE_EXPERIMENTS is present; refusing to run")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    events, users, items = load_timestamped_catalog()
    embeddings = load_matching_title_embeddings(items)
    inner_cutoff = quantile_cutoff(events, INNER_Q)
    outer_cutoff = quantile_cutoff(events, OUTER_Q)

    inner = StageModel(events, embeddings, cutoff=inner_cutoff, stage_end=outer_cutoff)
    inner_rows = evaluate_stage(inner, KERNELS)
    if not inner_rows:
        raise RuntimeError("no eligible inner-development cold targets")

    kernel_scores = {}
    for name in KERNELS:
        content = mean_metric(inner_rows, f"content_{name}_cold_ndcg10")
        lc2c = mean_metric(inner_rows, f"lc2c_{name}_cold_ndcg10")
        kernel_scores[name] = {
            "content_cold_ndcg10": content,
            "lc2c_cold_ndcg10": lc2c,
            "selection_mean": (content + lc2c) / 2.0,
        }
    selected = max(
        (name for name in KERNELS if name != "boxcar8"),
        key=lambda name: (kernel_scores[name]["selection_mean"], name),
    )

    outer = StageModel(events, embeddings, cutoff=outer_cutoff, stage_end=None)
    outer_rows = evaluate_stage(outer, {"boxcar8": KERNELS["boxcar8"], selected: KERNELS[selected]})
    if not outer_rows:
        raise RuntimeError("no eligible outer cold targets")

    endpoints = ("cold_ndcg10", "raw_full_ndcg10", "pzc_full_ndcg10")
    event_weighted_arm_means = {}
    user_weighted_arm_means = {}
    for method in ("content", "lc2c"):
        for kernel in ("boxcar8", selected):
            arm = f"{method}_{kernel}"
            event_weighted_arm_means[arm] = {
                endpoint: mean_metric(outer_rows, f"{arm}_{endpoint}") for endpoint in endpoints
            }
            user_weighted_arm_means[arm] = {
                endpoint: user_mean_metric(outer_rows, f"{arm}_{endpoint}") for endpoint in endpoints
            }

    rng = np.random.default_rng(SEED)
    contrasts = {}
    for endpoint in endpoints:
        contrasts[endpoint] = {
            "lc2c_fir_minus_boxcar": bootstrap_contrast(
                outer_rows,
                f"lc2c_{selected}_{endpoint}",
                f"lc2c_boxcar8_{endpoint}",
                rng,
            ),
            "content_fir_minus_boxcar": bootstrap_contrast(
                outer_rows,
                f"content_{selected}_{endpoint}",
                f"content_boxcar8_{endpoint}",
                rng,
            ),
            "factorial_interaction": bootstrap_interaction(outer_rows, endpoint, selected, rng),
        }

    first = first_times(events, len(items))
    input_paths = [SPLIT_DIR / f"{DATASET}.{split}.csv" for split in ("train", "valid", "test")]
    input_paths.extend([
        ROOT / "cache" / "beauty" / "raw_data_dedup.pkl",
        ROOT / "cache" / "beauty" / "v5" / "item_title_k5_dedup.pt",
    ])
    payload = {
        "classification": "exploratory proof of concept; not confirmatory or paper-bound",
        "dataset": DATASET,
        "n_users": len(users),
        "n_items": len(items),
        "n_events": len(events),
        "inner_quantile": INNER_Q,
        "inner_cutoff": inner_cutoff,
        "outer_quantile": OUTER_Q,
        "outer_cutoff": outer_cutoff,
        "inner_n_warm_items": int(len(inner.warm)),
        "inner_n_cold_items": int(len(inner.cold)),
        "inner_n_events": len(inner_rows),
        "outer_n_warm_items": int(np.sum(first <= outer_cutoff)),
        "outer_n_cold_items": int(np.sum(first > outer_cutoff)),
        "outer_n_events": len(outer_rows),
        "outer_n_users": len({int(row["user"]) for row in outer_rows}),
        "kernel_width": KERNEL_WIDTH,
        "kernel_taps": {name: [float(value) for value in taps] for name, taps in KERNELS.items()},
        "kernel_selection": kernel_scores,
        "selected_kernel": selected,
        "outer_event_weighted_arm_means": event_weighted_arm_means,
        "outer_user_weighted_arm_means": user_weighted_arm_means,
        "outer_contrasts": contrasts,
        "feasibility_rule": {
            "cold_pool_improves": contrasts["cold_ndcg10"]["lc2c_fir_minus_boxcar"]["mean"] > 0,
            "pzc_full_improves": contrasts["pzc_full_ndcg10"]["lc2c_fir_minus_boxcar"]["mean"] > 0,
            "cold_pool_interaction_positive": contrasts["cold_ndcg10"]["factorial_interaction"]["mean"] > 0,
            "interpretation": "directional only; no confirmatory threshold was preregistered",
        },
        "software": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "sklearn": sklearn.__version__,
            "torch": torch.__version__,
        },
        "input_sha256": {str(path.relative_to(ROOT)): file_sha256(path) for path in input_paths},
        "script_sha256": file_sha256(Path(__file__)),
    }

    summary_path = OUTPUT_DIR / "results.json"
    records_path = OUTPUT_DIR / "outer_records.jsonl"
    summary_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    with records_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in outer_rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")

    print(json.dumps({
        "selected_kernel": selected,
        "inner_events": len(inner_rows),
        "outer_events": len(outer_rows),
        "outer_users": payload["outer_n_users"],
        "outer_event_weighted_arm_means": event_weighted_arm_means,
        "outer_user_weighted_arm_means": user_weighted_arm_means,
        "outer_contrasts": contrasts,
        "feasibility_rule": payload["feasibility_rule"],
        "results": str(summary_path),
        "records": str(records_path),
    }, indent=2))


if __name__ == "__main__":
    main()
