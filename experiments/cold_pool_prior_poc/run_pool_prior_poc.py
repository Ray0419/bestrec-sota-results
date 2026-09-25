"""Exploratory audit of warm/cold pool-prior identifiability.

This script is deliberately isolated from the repository's frozen campaigns.  It
uses the timestamped All_Beauty data and the existing EASE/LC2C machinery, but
writes only inside ``experiments/cold_pool_prior_poc``.

The central intervention leaves every within-pool ordering unchanged.  It varies
only the prior probability assigned to the event that the next target belongs to
the post-cutoff (new-item) pool.  If a cold-target-only metric can be improved by
that intervention while warm-target utility falls, cross-pool calibration is not
identified by the cold-only benchmark.
"""
from __future__ import annotations

import hashlib
import json
import math
import platform
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterable

import numpy as np
import scipy
import sklearn


ROOT = Path(__file__).resolve().parents[2]
BESTREC = ROOT / "_bestrec_run"
sys.path.insert(0, str(BESTREC))

from run_poc_temporal_lc2c_v1 import (  # noqa: E402
    DATASET,
    KERNELS,
    OUTER_Q,
    SEED,
    SPLIT_DIR,
    Event,
    StageModel,
    file_sha256,
    load_matching_title_embeddings,
    load_timestamped_catalog,
    quantile_cutoff,
)


OUTPUT_DIR = Path(__file__).resolve().parent
RESULTS_PATH = OUTPUT_DIR / "results.json"
RECORDS_PATH = OUTPUT_DIR / "outer_records.jsonl"
INNER_Q = 0.60
TOP_K = 10
BOOTSTRAP_REPS = 2_000
ALPHA_GRID = (0.0, 0.25, 0.5, 0.75, 1.0)
TEMPERATURE_GRID = (0.25, 0.5, 1.0, 2.0, 4.0)
PRIOR_SWEEP = (0.001, 0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99, 0.999)
# A dense log-spaced validation grid avoids making the safety decision hinge on
# the coarse reporting grid above.  Only the selected value is evaluated on the
# outer window.
PRIOR_SELECTION_GRID = tuple(float(value) for value in np.geomspace(0.001, 0.25, 81))
WARM_RETENTION_FLOOR = 0.90


def stable_log_softmax(values: np.ndarray, temperature: float) -> np.ndarray:
    scaled = values.astype(np.float64, copy=False) / float(temperature)
    peak = float(np.max(scaled))
    shifted = scaled - peak
    return shifted - math.log(float(np.exp(shifted).sum()))


def standardize(values: np.ndarray) -> np.ndarray:
    values64 = values.astype(np.float64, copy=False)
    scale = float(values64.std())
    if scale < 1e-10:
        return np.zeros_like(values64)
    return (values64 - float(values64.mean())) / scale


def deterministic_rank(scores: np.ndarray, item_ids: np.ndarray, target: int) -> int:
    target_positions = np.flatnonzero(item_ids == target)
    if len(target_positions) != 1:
        raise RuntimeError(f"target {target} appears {len(target_positions)} times")
    target_score = float(scores[int(target_positions[0])])
    return int(np.sum(scores > target_score) + np.sum((scores == target_score) & (item_ids < target)))


def ndcg10(rank0: int) -> float:
    return 1.0 / math.log2(rank0 + 2) if rank0 < TOP_K else 0.0


def eligible_events(model: StageModel) -> list[Event]:
    output: list[Event] = []
    for event in model.events:
        if event.timestamp <= model.cutoff:
            continue
        if model.stage_end is not None and event.timestamp > model.stage_end:
            continue
        # Cross-pool calibration is defined only after at least one post-cutoff
        # item is available.  This condition depends on query time, not on the
        # target's pool label.
        if not np.any(model.first[model.cold] <= event.timestamp):
            continue
        prior = [row for row in model.histories[event.user] if row.timestamp < event.timestamp]
        if event.item in {row.item for row in prior}:
            continue
        if not any(row.item in model.warm_pos for row in prior):
            continue
        output.append(event)
    return output


