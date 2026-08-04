"""Prepare or run fresh component jobs for the frozen sparse-RRF candidate.

By default this script writes a job manifest and exits. Use `--execute` with a
specific `--seed` and `--component` for targeted execution. The full job set is
large: five fresh seeds times six components, with HSTU components trained in
WSL and SASRec trained in the local uv environment.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
LAB_DIR = ROOT / "_bestrec_sota_lab"
DEFAULT_PROTOCOL = LAB_DIR / "frozen_candidates" / "video_games_sparse_rrf_confirmatory_protocol_20260609.json"
DEFAULT_MANIFEST = LAB_DIR / "frozen_candidates" / "video_games_sparse_rrf_confirmatory_jobs.json"
DEFAULT_STATUS = LAB_DIR / "frozen_candidates" / "video_games_sparse_rrf_confirmatory_job_status.jsonl"
DEFAULT_LOG_DIR = LAB_DIR / "runs" / "video_games_sparse_rrf_confirmatory_job_logs"


@dataclass(frozen=True)
class HstuConfig:
    epochs: int
    learning_rate: float = 0.001
    dropout_rate: float = 0.5
    item_embedding_dim: int = 64
    hstu_num_blocks: int | None = None
    hstu_num_heads: int | None = None
    hstu_dv: int | None = None
    hstu_dqk: int | None = None
    resume_from_component: str | None = None


HSTU_CONFIGS: dict[str, HstuConfig] = {
    "dev4": HstuConfig(epochs=60, dropout_rate=0.5),
    "dev5": HstuConfig(epochs=30, dropout_rate=0.3),
    "dev9": HstuConfig(epochs=60, dropout_rate=0.3),
    "dev10": HstuConfig(epochs=40, learning_rate=0.0003, dropout_rate=0.3, resume_from_component="dev9"),
    "dev13": HstuConfig(
        epochs=60,
        dropout_rate=0.3,
        item_embedding_dim=96,
        hstu_num_blocks=4,
        hstu_num_heads=4,
        hstu_dv=24,
        hstu_dqk=24,
    ),
}

SASREC_CONFIG: dict[str, Any] = {
    "epochs": 50,
    "batch_size": 256,
    "eval_batch_size": 512,
    "max_seq_len": 50,
    "d_model": 64,
    "n_layers": 2,
    "n_heads": 2,
    "dropout": 0.3,
    "lr": 0.001,
    "lr_schedule": "warmup_cosine",
    "export_split": "test",
    "export_limit_users": 0,
    "export_top_k": 50,
    "method": "sasrec_sbert_confirmatory",
}


def sha256_file(path: Path) -> dict[str, Any]:
    record: dict[str, Any] = {"path": str(path), "exists": path.exists()}
    if not path.exists():
        return record
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    stat = path.stat()
    record.update({"sha256": digest.hexdigest(), "size_bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns})
    return record


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def wsl_path(path: str | Path) -> str:
    text = str(path).replace("\\", "/")
    if text.startswith("C:/"):
        return "/mnt/c/" + text[3:]
    return text


def expected_hstu_export(seed: int, component: str) -> Path:
    return (
        LAB_DIR
        / "runs"
        / f"video_games_confirmatory_seed{seed}_{component}_export_test"
        / "warm_full_catalog_records_Video_Games_strict_hstu_test.jsonl"
    )


def expected_sasrec_export(seed: int) -> Path:
    return (
        LAB_DIR
        / "runs"
        / f"video_games_confirmatory_seed{seed}_sasrec_export_test"
        / "warm_full_catalog_records_Video_Games_sasrec_sbert_test.jsonl"
    )


def hstu_train_env(seed: int, component: str, cfg: HstuConfig) -> dict[str, str]:
    run_id = f"video_games_confirmatory_seed{seed}_{component}_train"
    env = {
        "HSTU_STRICT_RUN_ID": run_id,
        "HSTU_STRICT_SEED": str(seed),
        "HSTU_STRICT_EPOCHS": str(cfg.epochs),
        "HSTU_STRICT_EVAL_EVERY": "1",
        "HSTU_STRICT_MAX_TRAIN_BATCHES": "0",
        "HSTU_STRICT_MAX_EVAL_BATCHES": "0",
        "HSTU_STRICT_LEARNING_RATE": str(cfg.learning_rate),
        "HSTU_STRICT_DROPOUT_RATE": str(cfg.dropout_rate),
        "HSTU_STRICT_ITEM_EMBEDDING_DIM": str(cfg.item_embedding_dim),
        "HSTU_STRICT_BATCH_SIZE": "128",
        "HSTU_STRICT_EVAL_BATCH_SIZE": "128",
    }
    if cfg.hstu_num_blocks is not None:
        env["HSTU_STRICT_HSTU_NUM_BLOCKS"] = str(cfg.hstu_num_blocks)
    if cfg.hstu_num_heads is not None:
        env["HSTU_STRICT_HSTU_NUM_HEADS"] = str(cfg.hstu_num_heads)
    if cfg.hstu_dv is not None:
        env["HSTU_STRICT_HSTU_DV"] = str(cfg.hstu_dv)
    if cfg.hstu_dqk is not None:
        env["HSTU_STRICT_HSTU_DQK"] = str(cfg.hstu_dqk)
    if cfg.resume_from_component:
        env["HSTU_STRICT_RESUME_CHECKPOINT"] = (
            f"/mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/runs/"
            f"video_games_confirmatory_seed{seed}_{cfg.resume_from_component}_train/strict_hstu_best_valid.pt"
        )
    return env


def hstu_export_env(seed: int, component: str) -> dict[str, str]:
    return {
        "HSTU_STRICT_EXPORT_RUN_ID": f"video_games_confirmatory_seed{seed}_{component}_export_test",
        "HSTU_STRICT_CHECKPOINT": (
            f"/mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/runs/"
            f"video_games_confirmatory_seed{seed}_{component}_train/strict_hstu_best_valid.pt"
        ),
        "HSTU_STRICT_EXPORT_SPLIT": "test",
        "HSTU_STRICT_EXPORT_MAX_EVAL_BATCHES": "0",
        "HSTU_STRICT_EXPORT_TEACHER_TOP_K": "50",
    }


def bash_env_command(env: dict[str, str], script: str) -> str:
    exports = " ".join(f"{key}={json.dumps(value)}" for key, value in env.items())
    return f"{exports} bash {json.dumps(script)}"


def make_hstu_job(seed: int, component: str, cfg: HstuConfig) -> dict[str, Any]:
    train_script = "/mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/hstu_blair_wsl/train_strict_hstu_sm120_wsl.sh"
    export_script = "/mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/hstu_blair_wsl/export_strict_hstu_records_sm120_wsl.sh"
    train_bash = bash_env_command(hstu_train_env(seed, component, cfg), train_script)
    export_bash = bash_env_command(hstu_export_env(seed, component), export_script)
    return {
        "seed": seed,
        "component": component,
        "kind": "hstu",
        "depends_on": [f"seed{seed}_{cfg.resume_from_component}"] if cfg.resume_from_component else [],
        "train_run_id": f"video_games_confirmatory_seed{seed}_{component}_train",
        "export_run_id": f"video_games_confirmatory_seed{seed}_{component}_export_test",
        "expected_output": str(expected_hstu_export(seed, component)),
        "ids_key": "teacher_top_ids",
        "frozen_config": cfg.__dict__,
        "train_command": ["wsl", "-d", "Ubuntu-20.04", "--", "bash", "-lc", train_bash],
        "export_command": ["wsl", "-d", "Ubuntu-20.04", "--", "bash", "-lc", export_bash],
    }


def make_sasrec_job(seed: int) -> dict[str, Any]:
    run_id = f"video_games_confirmatory_seed{seed}_sasrec_export_test"
    cmd = [
        sys.executable,
        str(LAB_DIR / "export_sasrec_sbert_records.py"),
        "--category",
        "Video_Games",
        "--run-id",
        run_id,
        "--epochs",
        str(SASREC_CONFIG["epochs"]),
        "--batch-size",
        str(SASREC_CONFIG["batch_size"]),
        "--eval-batch-size",
        str(SASREC_CONFIG["eval_batch_size"]),
        "--max-seq-len",
        str(SASREC_CONFIG["max_seq_len"]),
        "--d-model",
        str(SASREC_CONFIG["d_model"]),
        "--n-layers",
        str(SASREC_CONFIG["n_layers"]),
        "--n-heads",
        str(SASREC_CONFIG["n_heads"]),
        "--dropout",
        str(SASREC_CONFIG["dropout"]),
        "--lr",
        str(SASREC_CONFIG["lr"]),
        "--lr-schedule",
        str(SASREC_CONFIG["lr_schedule"]),
        "--export-split",
        str(SASREC_CONFIG["export_split"]),
        "--export-limit-users",
        str(SASREC_CONFIG["export_limit_users"]),
        "--export-top-k",
        str(SASREC_CONFIG["export_top_k"]),
        "--seed",
        str(seed),
        "--method",
        str(SASREC_CONFIG["method"]),
        "--evidence-stage",
        "confirmatory",
        "--evidence-scope",
        "video_games_sparse_rrf_frozen_component_input",
        "--protocol-manifest",
        str(DEFAULT_PROTOCOL),
        "--claim-scope",
        "local_video_games_component_comparator_evidence_only",
    ]
    return {
        "seed": seed,
        "component": "sasrec",
        "kind": "sasrec",
        "depends_on": [],
        "run_id": run_id,
        "expected_output": str(expected_sasrec_export(seed)),
        "ids_key": "top_ids",
        "frozen_config": SASREC_CONFIG,
        "command": cmd,
    }


def build_jobs(seeds: list[int]) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    for seed in seeds:
        for component in ("dev4", "dev5", "dev9", "dev10", "dev13"):
            jobs.append(make_hstu_job(seed, component, HSTU_CONFIGS[component]))
        jobs.append(make_sasrec_job(seed))
    return jobs


def job_key(job: dict[str, Any]) -> str:
    return f"seed{job['seed']}_{job['component']}"


def checkpoint_for(seed: int, component: str) -> Path:
    return LAB_DIR / "runs" / f"video_games_confirmatory_seed{seed}_{component}_train" / "strict_hstu_best_valid.pt"


def write_manifest(path: Path, protocol: dict[str, Any], jobs: list[dict[str, Any]]) -> None:
    outputs = [Path(job["expected_output"]) for job in jobs]
    payload = {
        "schema_version": 1,
        "status": "prepared",
        "evidence_stage": "confirmatory",
        "evidence_scope": "video_games_sparse_rrf_frozen_component_jobs",
        "claim_scope": "local_video_games_component_comparator_evidence_only",
        "publication_grade": False,
        "generated_at_utc": utc_now(),
        "protocol": protocol,
        "job_count": len(jobs),
        "jobs": jobs,
        "expected_outputs": [str(path) for path in outputs],
        "present_outputs": [str(path) for path in outputs if path.exists()],
        "missing_outputs": [str(path) for path in outputs if not path.exists()],
        "runner": sha256_file(Path(__file__)),
        "static_inputs": {
            "protocol": sha256_file(DEFAULT_PROTOCOL),
            "train_wrapper": sha256_file(LAB_DIR / "hstu_blair_wsl" / "train_strict_hstu_sm120_wsl.sh"),
            "export_wrapper": sha256_file(LAB_DIR / "hstu_blair_wsl" / "export_strict_hstu_records_sm120_wsl.sh"),
            "hstu_trainer": sha256_file(LAB_DIR / "hstu_blair_wsl" / "train_strict_hstu_sm120.py"),
            "hstu_exporter": sha256_file(LAB_DIR / "hstu_blair_wsl" / "export_strict_hstu_records.py"),
            "sasrec_exporter": sha256_file(LAB_DIR / "export_sasrec_sbert_records.py"),
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def preflight() -> dict[str, Any]:
    local_paths = {
        "candidate_protocol": DEFAULT_PROTOCOL,
        "hstu_train_wrapper": LAB_DIR / "hstu_blair_wsl" / "train_strict_hstu_sm120_wsl.sh",
        "hstu_export_wrapper": LAB_DIR / "hstu_blair_wsl" / "export_strict_hstu_records_sm120_wsl.sh",
        "hstu_trainer": LAB_DIR / "hstu_blair_wsl" / "train_strict_hstu_sm120.py",
        "hstu_exporter": LAB_DIR / "hstu_blair_wsl" / "export_strict_hstu_records.py",
        "sasrec_exporter": LAB_DIR / "export_sasrec_sbert_records.py",
        "strict_train_csv": LAB_DIR / "runs" / "hstu_strict_protocol_data_20260609" / "sasrec_format_train_strict.csv",
        "strict_valid_csv": LAB_DIR / "runs" / "hstu_strict_protocol_data_20260609" / "sasrec_format_valid_strict.csv",
        "strict_test_csv": LAB_DIR / "runs" / "hstu_strict_protocol_data_20260609" / "sasrec_format_test_strict.csv",
    }
    local = {name: sha256_file(path) for name, path in local_paths.items()}
    try:
        wsl = subprocess.run(
            [
                "wsl",
                "-d",
                "Ubuntu-20.04",
                "--",
                "bash",
                "-lc",
                "test -f /mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/hstu_blair_wsl/train_strict_hstu_sm120_wsl.sh && "
                "test -f /mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/hstu_blair_wsl/export_strict_hstu_records_sm120_wsl.sh && "
                "test -x $HOME/.bestrec_hstu_blair/venv_py39_sm120/bin/python && "
                "test -d $HOME/.bestrec_hstu_blair/HSTU-BLaIR && "
                "echo ok",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        wsl_report = {
            "returncode": wsl.returncode,
            "stdout": wsl.stdout.strip(),
            "stderr": wsl.stderr.strip(),
            "ok": wsl.returncode == 0 and "ok" in wsl.stdout,
        }
    except Exception as exc:
        wsl_report = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    return {
        "local": local,
        "local_ok": all(record.get("exists") for record in local.values()),
        "wsl": wsl_report,
        "ok": all(record.get("exists") for record in local.values()) and bool(wsl_report.get("ok")),
    }


def select_jobs(jobs: list[dict[str, Any]], seed: int | None, component: str | None) -> list[dict[str, Any]]:
    selected = []
    for job in jobs:
        if seed is not None and int(job["seed"]) != seed:
            continue
        if component and str(job["component"]) != component:
            continue
        selected.append(job)
    return selected


def append_status(status_path: Path, payload: dict[str, Any]) -> None:
    status_path.parent.mkdir(parents=True, exist_ok=True)
    with status_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def dependency_problems(job: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    for dep in job.get("depends_on", []):
        if not str(dep).startswith("seed"):
            problems.append(f"unsupported dependency key {dep}")
            continue
        seed_part, component = str(dep)[4:].split("_", 1)
        checkpoint = checkpoint_for(int(seed_part), component)
        if not checkpoint.exists():
            problems.append(f"missing dependency checkpoint {checkpoint}")
    return problems


def run_command_logged(command: list[str], log_path: Path) -> dict[str, Any]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    started = utc_now()
    with log_path.open("ab") as handle:
        handle.write(("\n=== started_utc " + started + " ===\n").encode("utf-8"))
        handle.write(("command: " + json.dumps(command) + "\n").encode("utf-8"))
        handle.flush()
        result = subprocess.run(command, check=False, stdout=handle, stderr=subprocess.STDOUT)
        finished = utc_now()
        handle.write(("=== finished_utc " + finished + f" returncode {result.returncode} ===\n").encode("utf-8"))
    return {
        "command": command,
        "started_utc": started,
        "finished_utc": finished,
        "returncode": int(result.returncode),
        "log": sha256_file(log_path),
    }


def run_job(job: dict[str, Any], *, status_path: Path, log_dir: Path, force: bool = False) -> dict[str, Any]:
    key = job_key(job)
    expected = Path(job["expected_output"])
    if expected.exists() and not force:
        report = {
            "event": "skip_existing_output",
            "job": key,
            "component": job["component"],
            "seed": int(job["seed"]),
            "timestamp_utc": utc_now(),
            "expected_output": sha256_file(expected),
        }
        append_status(status_path, report)
        return report
    problems = dependency_problems(job)
    if problems:
        report = {
            "event": "blocked_missing_dependencies",
            "job": key,
            "component": job["component"],
            "seed": int(job["seed"]),
            "timestamp_utc": utc_now(),
            "problems": problems,
        }
        append_status(status_path, report)
        raise RuntimeError("; ".join(problems))
    append_status(
        status_path,
        {
            "event": "job_started",
            "job": key,
            "component": job["component"],
            "kind": job["kind"],
            "seed": int(job["seed"]),
            "timestamp_utc": utc_now(),
            "expected_output": str(expected),
        },
    )
    command_reports: list[dict[str, Any]] = []
    if job["kind"] == "hstu":
        command_reports.append(run_command_logged(job["train_command"], log_dir / f"{key}_train.log"))
        if command_reports[-1]["returncode"] != 0:
            event = "job_failed_train"
        else:
            command_reports.append(run_command_logged(job["export_command"], log_dir / f"{key}_export.log"))
            event = "job_completed" if command_reports[-1]["returncode"] == 0 and expected.exists() else "job_failed_export"
    else:
        command_reports.append(run_command_logged(job["command"], log_dir / f"{key}.log"))
        event = "job_completed" if command_reports[-1]["returncode"] == 0 and expected.exists() else "job_failed"
    report = {
        "event": event,
        "job": key,
        "component": job["component"],
        "kind": job["kind"],
        "seed": int(job["seed"]),
        "timestamp_utc": utc_now(),
        "commands": command_reports,
        "expected_output": sha256_file(expected),
    }
    append_status(status_path, report)
    if event != "job_completed":
        raise RuntimeError(f"{key} did not complete; event={event}")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", default=str(DEFAULT_PROTOCOL))
    parser.add_argument("--manifest-out", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--status-out", default=str(DEFAULT_STATUS))
    parser.add_argument("--log-dir", default=str(DEFAULT_LOG_DIR))
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--component", choices=["dev4", "dev5", "dev9", "dev10", "dev13", "sasrec"], default=None)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--print-commands", action="store_true")
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()

    protocol_path = Path(args.protocol)
    protocol = read_json(protocol_path)
    seeds = [int(value) for value in protocol["fresh_confirmatory_seeds"]]
    jobs = build_jobs(seeds)
    write_manifest(Path(args.manifest_out), protocol, jobs)
    selected = select_jobs(jobs, args.seed, args.component)
    preflight_report = preflight() if args.preflight else None
    if args.print_commands:
        for job in selected:
            print(json.dumps({"job": job_key(job), "kind": job["kind"], "expected_output": job["expected_output"]}, sort_keys=True))
            if job["kind"] == "hstu":
                print(" ".join(job["train_command"]))
                print(" ".join(job["export_command"]))
            else:
                print(" ".join(job["command"]))
    if args.execute:
        if not selected:
            raise SystemExit("No jobs selected.")
        if args.seed is None or args.component is None:
            raise SystemExit("--execute requires both --seed and --component to avoid accidental full sweeps.")
        for job in selected:
            try:
                run_job(job, status_path=Path(args.status_out), log_dir=Path(args.log_dir), force=args.force)
            except RuntimeError as exc:
                print(
                    json.dumps(
                        {
                            "status": "job_not_completed",
                            "job": job_key(job),
                            "error": str(exc),
                            "status_log": str(Path(args.status_out)),
                        },
                        indent=2,
                        sort_keys=True,
                    )
                )
                return 2
    print(
        json.dumps(
            {
                "status": "manifest_written",
                "manifest": str(Path(args.manifest_out)),
                "job_count": len(jobs),
                "selected_jobs": [job_key(job) for job in selected],
                "execute": bool(args.execute),
                "force": bool(args.force),
                "status_log": str(Path(args.status_out)),
                "log_dir": str(Path(args.log_dir)),
                "preflight": preflight_report,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
