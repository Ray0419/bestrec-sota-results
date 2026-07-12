#!/usr/bin/env python
"""Data prep for the IMPACT program's FIR-BREADTH categories (PREREG_FIR_BREADTH.md).

Per category (idempotent; never overwrites an existing verified download):
  1. Download the OFFICIAL McAuley-Lab AR2023 benchmark 5-core rating CSV
     (the same artifact the reference pipeline consumes -- see
     _bestrec_run/theirs_preprocess.py / THEIRS_ON_OURS_REPORT.md S2.3):
       https://mcauleylab.ucsd.edu/public_datasets/data/amazon_2023/benchmark/5core/rating_only/<Cat>.csv.gz
     and the McAuley-Lab raw item metadata jsonl:
       https://mcauleylab.ucsd.edu/public_datasets/data/amazon_2023/raw/meta_categories/meta_<Cat>.jsonl.gz
     into data_raw_proper/<rawdir>/ (existing layout: video_games/, office/, ...).
  2. Record SHA256 + source URL of everything downloaded (and every derived file)
     in data_raw_proper/<rawdir>/provenance_<Cat>.json.
  3. Extract meta jsonl (kept alongside .gz, as for the existing categories).
  4. Convert the rating CSV to the 4-key jsonl records
     (user_id/parent_asin/rating/timestamp) that the paper's standard
     preprocessing script consumes.
  5. Run the UNMODIFIED tracked pipeline `preprocess_5core_standard.process_category`
     (imported; its hardcoded CATEGORIES map is extended in-memory only -- the
     tracked file is not touched). Because the input is already the official
     5-core corpus, the recursive 5-core filter is a stability no-op and the
     script's contribution is the deterministic LLOO split, identical to how
     every other category in the paper was split.
  6. Record users/items/interactions of the resulting split in the provenance json.

Usage:
  _bestrec_run/.venv/Scripts/python -u _bestrec_run/prep_impact_data.py Industrial_and_Scientific industrial_sci
  _bestrec_run/.venv/Scripts/python -u _bestrec_run/prep_impact_data.py CDs_and_Vinyl cds_vinyl
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path
from urllib.request import urlretrieve

HERE = Path(__file__).resolve().parent            # _bestrec_run
ROOT = HERE.parent                                # repo root
RAW_ROOT = ROOT / "data_raw_proper"
SPLIT_DIR = ROOT / "data_5core" / "5core" / "last_out"

BENCH_URL = ("https://mcauleylab.ucsd.edu/public_datasets/data/amazon_2023/"
             "benchmark/5core/rating_only/{cat}.csv.gz")
META_URL = ("https://mcauleylab.ucsd.edu/public_datasets/data/amazon_2023/"
            "raw/meta_categories/meta_{cat}.jsonl.gz")


def sha256(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def gzip_ok(path: Path) -> bool:
    try:
        with gzip.open(path, "rb") as f:
            while f.read(1 << 22):
                pass
        return True
    except Exception:
        return False


def download(url: str, dest: Path) -> None:
    if dest.exists() and gzip_ok(dest):
        print(f"  [dl] {dest.name} already present + gzip-valid; keeping (never overwrite)")
        return
    if dest.exists():
        quarantine = dest.with_suffix(dest.suffix + f".corrupt.{int(time.time())}")
        print(f"  [dl] {dest.name} present but gzip-INVALID -> renaming to {quarantine.name}")
        dest.rename(quarantine)
    part = dest.with_suffix(dest.suffix + ".part")
    print(f"  [dl] {url}\n       -> {dest}")
    t0 = time.time()
    urlretrieve(url, part)
    if not gzip_ok(part):
        raise RuntimeError(f"downloaded file failed gzip integrity check: {part}")
    part.rename(dest)
    print(f"       {dest.stat().st_size/1e6:.1f} MB in {time.time()-t0:.0f}s")


def csv_gz_to_jsonl(csv_gz: Path, jsonl_out: Path) -> int:
    """Official 5-core rating CSV (user_id,parent_asin,rating,timestamp) -> the
    4-key jsonl records preprocess_5core_standard.load_ratings expects."""
    if jsonl_out.exists():
        print(f"  [cv] {jsonl_out.name} already exists; keeping")
        with open(jsonl_out, "rb") as f:
            return sum(1 for _ in f)
    tmp = jsonl_out.with_suffix(".part")
    n = 0
    with gzip.open(csv_gz, "rt", encoding="utf-8", newline="") as fin, \
            open(tmp, "w", encoding="utf-8") as fout:
        rdr = csv.DictReader(fin)
        assert set(rdr.fieldnames) >= {"user_id", "parent_asin", "rating", "timestamp"}, \
            f"unexpected CSV columns: {rdr.fieldnames}"
        for r in rdr:
            fout.write(json.dumps({
                "user_id": r["user_id"], "parent_asin": r["parent_asin"],
                "rating": float(r["rating"]), "timestamp": int(r["timestamp"]),
            }) + "\n")
            n += 1
    tmp.rename(jsonl_out)
    print(f"  [cv] wrote {jsonl_out.name}: {n:,} records")
    return n


def split_stats(cat: str) -> dict:
    st = {}
    total = 0
    users = items = None
    for sp in ("train", "valid", "test"):
        p = SPLIT_DIR / f"{cat}.{sp}.csv"
        with open(p, encoding="utf-8", newline="") as f:
            rows = sum(1 for _ in f) - 1     # minus header
        st[sp] = {"rows": rows, "sha256": sha256(p)}
        total += rows
    uset, iset = set(), set()
    for sp in ("train", "valid", "test"):
        with open(SPLIT_DIR / f"{cat}.{sp}.csv", encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                uset.add(r["user_id"]); iset.add(r["parent_asin"])
    st["n_users"] = len(uset)
    st["n_items"] = len(iset)
    st["n_interactions_total"] = total
    return st


def main() -> int:
    assert len(sys.argv) == 3, "usage: prep_impact_data.py <Category> <raw_subdir>"
    cat, rawdir = sys.argv[1], sys.argv[2]
    d = RAW_ROOT / rawdir
    d.mkdir(parents=True, exist_ok=True)
    prov_path = d / f"provenance_{cat}.json"
    prov = json.load(open(prov_path)) if prov_path.exists() else {}
    prov.setdefault("category", cat)
    prov.setdefault("created_utc", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    prov["updated_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    prov.setdefault("files", {})

    # 1. downloads --------------------------------------------------------
    csv_gz = d / f"{cat}.csv.gz"
    meta_gz = d / f"meta_{cat}.jsonl.gz"
    bench_url = BENCH_URL.format(cat=cat)
    meta_url = META_URL.format(cat=cat)
    download(bench_url, csv_gz)
    download(meta_url, meta_gz)
    prov["files"][csv_gz.name] = {"sha256": sha256(csv_gz), "bytes": csv_gz.stat().st_size,
                                  "source_url": bench_url,
                                  "note": "official AR2023 benchmark 5-core rating_only CSV "
                                          "(same source the reference pipeline downloads)"}
    prov["files"][meta_gz.name] = {"sha256": sha256(meta_gz), "bytes": meta_gz.stat().st_size,
                                   "source_url": meta_url,
                                   "note": "McAuley-Lab AR2023 raw item metadata jsonl"}
    json.dump(prov, open(prov_path, "w"), indent=2)   # checkpoint after downloads

    # 2. extract meta ------------------------------------------------------
    meta_jsonl = d / f"meta_{cat}.jsonl"
    if not meta_jsonl.exists():
        print(f"  [gz] extracting {meta_gz.name} -> {meta_jsonl.name}")
        with gzip.open(meta_gz, "rb") as fin, open(meta_jsonl, "wb") as fout:
            shutil.copyfileobj(fin, fout, 1 << 22)
    prov["files"][meta_jsonl.name] = {"sha256": sha256(meta_jsonl),
                                      "bytes": meta_jsonl.stat().st_size,
                                      "derived_from": meta_gz.name}

    # 3. csv -> jsonl ------------------------------------------------------
    jsonl = d / f"{cat}.jsonl"
    n_raw = csv_gz_to_jsonl(csv_gz, jsonl)
    prov["files"][jsonl.name] = {"sha256": sha256(jsonl), "bytes": jsonl.stat().st_size,
                                 "rows": n_raw, "derived_from": csv_gz.name,
                                 "note": "lossless csv->jsonl record conversion for "
                                         "preprocess_5core_standard.load_ratings"}
    json.dump(prov, open(prov_path, "w"), indent=2)

    # 4. standard preprocessing (tracked script, imported unmodified) ------
    need = [SPLIT_DIR / f"{cat}.{sp}.csv" for sp in ("train", "valid", "test")]
    if all(p.exists() for p in need):
        print(f"  [pp] split CSVs already exist for {cat}; keeping (never overwrite)")
    else:
        sys.path.insert(0, str(HERE))
        import preprocess_5core_standard as pp
        pp.CATEGORIES[cat] = (f"../data_raw_proper/{rawdir}", f"{cat}.jsonl")
        prov["preprocess"] = {
            "script": "_bestrec_run/preprocess_5core_standard.py",
            "script_sha256": sha256(HERE / "preprocess_5core_standard.py"),
            "categories_entry_injected_in_memory": pp.CATEGORIES[cat],
            "k": 5,
        }
        pp.process_category(cat, k=5)

    # 5. record split stats -------------------------------------------------
    print("  [st] computing split stats + hashes...")
    prov["split"] = split_stats(cat)
    prov["split"]["note"] = ("input was the official benchmark 5-core corpus, so the "
                             "recursive 5-core filter is a stability no-op; this records "
                             "the LLOO split actually consumed by run_sasrec_sbert.py")
    json.dump(prov, open(prov_path, "w"), indent=2)
    s = prov["split"]
    print(f"\n  {cat}: users={s['n_users']:,} items={s['n_items']:,} "
          f"interactions={s['n_interactions_total']:,} "
          f"(train {s['train']['rows']:,} / valid {s['valid']['rows']:,} / test {s['test']['rows']:,})")
    print(f"  provenance -> {prov_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
