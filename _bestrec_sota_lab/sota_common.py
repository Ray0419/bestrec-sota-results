"""Shared isolated SOTA-lab harness.

All imports from `_bestrec_run` are read-only. All generated artifacts are
written under `_bestrec_sota_lab/runs/<run_id>/`.
"""

from __future__ import annotations

import gc
import json
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np
from scipy.sparse import csr_matrix

LAB_DIR = Path(__file__).resolve().parent
ROOT = LAB_DIR.parent
RUNS_DIR = LAB_DIR / "runs"
BESTREC_RUN_DIR = ROOT / "_bestrec_run"
sys.path.insert(0, str(BESTREC_RUN_DIR))

from artifact_utils import DATASET_LABELS, DATASET_STATS, DATASETS, append_manifest_run, machine_notes, metric_fmt, utc_now, write_json  # noqa: E402
from ease_efficient import ease_fast  # noqa: E402
from run_all_confirmatory import (  # noqa: E402
    build_warm_matrix,
    eval_full_catalog,
    make_blair_text_full,
    make_contrastive_cold_full,
    make_dropoutnet_full,
    make_lc2c_v2_full,
    make_melt_tail_transfer_full,
    make_popularity_full,
    make_run_id,
    make_z_fusion_full,
    run_warm_confirmatory_dataset,
    select_lc2cpp_weight,
    summarize_records,
)
from run_cold_item import DATASET_KCORE, HP, make_item_kfold  # noqa: E402
from run_warm_loo import warm_ranking_eval  # noqa: F401,E402
from v5_utils import NUM_FOLDS, content_sim_matrix  # noqa: E402
from run_all_confirmatory import load_dataset  # noqa: E402
from run_faithful_dropoutnet import (  # noqa: E402
    build_inference_factors as official_dropoutnet_build_inference_factors,
    make_dropoutnet_score as official_dropoutnet_make_score,
    train_item_tower as official_dropoutnet_train_item_tower,
    wmf_als as official_dropoutnet_wmf_als,
)

from lc2c_retrieval_ltr import LTRConfig, fit_retrieval_ltr, make_seen_items_by_user  # noqa: E402
from protocol import load_dropoutnet_feature_config, load_protocol, protocol_summary, strict_manifest_inputs  # noqa: E402


BASELINE_METHODS = [
    "popularity",
    "content_direct",
    "blair_text",
    "faithful_dropoutnet",
    "clcrec_contrastive",
    "melt_tail_transfer",
    "lc2c_v2",
    "lc2cpp_validated_margin",
]
LAB_CANDIDATE = "lc2c_retrieval_ltr"
LAB_METHODS = [*BASELINE_METHODS, LAB_CANDIDATE]

LAB_PROTOCOL = load_protocol()
OFFICIAL_DROPOUTNET_FEATURE_CONFIG = load_dropoutnet_feature_config(LAB_PROTOCOL)
CONFIRMATORY_SEEDS = [int(x) for x in LAB_PROTOCOL.get("fresh_confirmatory_seeds", [])]
CONFIRMATORY_SEEDS_CSV = ",".join(str(x) for x in CONFIRMATORY_SEEDS)


def parse_csv(value: str, cast: Callable[[str], Any] = str) -> list[Any]:
    return [cast(x.strip()) for x in str(value).split(",") if x.strip()]


def make_lab_run_dir(prefix: str, run_id: str | None = None) -> tuple[str, Path]:
    rid = run_id or make_run_id(prefix)
    run_dir = RUNS_DIR / rid
    run_dir.mkdir(parents=True, exist_ok=True)
    return rid, run_dir


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")


