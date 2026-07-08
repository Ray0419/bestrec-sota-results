"""Audit and run the WSL reproduction lane for HSTU-BLaIR.

This wrapper writes evidence under `_bestrec_sota_lab/runs/<run_id>/`.
It does not edit the upstream HSTU-BLaIR checkout. The stages are:

  inspect: WSL/GPU/source feasibility only.
  setup:       install the pinned Linux Python 3.9 HSTU-BLaIR environment.
  smoke:       verify pinned imports/CUDA/upstream entrypoint after setup.
  setup-sm120: install a clearly labelled CUDA 12.8 compatibility environment.
  smoke-sm120: smoke the compatibility environment.

  preprocess-game-sm120: preprocess only amzn23_game with BLaIR embeddings.
  train-game-sm120:      run upstream amzn23_game HSTU-BLaIR training.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LAB_DIR = Path(__file__).resolve().parent
ROOT = LAB_DIR.parent
RUNS_DIR = LAB_DIR / "runs"
HSTU_DIR = ROOT / "external" / "HSTU-BLaIR"
SCRIPT_DIR = LAB_DIR / "hstu_blair_wsl"
WSL_NATIVE_HSTU_DIR = "~/.bestrec_hstu_blair/HSTU-BLaIR"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean_output(text: str | None) -> str:
    if text is None:
        return ""
    return text.replace("\x00", "")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def run_cmd(cmd: list[str], timeout: int) -> dict[str, Any]:
    started_utc = utc_now()
    started = time.monotonic()
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    return {
        "command": cmd,
        "returncode": int(proc.returncode),
        "stdout": clean_output(proc.stdout),
        "stderr": clean_output(proc.stderr),
        "started_utc": started_utc,
        "completed_utc": utc_now(),
        "duration_sec": round(time.monotonic() - started, 3),
    }


def wsl_bash(script: str, timeout: int) -> dict[str, Any]:
    return run_cmd(["wsl", "-d", "Ubuntu-20.04", "--", "bash", "-lc", script], timeout)


def status_from(result: dict[str, Any]) -> str:
    return "passed" if result["returncode"] == 0 else "failed"


EVAL_EPOCH_RE = re.compile(
    r"eval @ epoch (?P<epoch>\d+) in (?P<seconds>[0-9.]+)s: "
    r"NDCG@10 (?P<ndcg10>[0-9.]+), NDCG@50 (?P<ndcg50>[0-9.]+), "
    r"HR@10 (?P<hr10>[0-9.]+), HR@50 (?P<hr50>[0-9.]+), MRR (?P<mrr>[0-9.]+)"
)
BATCH_EVAL_RE = re.compile(
    r"batch-stat \(eval\): iter (?P<iter>\d+) \(epoch (?P<epoch>\d+)\): "
    r"NDCG@10 (?P<ndcg10>[0-9.]+), HR@10 (?P<hr10>[0-9.]+), "
    r"HR@50 (?P<hr50>[0-9.]+), MRR (?P<mrr>[0-9.]+)"
)
PROBE_MARKER = "HSTU_ARTIFACT_PROBE_JSON="


def _float(value: str) -> float:
    return float(value)


def extract_hstu_metrics(*texts: str) -> dict[str, Any]:
    """Extract reviewable metrics from upstream HSTU-BLaIR logs."""
    joined = "\n".join(texts)
    epoch_metrics: list[dict[str, Any]] = []
    for match in EVAL_EPOCH_RE.finditer(joined):
        epoch_metrics.append(
            {
                "epoch": int(match.group("epoch")),
                "eval_seconds": _float(match.group("seconds")),
                "ndcg10": _float(match.group("ndcg10")),
                "ndcg50": _float(match.group("ndcg50")),
                "hr10": _float(match.group("hr10")),
                "hr50": _float(match.group("hr50")),
                "mrr": _float(match.group("mrr")),
                "source": "upstream_stdout_eval_epoch",
            }
        )
    batch_metrics: list[dict[str, Any]] = []
    for match in BATCH_EVAL_RE.finditer(joined):
        batch_metrics.append(
            {
                "iter": int(match.group("iter")),
                "epoch": int(match.group("epoch")),
                "ndcg10": _float(match.group("ndcg10")),
                "hr10": _float(match.group("hr10")),
                "hr50": _float(match.group("hr50")),
                "mrr": _float(match.group("mrr")),
                "source": "upstream_stdout_batch_eval",
            }
        )
    return {
        "eval_epoch_metrics": epoch_metrics,
        "batch_eval_metrics": batch_metrics,
        "final_eval_epoch": epoch_metrics[-1] if epoch_metrics else None,
        "best_eval_epoch_by_ndcg10": max(epoch_metrics, key=lambda row: row["ndcg10"])
        if epoch_metrics
        else None,
    }


def extract_probe_payload(result: dict[str, Any]) -> dict[str, Any] | None:
    for line in result.get("stdout", "").splitlines():
        if line.startswith(PROBE_MARKER):
            return json.loads(line[len(PROBE_MARKER) :])
    return None


def hstu_artifact_probe(timeout: int = 300) -> dict[str, Any]:
    probe = script_stage("artifact_probe_sm120_wsl.sh", timeout)
    probe["payload"] = extract_probe_payload(probe)
    return probe


def inspect_stage(timeout: int) -> dict[str, Any]:
    source_check = run_cmd(["git", "-C", str(HSTU_DIR), "rev-parse", "HEAD"], timeout=30) if HSTU_DIR.exists() else {
        "returncode": 2,
        "stdout": "",
        "stderr": f"missing source dir: {HSTU_DIR}",
        "command": ["git", "-C", str(HSTU_DIR), "rev-parse", "HEAD"],
    }
    source_status = run_cmd(["git", "-C", str(HSTU_DIR), "status", "--short"], timeout=30) if HSTU_DIR.exists() else {
        "returncode": 2,
        "stdout": "",
        "stderr": f"missing source dir: {HSTU_DIR}",
        "command": ["git", "-C", str(HSTU_DIR), "status", "--short"],
    }
    wsl_status = run_cmd(["wsl", "--status"], timeout=30)
    wsl_list = run_cmd(["wsl", "-l", "-v"], timeout=30)
    wsl_probe = wsl_bash(
        r"""
