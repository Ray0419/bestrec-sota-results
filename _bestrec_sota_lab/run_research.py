"""Run isolated development experiments for the retrieval-first LC2C successor."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from lc2c_retrieval_ltr import LTRConfig
from sota_common import (
    LAB_CANDIDATE,
    LAB_DIR,
    DATASETS,
    LAB_PROTOCOL,
    OFFICIAL_DROPOUTNET_FEATURE_CONFIG,
    make_lab_run_dir,
    parse_csv,
    protocol_summary,
    run_cold_ltr_dataset,
    write_json,
    write_run_config,
)


def research_decision(cold_results: dict) -> dict:
    wins = []
    macro_candidate = []
    macro_content = []
    for dataset, block in cold_results.items():
        methods = block.get("methods", block)
        cand = methods.get(LAB_CANDIDATE, {}).get("NDCG@10")
        content = methods.get("content_direct", {}).get("NDCG@10")
        if cand is None or content is None:
            wins.append({"dataset": dataset, "win": False, "reason": "missing_metrics"})
            continue
        macro_candidate.append(float(cand))
        macro_content.append(float(content))
        wins.append({"dataset": dataset, "win": float(cand) > float(content), "candidate_ndcg10": cand, "content_direct_ndcg10": content})
    n_wins = sum(1 for row in wins if row.get("win"))
    macro_delta = None
    if macro_candidate and macro_content:
        macro_delta = sum(macro_candidate) / len(macro_candidate) - sum(macro_content) / len(macro_content)
    selected = len(wins) >= 4 and n_wins >= 3 and (macro_delta is not None and macro_delta > 0)
    return {
        "candidate": LAB_CANDIDATE,
        "selected_for_confirmatory": selected,
        "rule": "select only if all four datasets are present, candidate beats content_direct on >=3 datasets, and macro delta is positive",
        "wins": wins,
        "n_wins": n_wins,
        "macro_delta_vs_content_direct": macro_delta,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datasets", default="beauty,fashion,instruments,books")
    parser.add_argument("--seeds", default="101,102,103")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--max-folds", type=int, default=0, help="Smoke-test limit; 0 means all folds.")
    parser.add_argument("--quick", action="store_true", help="Use short deep-baseline training for smoke tests.")
    parser.add_argument("--resume", action="store_true", help="Skip dataset/seed/folds already present in JSONL records.")
    parser.add_argument("--rank-feature-scope", choices=["full", "local", "zsigmoid"], default=LTRConfig().rank_feature_scope)
    parser.add_argument("--rerank-top-m", type=int, default=LTRConfig().rerank_top_m)
    parser.add_argument("--rerank-anchor-method", default=LTRConfig().rerank_anchor_method)
    parser.add_argument("--extra-rerank-anchor-methods", default="")
    parser.add_argument("--rerank-output-mode", choices=["lift", "rank_blend", "residual"], default=LTRConfig().rerank_output_mode)
    parser.add_argument("--rerank-prediction-weight", type=float, default=LTRConfig().rerank_prediction_weight)
    parser.add_argument("--min-validation-gain", type=float, default=LTRConfig().min_validation_gain)
    parser.add_argument("--validation-baseline-method", default=None)
    parser.add_argument("--fallback-method", default=None)
    parser.add_argument("--mask-seen-in-topm", action="store_true", help="Exclude training-history items when selecting the candidate rerank set.")
    parser.add_argument("--use-official-dropoutnet", action="store_true", help="Add faithful WMF-backed DropoutNet as an LTR feature and rerank anchor.")
    parser.add_argument("--finalize-bootstrap-reps", type=int, default=200, help="Research finalization bootstrap reps; research runs never approve publication.")
    parser.add_argument("--allow-negative", action="store_true", help="Return 0 even when the research decision is negative.")
    args = parser.parse_args()

    datasets = parse_csv(args.datasets)
    seeds = parse_csv(args.seeds, int)
    run_id, run_dir = make_lab_run_dir("research", args.run_id)
    deep_scale = 0.05 if args.quick else 1.0
    if args.quick and not args.max_folds:
        args.max_folds = 1
    feature_methods = list(LTRConfig().feature_methods)
    anchor_methods = parse_csv(args.extra_rerank_anchor_methods)
    if args.use_official_dropoutnet:
        if "official_dropoutnet" not in feature_methods:
            feature_methods.append("official_dropoutnet")
        anchor_methods.append("official_dropoutnet")
        if args.rerank_anchor_method == "official_dropoutnet" and "content_direct" not in anchor_methods:
            anchor_methods.append("content_direct")
    validation_baseline_method = args.validation_baseline_method
    fallback_method = args.fallback_method
    if args.use_official_dropoutnet:
        validation_baseline_method = validation_baseline_method or "official_dropoutnet"
        fallback_method = fallback_method or "official_dropoutnet"
    config = LTRConfig(
        feature_methods=tuple(feature_methods),
        min_validation_gain=args.min_validation_gain,
        rank_feature_scope=args.rank_feature_scope,
        rerank_top_m=args.rerank_top_m,
        rerank_anchor_method=args.rerank_anchor_method,
        rerank_output_mode=args.rerank_output_mode,
        rerank_prediction_weight=args.rerank_prediction_weight,
        mask_seen_in_topm=args.mask_seen_in_topm,
        rerank_anchor_methods=tuple(anchor_methods),
        validation_baseline_method=validation_baseline_method or LTRConfig().validation_baseline_method,
        fallback_method=fallback_method or LTRConfig().fallback_method,
    )
    write_run_config(
        run_dir,
        {
            "stage": "research",
            "run_id": run_id,
            "datasets": datasets,
            "seeds": seeds,
            "candidate_scope": "full_catalog",
            "max_folds": args.max_folds,
            "quick": args.quick,
            "ltr_config": config.to_json(),
        },
    )
    cold_results = {}
    for dataset in datasets:
        cold_results[dataset] = run_cold_ltr_dataset(
            dataset=dataset,
            seeds=seeds,
            run_dir=run_dir,
            ltr_config=config,
            stage="research",
            include_deep=True,
            deep_epochs_scale=deep_scale,
            max_folds=args.max_folds,
            resume=args.resume,
        )
        write_json(run_dir / "results_partial.json", {"schema_version": 1, "run_id": run_id, "cold_full_catalog": cold_results})

    decision = research_decision(cold_results)
    if args.quick or args.max_folds or set(datasets) != set(DATASETS):
        decision["selected_for_confirmatory"] = False
        decision["selection_blocked_reason"] = "quick, max-fold, or partial-dataset runs cannot freeze a confirmatory candidate"
    write_json(run_dir / "research_decision.json", decision)
    if decision["selected_for_confirmatory"]:
        write_json(
            run_dir / "frozen_candidate_config.json",
            {
                "schema_version": 1,
                "candidate": LAB_CANDIDATE,
                "ltr_config": config.to_json(),
                "source_research_run": run_id,
                "protocol": protocol_summary(LAB_PROTOCOL),
                "dropoutnet_feature_config": OFFICIAL_DROPOUTNET_FEATURE_CONFIG,
            },
        )
    subprocess.run([sys.executable, str(LAB_DIR / "finalize.py"), "--run-id", run_id, "--bootstrap-reps", str(args.finalize_bootstrap_reps)], check=False)
    if args.resume:
        final_path = run_dir / "results_final.json"
        if final_path.exists():
            final_payload = __import__("json").loads(final_path.read_text(encoding="utf-8"))
            decision = research_decision(final_payload.get("cold_full_catalog", {}))
            if args.quick or args.max_folds or set(datasets) != set(DATASETS):
                decision["selected_for_confirmatory"] = False
                decision["selection_blocked_reason"] = "quick, max-fold, or partial-dataset runs cannot freeze a confirmatory candidate"
            write_json(run_dir / "research_decision.json", decision)
            if decision["selected_for_confirmatory"]:
                write_json(
                    run_dir / "frozen_candidate_config.json",
                    {
                        "schema_version": 1,
                        "candidate": LAB_CANDIDATE,
                        "ltr_config": config.to_json(),
                        "source_research_run": run_id,
                        "protocol": protocol_summary(LAB_PROTOCOL),
                        "dropoutnet_feature_config": OFFICIAL_DROPOUTNET_FEATURE_CONFIG,
                    },
                )
    print(f"Research run: {run_dir}")
    print("Selected for confirmatory:", decision["selected_for_confirmatory"])
    return 0 if decision["selected_for_confirmatory"] or args.allow_negative else 1


if __name__ == "__main__":
    raise SystemExit(main())
