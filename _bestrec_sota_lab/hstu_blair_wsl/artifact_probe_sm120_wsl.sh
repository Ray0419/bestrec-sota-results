#!/usr/bin/env bash
set -euo pipefail

WORK_DIR="${HSTU_BLAIR_WORK_DIR:-$HOME/.bestrec_hstu_blair}"
SRC="${HSTU_BLAIR_SRC:-$WORK_DIR/HSTU-BLaIR}"
ENV_DIR="${HSTU_BLAIR_SM120_ENV_DIR:-$WORK_DIR/venv_py39_sm120}"

if [[ ! -x "$ENV_DIR/bin/python" ]]; then
  echo "SM120 environment missing: $ENV_DIR" >&2
  exit 2
fi

cd "$SRC"

"$ENV_DIR/bin/python" - <<'PYCODE'
import csv
import hashlib
import json
import subprocess
from pathlib import Path

root = Path.cwd()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git_output(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def file_record(path: Path) -> dict:
    record = {"path": str(path), "exists": path.exists()}
    if path.exists():
        stat = path.stat()
        record.update(
            {
                "size_bytes": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
                "sha256": sha256(path),
            }
        )
    return record


tmp_dir = root / "tmp" / "amzn23_game"
exps_dir = root / "exps" / "amzn23_game-l50"
ckpts_dir = root / "ckpts" / "amzn23_game-l50"
files = [
    root / "configs" / "amzn23_game" / "hstu-sampled-softmax-n512-blair.gin",
    tmp_dir / "sasrec_format.csv",
    tmp_dir / "item_text_embeddings_blair.pt",
    tmp_dir / "item2meta.json",
    tmp_dir / "id2meta.json",
    tmp_dir / "mappings.json",
]

dataset_counts = {}
ratings_path = tmp_dir / "sasrec_format.csv"
if ratings_path.exists():
    item_ids = set()
    rows = 0
    with ratings_path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows += 1
            for raw_id in row.get("sequence_item_ids", "").split(","):
                if raw_id:
                    item_ids.add(raw_id)
    dataset_counts = {
        "sequence_rows": rows,
        "unique_sequence_items": len(item_ids),
        "csv_columns": reader.fieldnames or [],
    }

try:
    import torch

    emb_path = tmp_dir / "item_text_embeddings_blair.pt"
    embedding_info = {}
    if emb_path.exists():
        tensor = torch.load(emb_path, map_location="cpu")
        embedding_info = {
            "shape": list(tensor.shape) if hasattr(tensor, "shape") else None,
            "dtype": str(getattr(tensor, "dtype", "")),
        }
except Exception as exc:
    embedding_info = {"load_error": repr(exc)}

exp_dirs = []
if exps_dir.exists():
    for path in sorted(p for p in exps_dir.iterdir() if p.is_dir()):
        exp_dirs.append(
            {
                "path": str(path),
                "mtime_ns": path.stat().st_mtime_ns,
                "event_files": [
                    file_record(child)
                    for child in sorted(path.glob("events.out.tfevents*"))
                ],
            }
        )

ckpts = []
if ckpts_dir.exists():
    ckpts = [
        file_record(path)
        for path in sorted(p for p in ckpts_dir.iterdir() if p.is_file())
    ]

tensorboard_scalar_summary = {}
event_files = []
if exps_dir.exists():
    for path in exps_dir.glob("*/events.out.tfevents*"):
        if path.is_file():
            event_files.append(path)
if event_files:
    latest_event = max(event_files, key=lambda path: path.stat().st_mtime_ns)
    try:
        from tensorboard.backend.event_processing.event_accumulator import (
            EventAccumulator,
        )

        interesting_tags = [
            "eval/ndcg@10",
            "eval/hr@10",
            "eval/mrr",
            "eval_epoch/ndcg@10",
            "eval_epoch/hr@10",
            "eval_epoch/mrr",
            "eval_epoch_full/ndcg@10",
            "eval_epoch_full/hr@10",
            "eval_epoch_full/mrr",
            "loss/train",
        ]
        accumulator = EventAccumulator(
            str(latest_event),
            size_guidance={"scalars": 0},
        )
        accumulator.Reload()
        available_tags = set(accumulator.Tags().get("scalars", []))
        for tag in interesting_tags:
            if tag not in available_tags:
                continue
            scalars = [
                {
                    "step": int(value.step),
                    "value": float(value.value),
                    "wall_time": float(value.wall_time),
                }
                for value in accumulator.Scalars(tag)
            ]
            if not scalars:
                continue
            tensorboard_scalar_summary[tag] = {
                "latest": scalars[-1],
                "best_by_value": max(scalars, key=lambda row: row["value"]),
                "num_points": len(scalars),
                "tail": scalars[-10:],
            }
        tensorboard_scalar_summary["_latest_event_file"] = file_record(latest_event)
    except Exception as exc:
        tensorboard_scalar_summary["_load_error"] = repr(exc)

payload = {
    "source_commit": git_output("rev-parse", "HEAD"),
    "source_status_short": git_output("status", "--short"),
    "source_code_status_short_excluding_outputs": subprocess.check_output(
        [
            "git",
            "status",
            "--short",
            "--",
            ".",
            ":(exclude)tmp",
            ":(exclude)exps",
            ":(exclude)ckpts",
        ],
        cwd=root,
        text=True,
    ).strip(),
    "dataset_counts": dataset_counts,
    "embedding_info": embedding_info,
    "files": [file_record(path) for path in files],
    "experiment_dirs": exp_dirs,
    "checkpoints": ckpts,
    "tensorboard_scalar_summary": tensorboard_scalar_summary,
}
print("HSTU_ARTIFACT_PROBE_JSON=" + json.dumps(payload, sort_keys=True))
PYCODE