set -euo pipefail
echo "uname=$(uname -a)"
echo "pwd=$(pwd)"
echo "python3=$(python3 --version 2>&1 || true)"
echo "pip3=$(python3 -m pip --version 2>&1 || true)"
echo "curl=$(command -v curl || true)"
echo "uv=$(command -v uv || true)"
echo "uv_home=$([ -x ~/.local/bin/uv ] && ~/.local/bin/uv --version || true)"
echo "gcc=$(command -v gcc || true)"
echo "g++=$(command -v g++ || true)"
echo "git=$(command -v git || true)"
echo "nvidia_smi=$(command -v nvidia-smi || true)"
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
python3 -c "import multiprocessing as mp; print('mp_methods=' + ','.join(mp.get_all_start_methods()))"
test -d /mnt/c/Users/rayxc/Documents/R/external/HSTU-BLaIR
test -f /mnt/c/Users/rayxc/Documents/R/external/HSTU-BLaIR/requirements.txt
echo "hstu_commit=$(git -C /mnt/c/Users/rayxc/Documents/R/external/HSTU-BLaIR rev-parse HEAD)"
echo "hstu_wsl_status_count=$(git -C /mnt/c/Users/rayxc/Documents/R/external/HSTU-BLaIR status --short | wc -l)"
if [ -d "$HOME/.bestrec_hstu_blair/HSTU-BLaIR/.git" ]; then
  echo "native_hstu_commit=$(git -C "$HOME/.bestrec_hstu_blair/HSTU-BLaIR" rev-parse HEAD)"
  echo "native_hstu_status_count=$(git -C "$HOME/.bestrec_hstu_blair/HSTU-BLaIR" status --short | wc -l)"
