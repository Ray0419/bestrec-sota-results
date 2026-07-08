"""Generate the manuscript data-processing appendix from local artifacts."""

from __future__ import annotations

import json
import pickle
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
BESTREC_RUN = ROOT / "_bestrec_run"
LAB = ROOT / "_bestrec_sota_lab"
sys.path.insert(0, str(BESTREC_RUN))
sys.path.insert(0, str(LAB))

from artifact_utils import DATASET_LABELS, DATASETS  # noqa: E402
from preprocess_5core_standard import CATEGORIES  # noqa: E402
from run_cold_item import DATASET_KCORE, make_item_kfold  # noqa: E402
from v5_utils import kcore_filter, reindex  # noqa: E402


RUN_ID = "full_clean_rebuild_confirmatory_masked_candidate_20260701_20260705"
CANONICAL_RUN_ID = "confirmatory_masked_candidate_20260701_20260705_candidate_only"
RUN_DIR = LAB / "runs" / RUN_ID
PAPER = LAB / "paper_draft" / "lc2c_retrieval_ltr_paper.md"
OUT_MD = LAB / "paper_draft" / "data_processing_appendix.md"
OUT_JSON = LAB / "paper_draft" / "data_processing_appendix.json"

START = "<!-- DATA_PROCESSING_APPENDIX:START -->"
END = "<!-- DATA_PROCESSING_APPENDIX:END -->"