def completed_folds(path: Path, method: str = LAB_CANDIDATE) -> set[tuple[int, int]]:
    done: set[tuple[int, int]] = set()
    if not path.exists():
        return done
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if f'"method": "{method}"' not in line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            done.add((int(row["seed"]), int(row["fold_id"])))
    return done


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        if default is not None:
            return default
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def split_inner_validation(
    outer_train: list[dict[str, Any]],
    outer_cold_items: set[int],
    n_items: int,
    seed: int,
    fold_id: int,
    val_frac: float = 0.2,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], set[int], set[int]]:
    outer_warm = np.array(sorted(set(range(n_items)) - set(outer_cold_items)), dtype=np.int32)
    rng = np.random.RandomState(seed + 777 * (fold_id + 1))
    shuffled = outer_warm.copy()
    rng.shuffle(shuffled)
    val_items = set(int(x) for x in shuffled[: max(1, int(round(len(shuffled) * val_frac)))])
    inner_cold = set(outer_cold_items) | val_items
    inner_train = [x for x in outer_train if int(x["item_id"]) not in val_items]
    val_inters = [x for x in outer_train if int(x["item_id"]) in val_items]
    return inner_train, val_inters, val_items, inner_cold


def build_base_scorers(
    *,
    dataset: str,
    seed: int,
    fold_id: int,
    train_inters: list[dict[str, Any]],
    cold_items: set[int],
    interactions: list[dict[str, Any]],
    n_users: int,
    n_items: int,
    item_title_emb: Any,
    S_content: np.ndarray,
    deep_epochs_scale: float = 1.0,
    include_deep: bool = True,
    include_official_dropoutnet: bool = False,
    needed_methods: set[str] | None = None,
) -> tuple[dict[str, Callable[[np.ndarray], np.ndarray]], dict[str, Any], np.ndarray]:
    lam, beta = HP[dataset]
    needed = set(BASELINE_METHODS) if needed_methods is None else set(needed_methods)
    needed.discard(LAB_CANDIDATE)
    needed.add("content_direct")
    if "lc2cpp_validated_margin" in needed:
        needed.add("lc2c_v2")
    if include_official_dropoutnet:
        needed.add("official_dropoutnet")
    warm_indices = np.array(sorted(set(range(n_items)) - set(cold_items)), dtype=np.int32)
    cold_indices = np.array(sorted(cold_items), dtype=np.int32)
    X_sparse, Xw = build_warm_matrix(train_inters, n_users, warm_indices)
    S_warm = S_content[np.ix_(warm_indices, warm_indices)]
    B_warm = ease_fast(X_sparse, lam=lam, beta=beta, S_content=S_warm, dtype=np.float32)
    scorers: dict[str, Callable[[np.ndarray], np.ndarray]] = {}
    if "popularity" in needed:
        scorers["popularity"] = make_popularity_full(train_inters, n_items)
    if "content_direct" in needed:
        scorers["content_direct"] = _make_content_direct_full(Xw, warm_indices, S_content)
    if "blair_text" in needed:
        scorers["blair_text"] = make_blair_text_full(Xw, warm_indices, item_title_emb)
    if "lc2c_v2" in needed:
        scorers["lc2c_v2"] = make_lc2c_v2_full(Xw, B_warm, item_title_emb, warm_indices, cold_indices, n_items)
    if "melt_tail_transfer" in needed:
        scorers["melt_tail_transfer"] = make_melt_tail_transfer_full(Xw, B_warm, item_title_emb, warm_indices, cold_indices, n_items)
    selected: dict[str, Any] = {}
    if "lc2cpp_validated_margin" in needed:
        selected = select_lc2cpp_weight(
            dataset,
            seed,
            fold_id,
            train_inters,
            set(cold_items),
            interactions,
            n_users,
            n_items,
            item_title_emb,
            S_content,
            lam,
            beta,
        )
        w = float(selected.get("margin_weight", 1.0))
        scorers["lc2cpp_validated_margin"] = scorers["lc2c_v2"] if w == 1.0 else make_z_fusion_full(scorers["lc2c_v2"], scorers["content_direct"], w)
    errors: dict[str, str] = {}
    if include_deep and "faithful_dropoutnet" in needed:
        try:
            scorers["faithful_dropoutnet"] = make_dropoutnet_full(
                Xw,
                item_title_emb,
                warm_indices,
                cold_indices,
                n_items,
                seed=seed,
                epochs=max(2, int(round(80 * deep_epochs_scale))),
            )
        except Exception as exc:
            errors["faithful_dropoutnet"] = "".join(traceback.format_exception_only(type(exc), exc)).strip()
    if include_deep and "clcrec_contrastive" in needed:
        try:
            scorers["clcrec_contrastive"] = make_contrastive_cold_full(
                Xw,
                item_title_emb,
                warm_indices,
                cold_indices,
                n_items,
                seed=seed,
                epochs=max(2, int(round(60 * deep_epochs_scale))),
            )
        except Exception as exc:
            errors["clcrec_contrastive"] = "".join(traceback.format_exception_only(type(exc), exc)).strip()
    if include_official_dropoutnet or "official_dropoutnet" in needed:
        try:
            cfg = OFFICIAL_DROPOUTNET_FEATURE_CONFIG[dataset]
            sbert = item_title_emb.cpu().numpy() if hasattr(item_title_emb, "cpu") else np.asarray(item_title_emb)
            sbert = sbert.astype(np.float32)
            U_wmf, V_warm_wmf = official_dropoutnet_wmf_als(
                X_sparse,
                k=int(cfg["k"]),
                alpha=40.0,
                reg=float(cfg["reg"]),
                n_iter=max(2, int(round(50 * deep_epochs_scale))),
                seed=seed,
            )
            tower = official_dropoutnet_train_item_tower(
                V_warm_wmf,
                sbert[warm_indices],
                p_drop=float(cfg["p_drop"]),
                epochs=max(2, int(round(100 * deep_epochs_scale))),
                lr=1e-3,
                batch_size=256,
                seed=seed,
            )
            V_warm_used, V_cold_used = official_dropoutnet_build_inference_factors(
                str(cfg["mode"]),
                V_warm_wmf,
                sbert[warm_indices],
                sbert[cold_indices],
                tower,
                int(cfg["k"]),
            )
            scorers["official_dropoutnet"] = official_dropoutnet_make_score(
                U_wmf,
                V_warm_used,
                V_cold_used,
                warm_indices,
                cold_indices,
                n_items,
            )
        except Exception as exc:
            errors["official_dropoutnet"] = "".join(traceback.format_exception_only(type(exc), exc)).strip()
    user_profile_norm = np.asarray(Xw.sum(axis=1), dtype=np.float32)
    meta = {
        "warm_items": int(len(warm_indices)),
        "cold_items": int(len(cold_indices)),
        "selected_lc2cpp": selected,
        "baseline_errors": errors,
    }
    del X_sparse, B_warm, S_warm
    gc.collect()
    return scorers, meta, user_profile_norm