else
  echo "native_hstu_missing=true"
fi
""",
        timeout,
    )
    return {
        "wsl_status": wsl_status,
        "wsl_list": wsl_list,
        "wsl_probe": wsl_probe,
        "source_commit": source_check,
        "source_status": source_status,
    }


def to_wsl_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/").replace("C:/", "/mnt/c/")


def script_stage(script_name: str, timeout: int, log_path: Path | None = None) -> dict[str, Any]:
    script_path = SCRIPT_DIR / script_name
    if not script_path.exists():
        return {
            "command": ["missing", str(script_path)],
            "returncode": 2,
            "stdout": "",
            "stderr": f"missing script: {script_path}",
        }
    wsl_script = str(script_path).replace("\\", "/").replace("C:/", "/mnt/c/")
    if log_path is None:
        return wsl_bash(f"bash {wsl_script}", timeout)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    wsl_log = to_wsl_path(log_path)
    return wsl_bash(f"set -o pipefail; bash {wsl_script} 2>&1 | tee {wsl_log}", timeout)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stage",
        choices=[
            "inspect",
            "setup",
            "smoke",
            "setup-sm120",
            "smoke-sm120",
            "preprocess-game-sm120",
            "train-game-sm120",
        ],
        default="inspect",
    )
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--timeout", type=int, default=1800)
    args = parser.parse_args()

    run_id = args.run_id or f"hstu_blair_wsl_{args.stage}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    audit_path = run_dir / "hstu_blair_wsl_audit.json"
    audit: dict[str, Any] = {
        "schema_version": 1,
        "run_id": run_id,
        "method": "hstu_blair",
        "stage": args.stage,
        "status": "running",
        "generated_utc": utc_now(),
        "source_dir": str(HSTU_DIR),
        "wsl_native_source_dir": WSL_NATIVE_HSTU_DIR,
        "wsl_distro": "Ubuntu-20.04",
        "publication_grade_records": False,
        "compatibility_mode": "sm120_cuda128_port" if args.stage.endswith("sm120") else "upstream_pinned",
        "reported_external_reference": {
            "source": "https://github.com/snapfinger/HSTU-BLaIR",
            "video_games_ndcg10": 0.0760,
        },
        "notes": [
            "This is an external comparator reproduction lane, not a proxy.",
            "SOTA claims remain blocked until protocol-matched canonical records exist or a defensible protocol mismatch is documented.",
        ],
    }
    write_json(audit_path, audit)

    if args.stage == "inspect":
        audit["checks"] = inspect_stage(args.timeout)
        failed = [name for name, result in audit["checks"].items() if result.get("returncode") not in (0, None)]
    elif args.stage == "setup":
        audit["checks"] = {"setup": script_stage("setup_hstu_blair_wsl.sh", args.timeout)}
        failed = ["setup"] if audit["checks"]["setup"]["returncode"] != 0 else []
    elif args.stage == "smoke":
        audit["checks"] = {"smoke": script_stage("smoke_hstu_blair_wsl.sh", args.timeout)}
        failed = ["smoke"] if audit["checks"]["smoke"]["returncode"] != 0 else []
    elif args.stage == "setup-sm120":
        audit["checks"] = {"setup_sm120": script_stage("setup_hstu_blair_sm120_wsl.sh", args.timeout)}
        failed = ["setup_sm120"] if audit["checks"]["setup_sm120"]["returncode"] != 0 else []
    elif args.stage == "smoke-sm120":
        audit["checks"] = {
            "smoke_sm120": wsl_bash(
                "HSTU_BLAIR_ENV_DIR=$HOME/.bestrec_hstu_blair/venv_py39_sm120 "
                "bash /mnt/c/Users/rayxc/Documents/R/_bestrec_sota_lab/hstu_blair_wsl/smoke_hstu_blair_wsl.sh",
                args.timeout,
            )
        }
        failed = ["smoke_sm120"] if audit["checks"]["smoke_sm120"]["returncode"] != 0 else []
    elif args.stage == "preprocess-game-sm120":
        audit["checks"] = {
            "preprocess_game_sm120": script_stage(
                "preprocess_game_sm120_wsl.sh",
                args.timeout,
                run_dir / "preprocess_game_sm120.log",
            )
        }
        failed = ["preprocess_game_sm120"] if audit["checks"]["preprocess_game_sm120"]["returncode"] != 0 else []
    else:
        audit["checks"] = {
            "train_game_sm120": script_stage(
                "train_game_sm120_wsl.sh",
                args.timeout,
                run_dir / "train_game_sm120.log",
            )
        }
        failed = ["train_game_sm120"] if audit["checks"]["train_game_sm120"]["returncode"] != 0 else []

    if args.stage in {"preprocess-game-sm120", "train-game-sm120"}:
        primary_check = next(iter(audit["checks"].values()))
        audit["artifact_probe"] = hstu_artifact_probe()
        audit["checks"]["artifact_probe"] = audit["artifact_probe"]
        if audit["artifact_probe"]["returncode"] != 0:
            failed.append("artifact_probe")
        if args.stage == "train-game-sm120":
            audit["extracted_metrics"] = extract_hstu_metrics(
                primary_check.get("stdout", ""),
                primary_check.get("stderr", ""),
            )
            final_metric = audit["extracted_metrics"].get("final_eval_epoch")
            if final_metric is not None:
                audit["reported_metric_from_stdout"] = {
                    "dataset": "amzn23_game",
                    "candidate_scope": "upstream_hstu_blair_eval_protocol",
                    "ndcg10": final_metric["ndcg10"],
                    "hr10": final_metric["hr10"],
                    "mrr": final_metric["mrr"],
                    "epoch": final_metric["epoch"],
                    "source": "parsed upstream stdout; not canonical BEST-Rec JSONL",
                }
            tensorboard_summary = (
                audit["artifact_probe"]
                .get("payload", {})
                .get("tensorboard_scalar_summary", {})
            )
            tb_ndcg = tensorboard_summary.get("eval_epoch_full/ndcg@10") or tensorboard_summary.get(
                "eval_epoch/ndcg@10"
            )
            tb_hr = tensorboard_summary.get("eval_epoch_full/hr@10") or tensorboard_summary.get(
                "eval_epoch/hr@10"
            )
            tb_mrr = tensorboard_summary.get("eval_epoch_full/mrr") or tensorboard_summary.get(
                "eval_epoch/mrr"
            )
            if tb_ndcg and not audit.get("reported_metric_from_stdout"):
                audit["reported_metric_from_tensorboard"] = {
                    "dataset": "amzn23_game",
                    "candidate_scope": "upstream_hstu_blair_eval_protocol",
                    "ndcg10": tb_ndcg["latest"]["value"],
                    "hr10": tb_hr["latest"]["value"] if tb_hr else None,
                    "mrr": tb_mrr["latest"]["value"] if tb_mrr else None,
                    "epoch_or_step": tb_ndcg["latest"]["step"],
                    "source": "parsed upstream TensorBoard event file; not canonical BEST-Rec JSONL",
                    "event_file": tensorboard_summary.get("_latest_event_file", {}).get("path"),
                }

    audit["status"] = "failed" if failed else "complete"
    audit["failed_checks"] = failed
    audit["completed_utc"] = utc_now()
    write_json(audit_path, audit)
    print(f"HSTU-BLaIR WSL audit: {audit_path}")
    print(f"Status: {audit['status']}")
    if failed:
        for name in failed:
            result = audit["checks"][name]
            print(f"\n[{name}] stderr:\n{result.get('stderr', '')}")
            print(f"\n[{name}] stdout:\n{result.get('stdout', '')}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
