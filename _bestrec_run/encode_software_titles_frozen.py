#!/usr/bin/env python3
"""Build the frozen, outcome-free Software title cache for prospective V2."""

from __future__ import annotations

import csv
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch


ROOT = Path(__file__).resolve().parent.parent
SPLIT_DIR = ROOT / "data_5core" / "5core" / "last_out"
META = ROOT / "data_raw_proper" / "software" / "meta_Software.jsonl"
CACHE_DIR = ROOT / "cache_5core"
EMBEDDINGS = CACHE_DIR / "sbert_titles_Software.npy"
ITEM_MAP = CACHE_DIR / "asin2idx_Software.json"
MANIFEST = ROOT / "_bestrec_run" / "software_title_cache_manifest.json"
FEASIBILITY = ROOT / "_bestrec_run" / "software_feasibility.json"
MODEL = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def split_items() -> list[str]:
    items: set[str] = set()
    for split in ("train", "valid", "test"):
        path = SPLIT_DIR / f"Software.{split}.csv"
        with path.open("r", encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                items.add(row["parent_asin"])
    return sorted(items)


def main() -> int:
    if EMBEDDINGS.exists() or ITEM_MAP.exists() or MANIFEST.exists():
        raise RuntimeError("Software cache output already exists; refusing overwrite")
    feasibility = json.loads(FEASIBILITY.read_text(encoding="utf-8"))
    if feasibility.get("verdict") != "SW-V2-FEASIBLE":
        raise RuntimeError("frozen feasibility gate has not passed")
    items = split_items()
    item_set = set(items)
    titles: dict[str, str] = {}
    with META.open("r", encoding="utf-8") as fh:
        for line in fh:
            record = json.loads(line)
            parent = record.get("parent_asin")
            if parent not in item_set or parent in titles:
                continue
            title = record.get("title") or ""
            if isinstance(title, list):
                title = " ".join(str(part) for part in title)
            titles[parent] = str(title).strip()
    texts = [titles.get(item, "") for item in items]

    from sentence_transformers import SentenceTransformer, __version__ as st_version

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = SentenceTransformer(
        MODEL,
        revision=MODEL_REVISION,
        device=device,
        local_files_only=True,
    )
    embeddings = model.encode(
        texts,
        batch_size=256,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=False,
    ).astype(np.float32, copy=False)
    if embeddings.shape != (len(items), 384) or not np.isfinite(embeddings).all():
        raise RuntimeError(f"unexpected embedding output: shape={embeddings.shape}")

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with EMBEDDINGS.open("xb") as fh:
        np.save(fh, embeddings, allow_pickle=False)
    with ITEM_MAP.open("x", encoding="utf-8", newline="\n") as fh:
        json.dump({item: index for index, item in enumerate(items)}, fh, sort_keys=True)
        fh.write("\n")
    payload = {
        "protocol": "PREREG_FIR_PROSPECTIVE_SW_V2_PREPARATION",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "model": MODEL,
        "model_revision": MODEL_REVISION,
        "device": device,
        "normalization": False,
        "dtype": str(embeddings.dtype),
        "shape": list(embeddings.shape),
        "items": len(items),
        "titles_found": sum(bool(titles.get(item, "")) for item in items),
        "titles_missing_or_empty": sum(not bool(titles.get(item, "")) for item in items),
        "versions": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "torch": torch.__version__,
            "sentence_transformers": st_version,
        },
        "inputs": {
            "metadata": {"path": META.relative_to(ROOT).as_posix(), "sha256": sha256(META)},
            "feasibility": {"path": FEASIBILITY.relative_to(ROOT).as_posix(), "sha256": sha256(FEASIBILITY)},
        },
        "outputs": {
            "embeddings": {
                "path": EMBEDDINGS.relative_to(ROOT).as_posix(),
                "bytes": EMBEDDINGS.stat().st_size,
                "sha256": sha256(EMBEDDINGS),
            },
            "item_map": {
                "path": ITEM_MAP.relative_to(ROOT).as_posix(),
                "bytes": ITEM_MAP.stat().st_size,
                "sha256": sha256(ITEM_MAP),
            },
        },
    }
    with MANIFEST.open("x", encoding="utf-8", newline="\n") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print(json.dumps({
        "verdict": "SW-V2-PREPARED",
        "items": len(items),
        "titles_found": payload["titles_found"],
        "titles_missing_or_empty": payload["titles_missing_or_empty"],
        "shape": payload["shape"],
        "embedding_sha256": payload["outputs"]["embeddings"]["sha256"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