def candidate_signals(
    model: StageModel,
    event: Event,
    alpha: float,
) -> dict[str, np.ndarray | bool | int]:
    history, seen = model.history_vector(event, KERNELS["boxcar8"])
    warm_raw_all = history @ model.b_warm
    lc2c_raw_all = history @ model.b_cold
    content_raw_all = history @ model.s_content_cold

    warm_keep = np.asarray([int(item) not in seen for item in model.warm], dtype=bool)
    available_cold = model.first[model.cold] <= event.timestamp
    cold_keep = available_cold & np.asarray([int(item) not in seen for item in model.cold], dtype=bool)

    warm_ids = model.warm[warm_keep]
    cold_ids = model.cold[cold_keep]
    warm_raw = warm_raw_all[warm_keep].astype(np.float64)
    lc2c_raw = lc2c_raw_all[cold_keep].astype(np.float64)
    content_raw = content_raw_all[cold_keep].astype(np.float64)
    if not len(warm_ids) or not len(cold_ids):
        raise RuntimeError("both candidate pools must be non-empty")

    target_is_cold = int(event.item) in model.cold_pos
    target_pool = cold_ids if target_is_cold else warm_ids
    if int(event.item) not in set(map(int, target_pool)):
        raise RuntimeError("eligible target is absent from its candidate pool")

    warm_z = standardize(warm_raw)
    lc2c_z = standardize(lc2c_raw)
    content_z = standardize(content_raw)
    cold_blend_z = float(alpha) * content_z + (1.0 - float(alpha)) * lc2c_z

    return {
        "warm_ids": warm_ids,
        "cold_ids": cold_ids,
        "warm_raw": warm_raw,
        "lc2c_raw": lc2c_raw,
        "content_raw": content_raw,
        "warm_z": warm_z,
        "cold_blend_z": cold_blend_z,
        "target_is_cold": target_is_cold,
        "target": int(event.item),
    }


def hierarchical_scores(
    signals: dict[str, np.ndarray | bool | int],
    cold_prior: float,
    temperature: float,
) -> tuple[np.ndarray, np.ndarray]:
    prior = min(max(float(cold_prior), 1e-9), 1.0 - 1e-9)
    warm_ids = np.asarray(signals["warm_ids"])
    cold_ids = np.asarray(signals["cold_ids"])
    warm_lp = stable_log_softmax(np.asarray(signals["warm_z"]), temperature) + math.log1p(-prior)
    cold_lp = stable_log_softmax(np.asarray(signals["cold_blend_z"]), temperature) + math.log(prior)
    return np.concatenate([warm_ids, cold_ids]), np.concatenate([warm_lp, cold_lp])


def raw_scores(
    signals: dict[str, np.ndarray | bool | int],
    cold_source: str,
) -> tuple[np.ndarray, np.ndarray]:
    warm_ids = np.asarray(signals["warm_ids"])
    cold_ids = np.asarray(signals["cold_ids"])
    return (
        np.concatenate([warm_ids, cold_ids]),
        np.concatenate([np.asarray(signals["warm_raw"]), np.asarray(signals[cold_source])]),
    )


def cdr_scores(signals: dict[str, np.ndarray | bool | int]) -> tuple[np.ndarray, np.ndarray]:
    warm_ids = np.asarray(signals["warm_ids"])
    cold_ids = np.asarray(signals["cold_ids"])
    return (
        np.concatenate([warm_ids, cold_ids]),
        np.concatenate([np.asarray(signals["warm_raw"]), np.asarray(signals["cold_blend_z"])]),
    )


def evaluate_config(
    model: StageModel,
    events: Iterable[Event],
    alpha: float,
    temperature: float,
    cold_prior: float,
) -> float:
    values: list[float] = []
    for event in events:
        signals = candidate_signals(model, event, alpha)
        ids, scores = hierarchical_scores(signals, cold_prior, temperature)
        values.append(ndcg10(deterministic_rank(scores, ids, int(event.item))))
    return float(np.mean(values)) if values else float("nan")


def evaluate_inner_strata(
    model: StageModel,
    events: Iterable[Event],
    alpha: float,
    temperature: float,
    cold_prior: float | None,
) -> dict[str, float]:
    values: dict[str, list[float]] = {"all": [], "cold": [], "warm": []}
    for event in events:
        signals = candidate_signals(model, event, alpha)
        if cold_prior is None:
            ids, scores = raw_scores(signals, "lc2c_raw")
        else:
            ids, scores = hierarchical_scores(signals, cold_prior, temperature)
        value = ndcg10(deterministic_rank(scores, ids, int(event.item)))
        pool = "cold" if bool(signals["target_is_cold"]) else "warm"
        values["all"].append(value)
        values[pool].append(value)
    return {
        stratum: float(np.mean(stratum_values)) if stratum_values else float("nan")
        for stratum, stratum_values in values.items()
    }


