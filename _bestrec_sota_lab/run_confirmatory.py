"""Run frozen isolated confirmatory experiments for the SOTA-lab candidate."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from lc2c_retrieval_ltr import LTRConfig
from sota_common import (
    LAB_DIR,
    CONFIRMATORY_SEEDS_CSV,
    DATASETS,
    LAB_PROTOCOL,
    OFFICIAL_DROPOUTNET_FEATURE_CONFIG,
    make_lab_run_dir,
    parse_csv,
    read_json,
    run_cold_ltr_dataset,
    run_warm_records,
    write_json,
    write_run_config,
)


def load_ltr_config(config_path: str | None) -> tuple[LTRConfig, dict]:
    if not config_path:
        cfg = LTRConfig()
        return cfg, {"source": "default_config_no_research_override", "ltr_config": cfg.to_json()}
    payload = read_json(Path(config_path))
    raw = payload.get("ltr_config", payload)
    cfg = LTRConfig(
        feature_methods=tuple(raw.get("feature_methods", LTRConfig().feature_methods)),
        negative_samples_per_positive=int(raw.get("negative_samples_per_positive", LTRConfig().negative_samples_per_positive)),
        max_train_examples=int(raw.get("max_train_examples", LTRConfig().max_train_examples)),
        n_estimators=int(raw.get("n_estimators", LTRConfig().n_estimators)),
        learning_rate=float(raw.get("learning_rate", LTRConfig().learning_rate)),
        max_depth=int(raw.get("max_depth", LTRConfig().max_depth)),
        min_validation_gain=float(raw.get("min_validation_gain", LTRConfig().min_validation_gain)),
        score_batch_items=int(raw.get("score_batch_items", LTRConfig().score_batch_items)),
        rerank_top_m=int(raw.get("rerank_top_m", LTRConfig().rerank_top_m)),
        rerank_anchor_method=str(raw.get("rerank_anchor_method", LTRConfig().rerank_anchor_method)),
        rerank_anchor_methods=tuple(raw.get("rerank_anchor_methods", LTRConfig().rerank_anchor_methods)),
        rank_feature_scope=str(raw.get("rank_feature_scope", LTRConfig().rank_feature_scope)),
        mask_seen_in_topm=bool(raw.get("mask_seen_in_topm", LTRConfig().mask_seen_in_topm)),
        validation_baseline_method=str(raw.get("validation_baseline_method", LTRConfig().validation_baseline_method)),
        fallback_method=str(raw.get("fallback_method", LTRConfig().fallback_method)),
        rerank_output_mode=str(raw.get("rerank_output_mode", LTRConfig().rerank_output_mode)),
        rerank_prediction_weight=float(raw.get("rerank_prediction_weight", LTRConfig().rerank_prediction_weight)),
    )
    return cfg, {
        "source": str(config_path),
        "ltr_config": cfg.to_json(),
        "protocol": payload.get("protocol", {}),
        "dropoutnet_feature_config": payload.get("dropoutnet_feature_config"),
        "source_research_run": payload.get("source_research_run"),
        "ablation": payload.get("ablation"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datasets", default="beauty,fashion,instruments,books")
    parser.add_argument("--seeds", default=CONFIRMATORY_SEEDS_CSV)
    parser.add_argument("--candidate-scope", choices=["full_catalog"], default="full_catalog")
    parser.add_argument("--no-books-cap", action="store_true")
    parser.add_argument("--config", default=None, help="Path to frozen_candidate_config.json from a research run.")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--skip-warm", action="store_true")
    parser.add_argument("--max-folds", type=int, default=0, help="Smoke-test limit; 0 means all folds.")
    parser.add_argument("--quick", action="store_true", help="Use short deep-baseline training for smoke tests.")
    parser.add_argument("--resume", action="store_true", help="Skip dataset/seed/folds already present in JSONL records.")
    parser.add_argument("--candidate-only", action="store_true", help="Diagnostic mode: write only lc2c_retrieval_ltr cold records.")
    parser.add_argument("--finalize-bootstrap-reps", type=int, default=None, help="Override finalization bootstrap reps. Full confirmatory defaults to the strict protocol minimum.")
    parser.add_argument("--allow-failure-report", action="store_true")
    args = parser.parse_args()

    if not args.no_books_cap:
        print("ERROR: confirmatory run requires --no-books-cap.")
        return 2
    datasets = parse_csv(args.datasets)
    seeds = parse_csv(args.seeds, int)
    run_id, run_dir = make_lab_run_dir("confirmatory", args.run_id)
    ltr_config, config_meta = load_ltr_config(args.config)
    expected_seeds = [int(x) for x in LAB_PROTOCOL.get("fresh_confirmatory_seeds", [])]
    full_confirmatory = not args.quick and not args.max_folds and set(datasets) == set(DATASETS)
    if full_confirmatory:
        if not args.config:
            print("ERROR: full confirmatory run requires --config from a strict-protocol research run.")
            return 2
        if seeds != expected_seeds:
            print(f"ERROR: full confirmatory seeds must be {expected_seeds}, got {seeds}.")
            return 2
        if config_meta.get("protocol", {}).get("protocol_id") != LAB_PROTOCOL.get("protocol_id"):
            print("ERROR: frozen candidate config was not produced under the active strict protocol.")
            return 2
        config_seeds = [int(x) for x in config_meta.get("protocol", {}).get("fresh_confirmatory_seeds", [])]
        if config_seeds and config_seeds != expected_seeds:
            print(f"ERROR: frozen candidate config seeds must be {expected_seeds}, got {config_seeds}.")
            return 2
        if config_meta.get("dropoutnet_feature_config") != OFFICIAL_DROPOUTNET_FEATURE_CONFIG:
            print("ERROR: frozen candidate config does not match the active DropoutNet feature config.")
            return 2
    deep_scale = 0.05 if args.quick else 1.0
    if args.quick and not args.max_folds:
        args.max_folds = 1
    write_run_config(
        run_dir,
        {
            "stage": "confirmatory",
            "run_id": run_id,
            "datasets": datasets,
            "seeds": seeds,
            "candidate_scope": args.candidate_scope,
            "no_books_cap": args.no_books_cap,
            "max_folds": args.max_folds,
            "quick": args.quick,
            "candidate_only": args.candidate_only,
            "frozen_config": config_meta,
        },
    )
    warm_results = {} if args.skip_warm else run_warm_records(datasets, seeds, run_dir)
    cold_results = {}
    for dataset in datasets:
        cold_results[dataset] = run_cold_ltr_dataset(
            dataset=dataset,
            seeds=seeds,
            run_dir=run_dir,
            ltr_config=ltr_config,
            stage="confirmatory",
            include_deep=True,
            deep_epochs_scale=deep_scale,
            max_folds=args.max_folds,
            resume=args.resume,
            eval_methods=["lc2c_retrieval_ltr"] if args.candidate_only else None,
        )
        write_json(run_dir / "results_partial.json", {"schema_version": 1, "run_id": run_id, "warm": warm_results, "cold_full_catalog": cold_results})
    finalize_cmd = [sys.executable, str(LAB_DIR / "finalize.py"), "--run-id", run_id]
    if args.finalize_bootstrap_reps is not None:
        finalize_cmd.extend(["--bootstrap-reps", str(args.finalize_bootstrap_reps)])
    elif args.quick or args.max_folds:
        finalize_cmd.extend(["--bootstrap-reps", "200"])
    res = subprocess.run(finalize_cmd, check=False)
    print(f"Confirmatory run: {run_dir}")
    return 0 if res.returncode == 0 or args.allow_failure_report else res.returncode


if __name__ == "__main__":
    raise SystemExit(main())