def run_cold_ltr_dataset(
    *,
    dataset: str,
    seeds: list[int],
    run_dir: Path,
    ltr_config: LTRConfig,
    stage: str,
    include_deep: bool = True,
    deep_epochs_scale: float = 1.0,
    max_folds: int = 0,
    resume: bool = False,
    eval_methods: list[str] | None = None,
    fold_ids: set[int] | None = None,
    max_new_folds: int = 0,
) -> dict[str, Any]:
    interactions, _, n_users, n_items, item_title_emb = load_dataset(dataset)
    S_content = content_sim_matrix(item_title_emb, dtype=np.float32)
    record_path = run_dir / f"cold_full_catalog_records_{dataset}.jsonl"
    if record_path.exists() and not resume:
        record_path.unlink()
    eval_methods = list(LAB_METHODS) if eval_methods is None else list(eval_methods)
    needed_methods = set(eval_methods)
    needed_methods.update(ltr_config.feature_methods)
    needed_methods.update(
        {
            ltr_config.validation_baseline_method,
            ltr_config.fallback_method,
            ltr_config.rerank_anchor_method,
            *ltr_config.rerank_anchor_methods,
            "content_direct",
        }
    )
    needed_methods.discard("")
    already_done = completed_folds(record_path) if resume else set()
    method_stats: dict[str, dict[str, float]] = {
        m: {"ndcg10_sum": 0.0, "hr10_sum": 0.0, "rr_sum": 0.0, "n_records": 0.0}
        for m in eval_methods
    }
    fold_meta: list[dict[str, Any]] = []
    baseline_errors: dict[str, list[str]] = {}
    new_folds_run = 0
    for seed in seeds:
        splits = make_item_kfold(interactions, n_items, n_splits=NUM_FOLDS, seed=seed)
        indexed_splits = list(enumerate(splits))
        if fold_ids is not None:
            indexed_splits = [(fold_id, split) for fold_id, split in indexed_splits if fold_id in fold_ids]
        elif max_folds:
            indexed_splits = indexed_splits[:max_folds]
        for fold_id, (tr_idx, te_idx, cold_items) in indexed_splits:
            if (seed, fold_id) in already_done:
                print(f"{stage} {dataset} seed={seed} fold={fold_id}: already complete; skipping")
                continue
            if max_new_folds and new_folds_run >= max_new_folds:
                break
            t0 = time.time()
            outer_train = [interactions[i] for i in tr_idx]
            outer_test = [interactions[i] for i in te_idx]
            print(f"{stage} {dataset} seed={seed} fold={fold_id}: full catalog, cold_items={len(cold_items):,}")
            inner_train, val_inters, _, inner_cold = split_inner_validation(outer_train, set(cold_items), n_items, seed, fold_id)
            inner_scorers, inner_meta, inner_profile = build_base_scorers(
                dataset=dataset,
                seed=seed,
                fold_id=fold_id,
                train_inters=inner_train,
                cold_items=inner_cold,
                interactions=interactions,
                n_users=n_users,
                n_items=n_items,
                item_title_emb=item_title_emb,
                S_content=S_content,
                deep_epochs_scale=deep_epochs_scale,
                include_deep=include_deep,
                include_official_dropoutnet="official_dropoutnet" in needed_methods,
                needed_methods=needed_methods,
            )
            ltr = fit_retrieval_ltr(
                base_scorers=inner_scorers,
                content_scorer=inner_scorers["content_direct"],
                train_inters=inner_train,
                validation_inters=val_inters,
                n_items=n_items,
                seed=seed,
                config=ltr_config,
                eval_full_catalog=eval_full_catalog,
                dataset=dataset,
                fold_id=fold_id,
                user_profile_norm=inner_profile,
            )
            outer_scorers, outer_meta, outer_profile = build_base_scorers(
                dataset=dataset,
                seed=seed,
                fold_id=fold_id,
                train_inters=outer_train,
                cold_items=set(cold_items),
                interactions=interactions,
                n_users=n_users,
                n_items=n_items,
                item_title_emb=item_title_emb,
                S_content=S_content,
                deep_epochs_scale=deep_epochs_scale,
                include_deep=include_deep,
                include_official_dropoutnet="official_dropoutnet" in needed_methods,
                needed_methods=needed_methods,
            )
            for name, err in outer_meta.get("baseline_errors", {}).items():
                baseline_errors.setdefault(name, []).append(f"seed={seed} fold={fold_id}: {err}")
            outer_scorers[LAB_CANDIDATE] = ltr.make_score_fn(
                outer_scorers,
                outer_scorers["content_direct"],
                n_items,
                outer_profile,
                seen_items_by_user=make_seen_items_by_user(outer_train),
            )
            for method in eval_methods:
                if method not in outer_scorers:
                    continue
                result, rows = eval_full_catalog(dataset, seed, fold_id, method, outer_scorers[method], outer_train, outer_test, n_items)
                append_jsonl(record_path, rows)
                stats = method_stats[method]
                stats["ndcg10_sum"] += float(result["NDCG@10"]) * len(rows)
                stats["hr10_sum"] += float(result["HR@10"]) * len(rows)
                stats["rr_sum"] += float(result["MRR"]) * len(rows)
                stats["n_records"] += len(rows)
                print(f"  {method:<26} NDCG@10={result['NDCG@10']:.5f} n={len(rows)}")
            fold_meta.append(
                {
                    "dataset": dataset,
                    "seed": seed,
                    "fold_id": fold_id,
                    "ltr_metadata": ltr.metadata,
                    "inner_meta": inner_meta,
                    "outer_meta": outer_meta,
                    "elapsed_seconds": time.time() - t0,
                }
            )
            new_folds_run += 1
            gc.collect()
        if max_new_folds and new_folds_run >= max_new_folds:
            break
    return {
        "dataset": dataset,
        "stage": stage,
        "candidate_scope": "full_catalog",
        "n_users": n_users,
        "n_items": n_items,
        "k_core": DATASET_KCORE[dataset],
        "record_file": record_path.name,
        "methods": {
            m: {
                "NDCG@10": (s["ndcg10_sum"] / s["n_records"]) if s["n_records"] else None,
                "HR@10": (s["hr10_sum"] / s["n_records"]) if s["n_records"] else None,
                "MRR": (s["rr_sum"] / s["n_records"]) if s["n_records"] else None,
                "n_records": int(s["n_records"]),
            }
            for m, s in method_stats.items()
        },
        "fold_meta": fold_meta,
        "fold_ids_requested": sorted(fold_ids) if fold_ids is not None else None,
        "max_new_folds": int(max_new_folds),
        "new_folds_run": int(new_folds_run),
        "baseline_errors": baseline_errors,
        "ltr_config": ltr_config.to_json(),
    }