def empirical_cold_prior(model: StageModel, events: Iterable[Event]) -> float:
    labels = [int(event.item) in model.cold_pos for event in events]
    if not labels:
        raise RuntimeError("cannot estimate a pool prior from zero events")
    return float(np.mean(labels))


def select_config(model: StageModel, events: list[Event], prior: float) -> tuple[float, float, list[dict]]:
    trials: list[dict] = []
    for alpha in ALPHA_GRID:
        for temperature in TEMPERATURE_GRID:
            score = evaluate_config(model, events, alpha, temperature, prior)
            trials.append({
                "alpha": float(alpha),
                "temperature": float(temperature),
                "overall_ndcg10": score,
            })
    best = max(trials, key=lambda row: (row["overall_ndcg10"], -row["temperature"], -row["alpha"]))
    return float(best["alpha"]), float(best["temperature"]), trials


def mean_by_user(rows: list[dict], method: str, stratum: str) -> dict[int, float]:
    grouped: dict[int, list[float]] = defaultdict(list)
    for row in rows:
        if stratum != "all" and row["target_pool"] != stratum:
            continue
        grouped[int(row["user"])].append(float(row[method]))
    return {user: float(np.mean(values)) for user, values in grouped.items()}


def summarize_method(rows: list[dict], method: str, rng: np.random.Generator) -> dict:
    output: dict[str, dict] = {}
    for stratum in ("all", "cold", "warm"):
        user_values = mean_by_user(rows, method, stratum)
        values = np.asarray(list(user_values.values()), dtype=np.float64)
        if not len(values):
            output[stratum] = {"n_users": 0, "user_mean_ndcg10": float("nan")}
            continue
        boot = np.empty(BOOTSTRAP_REPS, dtype=np.float64)
        for rep in range(BOOTSTRAP_REPS):
            boot[rep] = float(values[rng.integers(0, len(values), size=len(values))].mean())
        event_values = [
            float(row[method])
            for row in rows
            if stratum == "all" or row["target_pool"] == stratum
        ]
        output[stratum] = {
            "n_events": len(event_values),
            "n_users": len(values),
            "event_mean_ndcg10": float(np.mean(event_values)),
            "user_mean_ndcg10": float(values.mean()),
            "user_bootstrap_ci95": [
                float(np.quantile(boot, 0.025)),
                float(np.quantile(boot, 0.975)),
            ],
        }
    return output


