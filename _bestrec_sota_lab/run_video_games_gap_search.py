"""Run isolated Video_Games sequential gap-search experiments.

This script is for repairing the blocked Video_Games claim honestly. It does
not edit the historical `_bestrec_run` code; it launches that runner read-only,
records exact commands/configs/hashes, and compares every attempt against the
HSTU-BLaIR blocker documented in the SOTA audit.

The output is exploratory unless a later multi-seed confirmatory runner turns a
winning configuration into canonical per-user records.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LAB_DIR = ROOT / "_bestrec_sota_lab"
RUN_DIR = LAB_DIR / "runs"
SASREC_RUNNER = ROOT / "_bestrec_run" / "run_sasrec_sbert.py"
SPLIT_DIR = ROOT / "data_5core" / "5core" / "last_out"
CACHE_DIR = ROOT / "cache_5core"
DATASET = "Video_Games"

UPSTREAM_HSTU_BLAIR_NDCG10 = 0.0760
LOCAL_HSTU_BLAIR_BEST_FULL_NDCG10 = 0.0740334615111351
LOCAL_HSTU_BLAIR_FINAL_FULL_NDCG10 = 0.07382241636514664
SASREC_SBERT_5SEED_MEAN_NDCG10 = 0.0550927


@dataclass(frozen=True)
class Variant:
    name: str
    epochs: int
    seed: int = 20260721
    batch_size: int = 256
    max_seq_len: int = 50
    d_model: int = 64
    n_layers: int = 2
    n_heads: int = 2
    dropout: float = 0.2
    lr: float = 1e-3
    eval_every: int = 5
    eval_subsample: int = 0
    item_chunk: int = 32768
    augment_factor: int = 1
    lr_schedule: str = "warmup_cosine"
    encoder_cache: Path | None = None
    mlp_adaptor: bool = False
    mlp_hidden: int = 300
    mlp_dropout: float = 0.2
    chunked_full_softmax: bool = True
    extra_flags: tuple[str, ...] = field(default_factory=tuple)

    def to_json(self) -> dict[str, Any]:
        payload = self.__dict__.copy()
        if self.encoder_cache is not None:
            payload["encoder_cache"] = str(self.encoder_cache)
        payload["extra_flags"] = list(self.extra_flags)
        return payload


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": str(path), "exists": False}
    h = hashlib.sha256()
    with path.open("rb") as fp:
        for block in iter(lambda: fp.read(1024 * 1024), b""):
            h.update(block)
    stat = path.stat()
    return {
        "path": str(path),
        "exists": True,
        "sha256": h.hexdigest(),
        "size_bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }


def ensure_run_dir(run_id: str | None) -> tuple[str, Path]:
    if run_id is None:
        stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        run_id = f"video_games_gap_search_{stamp}"
    path = RUN_DIR / run_id
    path.mkdir(parents=True, exist_ok=True)
    return run_id, path


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def profile_variants(profile: str, seed: int) -> list[Variant]:
    sbert = CACHE_DIR / "sbert_titles_Video_Games.npy"
    blair = CACHE_DIR / "blair_titles_Video_Games.npy"
    if profile == "smoke":
        return [
            Variant(
                name="smoke_sbert_d64_e1",
                seed=seed,
                epochs=1,
                eval_every=1,
                eval_subsample=512,
                dropout=0.2,
                encoder_cache=sbert,
            )
        ]
    if profile == "dev":
        return [
            Variant(
                name="sbert_d64_e50_dropout03_warmcos",
                seed=seed,
                epochs=50,
                dropout=0.3,
                encoder_cache=sbert,
            ),
            Variant(
                name="sbert_d128_l2_h4_e60_dropout03",
                seed=seed,
                epochs=60,
                d_model=128,
                n_heads=4,
                dropout=0.3,
                encoder_cache=sbert,
            ),
            Variant(
                name="sbert_d128_l3_h4_e60_dropout03",
                seed=seed,
                epochs=60,
                d_model=128,
                n_layers=3,
                n_heads=4,
                dropout=0.3,
                encoder_cache=sbert,
            ),
            Variant(
                name="sbert_mlp_d128_l2_h4_aug2_e60",
                seed=seed,
                epochs=60,
                d_model=128,
                n_heads=4,
                dropout=0.3,
                mlp_adaptor=True,
                augment_factor=2,
                encoder_cache=sbert,
            ),
            Variant(
                name="blair_mlp_d128_l2_h4_e60",
                seed=seed,
                epochs=60,
                d_model=128,
                n_heads=4,
                dropout=0.3,
                mlp_adaptor=True,
                encoder_cache=blair,
            ),
        ]
    if profile == "aggressive":
        return [
            Variant(
                name="sbert_d128_l3_h4_aug2_e100",
                seed=seed,
                epochs=100,
                d_model=128,
                n_layers=3,
                n_heads=4,
                dropout=0.3,
                augment_factor=2,
                encoder_cache=sbert,
            ),
            Variant(
                name="blair_mlp_d128_l3_h4_aug2_e100",
                seed=seed,
                epochs=100,
                d_model=128,
                n_layers=3,
                n_heads=4,
                dropout=0.3,
                mlp_adaptor=True,
                augment_factor=2,
                encoder_cache=blair,
            ),
        ]
    raise ValueError(f"unknown profile: {profile}")


def build_command(variant: Variant, out_path: Path) -> list[str]:
    cmd = [
        sys.executable,
        str(SASREC_RUNNER),
        DATASET,
        "--epochs",
        str(variant.epochs),
        "--batch-size",
        str(variant.batch_size),
        "--max-seq-len",
        str(variant.max_seq_len),
        "--d-model",
        str(variant.d_model),
        "--n-layers",
        str(variant.n_layers),
        "--n-heads",
        str(variant.n_heads),
        "--dropout",
        str(variant.dropout),
        "--lr",
        str(variant.lr),
        "--eval-every",
        str(variant.eval_every),
        "--eval-subsample",
        str(variant.eval_subsample),
        "--item-chunk",
        str(variant.item_chunk),
        "--augment-factor",
        str(variant.augment_factor),
        "--seed",
        str(variant.seed),
        "--lr-schedule",
        variant.lr_schedule,
        "--out",
        str(out_path),
    ]
    if variant.encoder_cache is not None:
        cmd.extend(["--encoder-cache", str(variant.encoder_cache)])
    if variant.mlp_adaptor:
        cmd.extend(["--mlp-adaptor", "--mlp-hidden", str(variant.mlp_hidden), "--mlp-dropout", str(variant.mlp_dropout)])
    if variant.chunked_full_softmax:
        cmd.append("--chunked-full-softmax")
    cmd.extend(variant.extra_flags)
    return cmd


def read_metric(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False}
    payload = json.loads(path.read_text(encoding="utf-8"))
    best_test = payload.get("best_test") or {}
    history = payload.get("history") or []
    final_test = {}
    for row in reversed(history):
        if "test" in row:
            final_test = row["test"]
            break
    best_ndcg = best_test.get("NDCG@10")
    final_ndcg = final_test.get("NDCG@10")
    return {
        "exists": True,
        "path": str(path),
        "best_test": best_test,
        "final_test": final_test,
        "best_test_ndcg10": best_ndcg,
        "final_test_ndcg10": final_ndcg,
        "best_val_ndcg10": payload.get("best_val_NDCG10"),
        "n_users": payload.get("n_users"),
        "n_items": payload.get("n_items"),
        "n_params": payload.get("n_params"),
    }


def summarize(run_id: str, run_dir: Path, variant_rows: list[dict[str, Any]]) -> dict[str, Any]:
    completed = [row for row in variant_rows if row.get("returncode") == 0 and row.get("metrics", {}).get("best_test_ndcg10") is not None]
    best = None
    if completed:
        best = max(completed, key=lambda row: float(row["metrics"]["best_test_ndcg10"]))
    target = max(UPSTREAM_HSTU_BLAIR_NDCG10, LOCAL_HSTU_BLAIR_BEST_FULL_NDCG10)
    best_ndcg = None if best is None else float(best["metrics"]["best_test_ndcg10"])
    return {
        "schema_version": 1,
        "run_id": run_id,
        "generated_at_utc": utc_now(),
        "stage": "exploratory_gap_search",
        "dataset": DATASET,
        "candidate_family": "sasrec_text_gap_search",
        "hstu_blocker": {
            "upstream_hstu_blair_ndcg10": UPSTREAM_HSTU_BLAIR_NDCG10,
            "local_hstu_blair_best_full_ndcg10": LOCAL_HSTU_BLAIR_BEST_FULL_NDCG10,
            "local_hstu_blair_final_full_ndcg10": LOCAL_HSTU_BLAIR_FINAL_FULL_NDCG10,
            "publication_note": "A single exploratory run beating this target would only justify a fresh multi-seed confirmatory study, not a SOTA claim.",
        },
        "previous_sasrec_sbert_5seed_mean_ndcg10": SASREC_SBERT_5SEED_MEAN_NDCG10,
        "best_variant": None if best is None else best["variant"],
        "best_variant_ndcg10": best_ndcg,
        "gap_to_required_single_run_target": None if best_ndcg is None else best_ndcg - target,
        "beats_single_run_hstu_target": bool(best_ndcg is not None and best_ndcg > target),
        "publication_claim_allowed": False,
        "publication_claim_blocker": (
            "No completed variant beats the HSTU-BLaIR target."
            if best_ndcg is None or best_ndcg <= target
            else "Exploratory single-seed result only; needs frozen multi-seed confirmatory per-user records."
        ),
        "variants": variant_rows,
    }


def write_report(run_dir: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Video_Games HSTU Gap Search Report",
        "",
        f"Run ID: `{summary['run_id']}`",
        f"Generated: `{summary['generated_at_utc']}`",
        "",
        "## Verdict",
        "",
    ]
    if summary["beats_single_run_hstu_target"]:
        lines.extend(
            [
                "A variant beat the single-run HSTU target in exploratory mode.",
                "",
                "**No SOTA claim is allowed yet.** Freeze the config and run fresh multi-seed confirmatory records.",
            ]
        )
    else:
        lines.append("No variant in this run beat the HSTU-BLaIR blocker. SOTA wording remains blocked.")
    lines.extend(
        [
            "",
            "## Targets",
            "",
            f"- Upstream HSTU-BLaIR NDCG@10: `{UPSTREAM_HSTU_BLAIR_NDCG10}`",
            f"- Local SM120 HSTU-BLaIR best full NDCG@10: `{LOCAL_HSTU_BLAIR_BEST_FULL_NDCG10}`",
            f"- Previous SASRec-SBERT 5-seed mean NDCG@10: `{SASREC_SBERT_5SEED_MEAN_NDCG10}`",
            "",
            "## Variants",
            "",
            "| Variant | Return | Best test NDCG@10 | Gap to target | Params | Result |",
            "|---|---:|---:|---:|---:|---|",
        ]
    )
    target = max(UPSTREAM_HSTU_BLAIR_NDCG10, LOCAL_HSTU_BLAIR_BEST_FULL_NDCG10)
    for row in summary["variants"]:
        metrics = row.get("metrics", {})
        ndcg = metrics.get("best_test_ndcg10")
        gap = "" if ndcg is None else f"{float(ndcg) - target:.6f}"
        ndcg_s = "" if ndcg is None else f"{float(ndcg):.6f}"
        params = metrics.get("n_params")
        params_s = "" if params is None else f"{int(params):,}"
        lines.append(
            f"| `{row['variant']}` | {row.get('returncode')} | {ndcg_s} | {gap} | {params_s} | `{metrics.get('path', '')}` |"
        )
    lines.extend(
        [
            "",
            "## Claim Rule",
            "",
            "This report can only unblock SOTA wording if a variant first beats the HSTU target here, then the exact frozen config passes fresh multi-seed confirmatory evaluation with per-user records, artifact hashes, and significance tests.",
            "",
        ]
    )
    (run_dir / "GAP_SEARCH_REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=["smoke", "dev", "aggressive"], default="smoke")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--seed", type=int, default=20260721)
    parser.add_argument("--variants", default="", help="Comma-separated variant names from the selected profile.")
    parser.add_argument("--max-variants", type=int, default=0)
    parser.add_argument("--force", action="store_true", help="Rerun variants even if their result JSON exists.")
    parser.add_argument("--dry-run", action="store_true", help="Write config/manifest without launching training.")
    parser.add_argument("--allow-negative", action="store_true", help="Return 0 even if no exploratory variant beats HSTU.")
    args = parser.parse_args()

    run_id, run_dir = ensure_run_dir(args.run_id)
    selected = profile_variants(args.profile, args.seed)
    if args.variants:
        wanted = {name.strip() for name in args.variants.split(",") if name.strip()}
        selected = [v for v in selected if v.name in wanted]
    if args.max_variants:
        selected = selected[: args.max_variants]
    if not selected:
        raise SystemExit("No variants selected.")

    inputs = [
        SASREC_RUNNER,
        Path(__file__),
        SPLIT_DIR / f"{DATASET}.train.csv",
        SPLIT_DIR / f"{DATASET}.valid.csv",
        SPLIT_DIR / f"{DATASET}.test.csv",
        CACHE_DIR / "sbert_titles_Video_Games.npy",
        CACHE_DIR / "blair_titles_Video_Games.npy",
    ]
    run_config = {
        "schema_version": 1,
        "run_id": run_id,
        "created_at_utc": utc_now(),
        "profile": args.profile,
        "seed": args.seed,
        "python": sys.executable,
        "platform": platform.platform(),
        "cwd": str(ROOT),
        "variants": [v.to_json() for v in selected],
        "hstu_target_ndcg10": max(UPSTREAM_HSTU_BLAIR_NDCG10, LOCAL_HSTU_BLAIR_BEST_FULL_NDCG10),
        "dry_run": args.dry_run,
    }
    write_json(run_dir / "run_config.json", run_config)
    write_json(
        run_dir / "results_manifest.json",
        {
            "schema_version": 1,
            "run_id": run_id,
            "created_at_utc": utc_now(),
            "input_hashes": {str(path): sha256_file(path) for path in inputs},
            "commands": [],
        },
    )

    manifest = json.loads((run_dir / "results_manifest.json").read_text(encoding="utf-8"))
    variant_rows: list[dict[str, Any]] = []
    for variant in selected:
        out_path = run_dir / f"result_{variant.name}.json"
        stdout_path = run_dir / f"{variant.name}.stdout.log"
        stderr_path = run_dir / f"{variant.name}.stderr.log"
        cmd = build_command(variant, out_path)
        row: dict[str, Any] = {
            "variant": variant.name,
            "config": variant.to_json(),
            "command": cmd,
            "out": str(out_path),
            "started_at_utc": utc_now(),
        }
        if out_path.exists() and not args.force:
            row["skipped"] = True
            row["returncode"] = 0
            row["metrics"] = read_metric(out_path)
        elif args.dry_run:
            row["skipped"] = True
            row["dry_run"] = True
            row["returncode"] = None
            row["metrics"] = read_metric(out_path)
        else:
            t0 = time.time()
            with stdout_path.open("w", encoding="utf-8") as stdout, stderr_path.open("w", encoding="utf-8") as stderr:
                proc = subprocess.run(cmd, cwd=ROOT, stdout=stdout, stderr=stderr, text=True, check=False)
            row["returncode"] = proc.returncode
            row["duration_s"] = time.time() - t0
            row["stdout"] = str(stdout_path)
            row["stderr"] = str(stderr_path)
            row["metrics"] = read_metric(out_path)
        row["completed_at_utc"] = utc_now()
        variant_rows.append(row)
        manifest["commands"].append(
            {
                "variant": variant.name,
                "command": cmd,
                "returncode": row.get("returncode"),
                "result_hash": sha256_file(out_path),
                "stdout_hash": sha256_file(stdout_path),
                "stderr_hash": sha256_file(stderr_path),
            }
        )
        write_json(run_dir / "results_partial.json", {"schema_version": 1, "run_id": run_id, "variants": variant_rows})
        write_json(run_dir / "results_manifest.json", manifest)

    summary = summarize(run_id, run_dir, variant_rows)
    manifest["output_hashes"] = {
        "run_config": sha256_file(run_dir / "run_config.json"),
        "results_partial": sha256_file(run_dir / "results_partial.json"),
    }
    write_json(run_dir / "gap_search_summary.json", summary)
    write_report(run_dir, summary)
    manifest["output_hashes"]["gap_search_summary"] = sha256_file(run_dir / "gap_search_summary.json")
    manifest["output_hashes"]["gap_search_report"] = sha256_file(run_dir / "GAP_SEARCH_REPORT.md")
    write_json(run_dir / "results_manifest.json", manifest)

    print(f"Gap-search run: {run_dir}")
    print(f"Best variant: {summary['best_variant']}")
    print(f"Best NDCG@10: {summary['best_variant_ndcg10']}")
    print(f"Beats HSTU single-run target: {summary['beats_single_run_hstu_target']}")
    if summary["beats_single_run_hstu_target"] or args.allow_negative or args.dry_run:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