def run_warm_records(datasets: list[str], seeds: list[int], run_dir: Path) -> dict[str, Any]:
    warm: dict[str, Any] = {}
    for dataset in datasets:
        warm[dataset] = run_warm_confirmatory_dataset(dataset, seeds, run_dir)
    return warm


def write_run_config(run_dir: Path, payload: dict[str, Any]) -> None:
    write_json(
        run_dir / "run_config.json",
        {
            "schema_version": 1,
            "machine": machine_notes(),
            "created_utc": utc_now(),
            "protocol": protocol_summary(LAB_PROTOCOL),
            "dropoutnet_feature_config": OFFICIAL_DROPOUTNET_FEATURE_CONFIG,
            **payload,
        },
    )


def write_manifest(run_dir: Path, command: list[str], datasets: list[str], seeds: list[int], outputs: list[Path], note: str) -> None:
    manifest = append_manifest_run(
        command=command,
        inputs=strict_manifest_inputs(run_dir, datasets),
        outputs=outputs,
        datasets=datasets,
        seeds=seeds,
        note=note,
        manifest_path=run_dir / "results_manifest.json",
    )
    latest = manifest.get("runs", [])[-1] if manifest.get("runs") else {}
    manifest["latest_run"] = {
        "timestamp_utc": latest.get("timestamp_utc"),
        "command": latest.get("command", []),
        "datasets": latest.get("datasets", []),
        "seeds": latest.get("seeds", []),
        "input_hash_count": len(latest.get("input_hashes", {})),
        "output_hashes": latest.get("output_hashes", {}),
        "machine": latest.get("machine", {}),
        "note": latest.get("note", note),
    }
    write_json(run_dir / "results_manifest.json", manifest)


def _make_content_direct_full(Xw: np.ndarray, warm_indices: np.ndarray, S_content: np.ndarray) -> Callable[[np.ndarray], np.ndarray]:
    S_w_all = S_content[warm_indices, :].astype(np.float32)

    def score(user_ids: np.ndarray) -> np.ndarray:
        return Xw[user_ids] @ S_w_all

    return score