def summarize_contrast(
    rows: list[dict],
    positive: str,
    negative: str,
    rng: np.random.Generator,
) -> dict:
    output: dict[str, dict] = {}
    for stratum in ("all", "cold", "warm"):
        positive_users = mean_by_user(rows, positive, stratum)
        negative_users = mean_by_user(rows, negative, stratum)
        users = sorted(set(positive_users) & set(negative_users))
        differences = np.asarray(
            [positive_users[user] - negative_users[user] for user in users],
            dtype=np.float64,
        )
        boot = np.empty(BOOTSTRAP_REPS, dtype=np.float64)
        for rep in range(BOOTSTRAP_REPS):
            boot[rep] = float(
                differences[rng.integers(0, len(differences), size=len(differences))].mean()
            )
        event_differences = [
            float(row[positive]) - float(row[negative])
            for row in rows
            if stratum == "all" or row["target_pool"] == stratum
        ]
        output[stratum] = {
            "n_events": len(event_differences),
            "n_users": len(users),
            "event_mean_difference": float(np.mean(event_differences)),
            "user_mean_difference": float(differences.mean()),
            "user_bootstrap_ci95": [
                float(np.quantile(boot, 0.025)),
                float(np.quantile(boot, 0.975)),
            ],
            "positive_user_fraction": float(np.mean(differences > 0)),
        }
    return output


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    if (ROOT / "PAUSE_EXPERIMENTS").exists():
        raise SystemExit("PAUSE_EXPERIMENTS is present; refusing to run")

    events, users, items = load_timestamped_catalog()
    embeddings = load_matching_title_embeddings(items)
    inner_cutoff = quantile_cutoff(events, INNER_Q)
    outer_cutoff = quantile_cutoff(events, OUTER_Q)

    inner_model = StageModel(events, embeddings, cutoff=inner_cutoff, stage_end=outer_cutoff)
    inner_events = eligible_events(inner_model)
    inner_prior = empirical_cold_prior(inner_model, inner_events)
    selected_alpha, selected_temperature, selection_trials = select_config(
        inner_model,
        inner_events,
        inner_prior,
    )
    inner_raw_lc2c = evaluate_inner_strata(
        inner_model,
        inner_events,
        selected_alpha,
        selected_temperature,
        None,
    )
    warm_floor = WARM_RETENTION_FLOOR * inner_raw_lc2c["warm"]
    safe_prior_trials: list[dict] = []
    for prior in PRIOR_SELECTION_GRID:
        metrics = evaluate_inner_strata(
            inner_model,
            inner_events,
            selected_alpha,
            selected_temperature,
            prior,
        )
        safe_prior_trials.append({
            "cold_prior": float(prior),
            "overall_ndcg10": metrics["all"],
            "cold_ndcg10": metrics["cold"],
            "warm_ndcg10": metrics["warm"],
            "warm_retention": (
                metrics["warm"] / inner_raw_lc2c["warm"]
                if inner_raw_lc2c["warm"] > 0
                else float("nan")
            ),
            "passes_warm_floor": bool(metrics["warm"] >= warm_floor),
        })
    feasible_priors = [row for row in safe_prior_trials if row["passes_warm_floor"]]
    if not feasible_priors:
        raise RuntimeError("no pool prior satisfies the validation warm-retention floor")
    selected_safe_prior = float(max(
        feasible_priors,
        key=lambda row: (row["cold_ndcg10"], row["overall_ndcg10"], -row["cold_prior"]),
    )["cold_prior"])

    outer_model = StageModel(events, embeddings, cutoff=outer_cutoff, stage_end=None)
    outer_events = eligible_events(outer_model)
    outer_prior = empirical_cold_prior(outer_model, outer_events)
    rows: list[dict] = []
    for event in outer_events:
        signals = candidate_signals(outer_model, event, selected_alpha)
        target = int(event.item)
        target_pool = "cold" if bool(signals["target_is_cold"]) else "warm"

        record: dict = {
            "user": int(event.user),
            "item": target,
            "timestamp": int(event.timestamp),
            "target_pool": target_pool,
            "n_warm_candidates": int(len(np.asarray(signals["warm_ids"]))),
            "n_cold_candidates": int(len(np.asarray(signals["cold_ids"]))),
        }
        for method, source in (
            ("raw_content", "content_raw"),
            ("raw_lc2c", "lc2c_raw"),
        ):
            ids, scores = raw_scores(signals, source)
            record[method] = ndcg10(deterministic_rank(scores, ids, target))

        ids, scores = cdr_scores(signals)
        record["cdr_z"] = ndcg10(deterministic_rank(scores, ids, target))

        for method, prior in (
            ("hier_inner_prior", inner_prior),
            ("hier_equal_prior", 0.5),
            ("hier_outer_oracle_prior", outer_prior),
            ("hier_warm_safe_prior", selected_safe_prior),
        ):
            ids, scores = hierarchical_scores(signals, prior, selected_temperature)
            record[method] = ndcg10(deterministic_rank(scores, ids, target))

        pool_ids = np.asarray(signals["cold_ids"] if target_pool == "cold" else signals["warm_ids"])
        pool_scores = np.asarray(
            signals["cold_blend_z"] if target_pool == "cold" else signals["warm_z"]
        )
        record["within_target_pool_ndcg10"] = ndcg10(
            deterministic_rank(pool_scores, pool_ids, target)
        )

        for prior in PRIOR_SWEEP:
            ids, scores = hierarchical_scores(signals, prior, selected_temperature)
            record[f"hier_prior_{prior:.3f}"] = ndcg10(deterministic_rank(scores, ids, target))
        rows.append(record)

    rng = np.random.default_rng(SEED)
    main_methods = (
        "raw_content",
        "raw_lc2c",
        "cdr_z",
        "hier_inner_prior",
        "hier_equal_prior",
        "hier_outer_oracle_prior",
        "hier_warm_safe_prior",
        "within_target_pool_ndcg10",
    )
    summaries = {method: summarize_method(rows, method, rng) for method in main_methods}
    paired_contrasts = {
        "hier_warm_safe_prior_minus_raw_lc2c": summarize_contrast(
            rows,
            "hier_warm_safe_prior",
            "raw_lc2c",
            rng,
        ),
        "cdr_z_minus_raw_lc2c": summarize_contrast(rows, "cdr_z", "raw_lc2c", rng),
        "raw_content_minus_raw_lc2c": summarize_contrast(
            rows,
            "raw_content",
            "raw_lc2c",
            rng,
        ),
    }
    prior_sweep = {
        f"{prior:.3f}": summarize_method(rows, f"hier_prior_{prior:.3f}", rng)
        for prior in PRIOR_SWEEP
    }

    input_paths = [SPLIT_DIR / f"{DATASET}.{split}.csv" for split in ("train", "valid", "test")]
    input_paths.extend([
        ROOT / "cache" / "beauty" / "raw_data_dedup.pkl",
        ROOT / "cache" / "beauty" / "v5" / "item_title_k5_dedup.pt",
    ])
    payload = {
        "classification": "exploratory proof of concept; not confirmatory or paper-bound",
        "question": (
            "Can cold-target-only full-catalog NDCG be changed by a pool-prior offset "
            "that leaves all within-warm and within-cold rankings unchanged?"
        ),
        "dataset": DATASET,
        "n_users": len(users),
        "n_items": len(items),
        "n_events": len(events),
        "inner_quantile": INNER_Q,
        "inner_cutoff": inner_cutoff,
        "outer_quantile": OUTER_Q,
        "outer_cutoff": outer_cutoff,
        "inner_n_events": len(inner_events),
        "inner_n_cold_targets": int(sum(int(event.item) in inner_model.cold_pos for event in inner_events)),
        "inner_empirical_cold_prior": inner_prior,
        "outer_n_events": len(outer_events),
        "outer_n_cold_targets": int(sum(row["target_pool"] == "cold" for row in rows)),
        "outer_empirical_cold_prior": outer_prior,
        "selected_alpha": selected_alpha,
        "selected_temperature": selected_temperature,
        "warm_retention_floor": WARM_RETENTION_FLOOR,
        "inner_raw_lc2c_metrics": inner_raw_lc2c,
        "selected_warm_safe_prior": selected_safe_prior,
        "warm_safe_prior_trials": safe_prior_trials,
        "selection_trials": selection_trials,
        "method_summaries": summaries,
        "paired_contrasts": paired_contrasts,
        "prior_sweep": prior_sweep,
        "invariance_contract": (
            "Only the additive log pool prior changes across prior_sweep; candidate sets and all "
            "within-pool scores, ranks, temperatures, and blend weights are identical."
        ),
        "limitations": [
            "Catalog availability is proxied by an item's first observed interaction timestamp.",
            "All_Beauty is small; this is a directional proof of concept, not a generalization claim.",
            "The outer empirical prior is an outcome-visible oracle comparator and is not deployable.",
            "Histories use the last eight pre-cutoff-warm items to match the earlier temporal LC2C POC.",
        ],
        "software": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "sklearn": sklearn.__version__,
        },
        "input_sha256": {str(path.relative_to(ROOT)): file_sha256(path) for path in input_paths},
        "script_sha256": sha256(Path(__file__)),
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    with RECORDS_PATH.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")

    compact = {
        "inner_prior": inner_prior,
        "outer_prior": outer_prior,
        "selected_alpha": selected_alpha,
        "selected_temperature": selected_temperature,
        "selected_warm_safe_prior": selected_safe_prior,
        "outer_events": len(outer_events),
        "outer_cold_targets": payload["outer_n_cold_targets"],
        "method_summaries": summaries,
        "paired_contrasts": paired_contrasts,
        "prior_sweep": prior_sweep,
        "results": str(RESULTS_PATH),
        "records": str(RECORDS_PATH),
    }
    print(json.dumps(compact, indent=2))


if __name__ == "__main__":
    main()