CATEGORY_BY_DATASET = {
    "beauty": "All_Beauty",
    "fashion": "Amazon_Fashion",
    "instruments": "Musical_Instruments",
    "books": "Books",
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def fmt(value: int | float | str | None) -> str:
    if value is None:
        return "-"
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def fold_count_summary(fold_counts: dict[str, int]) -> dict[str, Any]:
    values = [int(v) for v in fold_counts.values()]
    return {
        "seed_fold_count": len(values),
        "total": int(sum(values)),
        "min": int(min(values)),
        "max": int(max(values)),
    }


def split_summary(interactions: list[dict[str, Any]], n_items: int, seeds: list[int]) -> dict[str, Any]:
    cold_counts: list[int] = []
    train_counts: list[int] = []
    test_counts: list[int] = []
    for seed in seeds:
        for train_idx, test_idx, cold_items in make_item_kfold(interactions, n_items, seed=seed):
            cold_counts.append(len(cold_items))
            train_counts.append(len(train_idx))
            test_counts.append(len(test_idx))
    return {
        "seed_fold_count": len(cold_counts),
        "cold_items_min": min(cold_counts),
        "cold_items_max": max(cold_counts),
        "train_interactions_min": min(train_counts),
        "train_interactions_max": max(train_counts),
        "test_interactions_min": min(test_counts),
        "test_interactions_max": max(test_counts),
    }


def significance_user_counts(significance: dict[str, Any], dataset: str) -> set[int]:
    counts: set[int] = set()
    payload = significance.get("cold_full_catalog", {}).get(dataset, {})
    rows: list[Any] = []
    if isinstance(payload.get("comparisons"), list):
        rows.extend(payload["comparisons"])
    rows.extend(payload.values())
    for row in rows:
        if isinstance(row, dict) and row.get("n_users") is not None:
            counts.add(int(row["n_users"]))
    return counts


def dataset_summary(dataset: str, results: dict[str, Any], significance: dict[str, Any], seeds: list[int]) -> dict[str, Any]:
    category = CATEGORY_BY_DATASET[dataset]
    raw_subdir, raw_file = CATEGORIES[category]
    raw_cache = ROOT / "cache" / dataset / "raw_data_dedup.pkl"
    with raw_cache.open("rb") as f:
        raw = pickle.load(f)
    raw_summary = {
        "cache": str(raw_cache.relative_to(ROOT)),
        "source_category": category,
        "source_review_file": f"data/{raw_subdir}/{raw_file}",
        "deduplicated_interactions": len(raw["interactions"]),
        "deduplicated_users": len(raw["user2id"]),
        "deduplicated_items": len(raw["item2id"]),
    }
    k_core = DATASET_KCORE[dataset]
    filtered = kcore_filter(raw["interactions"], k_core)
    interactions, _, n_users, n_items, _ = reindex(filtered, raw["item_metadata"])
    sig_users = significance_user_counts(significance, dataset)
    if sig_users and n_users not in sig_users:
        raise RuntimeError(f"{dataset}: computed user count {n_users} not found in significance user counts {sorted(sig_users)}")
    candidate = results["cold_full_catalog"][dataset]["lc2c_retrieval_ltr"]
    fold_summary = fold_count_summary(candidate["fold_counts"])
    if fold_summary["total"] != int(candidate["n_records"]):
        raise RuntimeError(f"{dataset}: fold count total does not match candidate n_records")
    return {
        "dataset": dataset,
        "label": DATASET_LABELS[dataset],
        "raw": raw_summary,
        "strict_k_core": {
            "threshold": k_core,
            "users": n_users,
            "items": n_items,
            "interactions": len(interactions),
            "significance_user_counts": sorted(sig_users),
        },
        "item_fold_split": split_summary(interactions, n_items, seeds),
        "confirmatory_records": fold_summary,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    rows_raw = []
    rows_strict = []
    rows_split = []
    for row in payload["datasets"]:
        raw = row["raw"]
        strict = row["strict_k_core"]
        split = row["item_fold_split"]
        records = row["confirmatory_records"]
        rows_raw.append(
            "| {label} | `{cat}` | `{file}` | {users} | {items} | {interactions} |".format(
                label=row["label"],
                cat=raw["source_category"],
                file=raw["source_review_file"],
                users=fmt(raw["deduplicated_users"]),
                items=fmt(raw["deduplicated_items"]),
                interactions=fmt(raw["deduplicated_interactions"]),
            )
        )
        rows_strict.append(
            "| {label} | {k} | {users} | {items} | {interactions} |".format(
                label=row["label"],
                k=fmt(strict["threshold"]),
                users=fmt(strict["users"]),
                items=fmt(strict["items"]),
                interactions=fmt(strict["interactions"]),
            )
        )
        rows_split.append(
            "| {label} | {seed_folds} | {cold_min}-{cold_max} | {train_min}-{train_max} | {test_min}-{test_max} | {record_min}-{record_max} | {records} |".format(
                label=row["label"],
                seed_folds=fmt(split["seed_fold_count"]),
                cold_min=fmt(split["cold_items_min"]),
                cold_max=fmt(split["cold_items_max"]),
                train_min=fmt(split["train_interactions_min"]),
                train_max=fmt(split["train_interactions_max"]),
                test_min=fmt(split["test_interactions_min"]),
                test_max=fmt(split["test_interactions_max"]),
                record_min=fmt(records["min"]),
                record_max=fmt(records["max"]),
                records=fmt(records["total"]),
            )
        )
    lines = [
        "This appendix is generated by `_bestrec_sota_lab/paper_draft/generate_data_processing_appendix.py` from the raw deduplicated caches, `_bestrec_run/run_cold_item.py`, `_bestrec_run/v5_utils.py`, and the approved confirmatory artifacts.",
        "",
        "The raw Amazon Reviews 2023 category mapping is inherited from `_bestrec_run/preprocess_5core_standard.py`. The strict cold-item pipeline then applies dataset-specific recursive k-core filtering with `v5_utils.kcore_filter`, reindexes users/items with `v5_utils.reindex`, partitions items into five cold folds with `run_cold_item.make_item_kfold`, and evaluates full-catalog candidates after masking each user's training history.",
        "",
        "**Raw deduplicated cache before strict k-core filtering.**",
        "",
        "| Dataset | Amazon Reviews 2023 category | Review file | Users | Items | Interactions |",
        "| --- | --- | --- | ---: | ---: | ---: |",
        *rows_raw,
        "",
        "**Strict evaluation graph after recursive k-core filtering.**",
        "",
        "| Dataset | k-core threshold | Users | Items | Interactions |",
        "| --- | ---: | ---: | ---: | ---: |",
        *rows_strict,
        "",
        "**Confirmatory item-fold and record construction.**",
        "",
        "| Dataset | Seed-folds | Cold items/fold | Train interactions/fold | Cold test interactions/fold | Candidate records/fold | Candidate records total |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        *rows_split,
        "",
        "The confirmatory seeds are `{}`. Each seed uses five item folds. For every test record, the target item is in the held-out cold item set, and the ranking candidate set is the full strict item catalog minus the user's training items.".format(
            ", ".join(str(seed) for seed in payload["seeds"])
        ),
        "",
        "The documented user-facing command for the approved protocol is:",
        "",
        "```powershell",
        "uv --project _bestrec_run run python _bestrec_sota_lab/run_confirmatory.py --datasets beauty,fashion,instruments,books --seeds 20260701,20260702,20260703,20260704,20260705 --candidate-scope full_catalog --no-books-cap",
        "```",
        "",
        "The independently rebuilt approval run is `{}`, compared against canonical run `{}`.".format(
            payload["run_id"], payload["canonical_run_id"]
        ),
    ]
    return "\n".join(lines) + "\n"


def replace_section(text: str, section: str) -> str:
    if START not in text or END not in text:
        raise RuntimeError("Manuscript appendix markers are missing")
    before, rest = text.split(START, 1)
    _, after = rest.split(END, 1)
    return before + START + "\n" + section.rstrip() + "\n" + END + after


def main() -> int:
    results = read_json(RUN_DIR / "results_final.json")
    significance = read_json(RUN_DIR / "significance.json")
    run_config = read_json(RUN_DIR / "run_config.json")
    seeds = [int(x) for x in run_config["seeds"]]
    payload = {
        "schema_version": 1,
        "run_id": RUN_ID,
        "canonical_run_id": CANONICAL_RUN_ID,
        "seeds": seeds,
        "datasets": [dataset_summary(dataset, results, significance, seeds) for dataset in DATASETS],
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    markdown = render_markdown(payload)
    OUT_MD.write_text(markdown, encoding="utf-8")
    PAPER.write_text(replace_section(PAPER.read_text(encoding="utf-8"), markdown), encoding="utf-8")
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {OUT_MD}")
    print(f"Updated {PAPER}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
