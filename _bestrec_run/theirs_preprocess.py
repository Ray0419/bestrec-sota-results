#!/usr/bin/env python
"""Run HSTU-BLaIR's OWN preprocessing pipeline locally (their repo, our env).

Runs external/HSTU-BLaIR (commit 40a27879) AmazonDataProcessor.preprocess_rating
with text_embedding_model="blair" for a chosen dataset, writing their standard
layout under _bestrec_run/theirs_runs/tmp/<prefix>/:
    sasrec_format.csv                      (training/eval CSV, their format)
    data_maps                              (user2id/item2id/id2item/id2meta)
    item_text_embeddings_blair.pt          (BLaIR item embeddings, row 0 = pad)

TWO MONKEYPATCHES (from our side; their repo files untouched), both pure data
ACQUISITION plumbing -- the transformation/filtering/remapping/embedding logic
is their unmodified code:

 1. AmazonDataProcessor.download
    Their shipped download() unconditionally raises
    ValueError("Unknown archive type ...") because _saved_name is
    'tmp/<X>.csv' (doesn't end with '.csv.gz'), i.e. the given path is broken
    as shipped. Replacement: fetch the SAME URL they hardcode
    (https://mcauleylab.ucsd.edu/.../5core/rating_only/<X>.csv.gz), save the
    .gz, extract to their expected 'tmp/<X>.csv'. SHA256s recorded.

 2. AmazonDataProcessor.process_meta
    Their version loads HF dataset 'McAuley-Lab/Amazon-Reviews-2023'
    (raw_meta_<domain>) via a dataset loading SCRIPT with trust_remote_code —
    unsupported by modern `datasets` (script datasets removed). Replacement:
    read the SAME McAuley-Lab raw metadata jsonl already on local disk and
    apply THEIR OWN clean_metadata() (imported from their
    generative_recommenders.research.data.utils) per record, producing the
    identical dict(parent_asin -> cleaned_metadata).

The dataset-level assertion in THEIR code
(expected_num_unique_items: office=77551, music=24587, game=25612) remains
active and validates that this replication lands on exactly their corpus.

Usage:
  _bestrec_run/.venv/Scripts/python _bestrec_run/theirs_preprocess.py amzn23_office
"""
from __future__ import annotations

import gzip
import hashlib
import json
import logging
import os
import shutil
import sys
import time
from urllib.request import urlretrieve

HERE = os.path.dirname(os.path.abspath(__file__))            # _bestrec_run
ROOT = os.path.dirname(HERE)                                  # repo root
THEIRS = os.path.join(ROOT, "external", "HSTU-BLaIR")
RUNROOT = os.path.join(HERE, "theirs_runs")                   # cwd for their relative paths

# Local copies of the McAuley-Lab Amazon-Reviews-2023 raw metadata jsonl
# (same artifact the HF raw_meta_<domain> configs serve).
META_JSONL = {
    "amzn23_office": os.path.join(ROOT, "data_raw_proper", "office", "meta_Office_Products.jsonl"),
    "amzn23_music": os.path.join(ROOT, "data", "instruments", "meta_Musical_Instruments.jsonl"),
    "amzn23_game": os.path.join(ROOT, "data_raw_proper", "video_games", "meta_Video_Games.jsonl"),
}


def sha256(path: str, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def main() -> int:
    assert len(sys.argv) == 2 and sys.argv[1] in META_JSONL, \
        f"usage: theirs_preprocess.py {{{'|'.join(META_JSONL)}}}"
    prefix = sys.argv[1]

    os.makedirs(RUNROOT, exist_ok=True)
    os.chdir(RUNROOT)                       # their code writes to relative tmp/
    os.makedirs("tmp", exist_ok=True)
    sys.path.insert(0, THEIRS)

    logging.basicConfig(stream=sys.stdout, level=logging.INFO)

    from generative_recommenders.research.data import preprocessor as prep_mod
    from generative_recommenders.research.data.utils import clean_metadata  # THEIR fn

    provenance: dict = {
        "dataset": prefix,
        "their_repo_commit": "40a27879ec22648657b5abc77915a7cc88c66cfd",
        "monkeypatches": ["AmazonDataProcessor.download", "AmazonDataProcessor.process_meta"],
        "files": {},
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    # ---- patch 1: working download of their hardcoded URL -----------------
    def download_fixed(self) -> None:
        csv_path = self._saved_name                      # e.g. tmp/Office_Products.csv
        gz_path = csv_path + ".gz"
        if not os.path.isfile(csv_path):
            if not os.path.isfile(gz_path):
                logging.info(f"Downloading {self._download_path} -> {gz_path}")
                urlretrieve(self._download_path, gz_path)
            provenance["files"][gz_path] = {"sha256": sha256(gz_path),
                                            "source_url": self._download_path}
            logging.info(f"Extracting {gz_path} -> {csv_path}")
            with gzip.open(gz_path, "rb") as f_in, open(csv_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        if gz_path not in provenance["files"] and os.path.isfile(gz_path):
            provenance["files"][gz_path] = {"sha256": sha256(gz_path),
                                            "source_url": self._download_path}
        provenance["files"][csv_path] = {"sha256": sha256(csv_path)}

    # ---- patch 2: metadata from local McAuley jsonl + THEIR clean_metadata -
    def process_meta_local(self):
        meta_path = META_JSONL[self._prefix]
        provenance["files"][meta_path] = {"sha256": sha256(meta_path),
                                          "note": "McAuley-Lab AR2023 raw_meta jsonl (local copy)"}
        needed = ("title", "features", "categories", "description")
        item2meta = {}
        n_null = 0
        t0 = time.time()
        with open(meta_path, encoding="utf-8") as f:
            for i, line in enumerate(f):
                rec = json.loads(line)
                for k in needed:                 # HF json loader would give None
                    if rec.get(k) is None:       # for missing; guard identically
                        rec[k] = ""
                        n_null += 1
                out = clean_metadata(rec)        # THEIR function, unmodified
                item2meta[out["parent_asin"]] = out["cleaned_metadata"]
                if (i + 1) % 200000 == 0:
                    logging.info(f"  meta {i + 1} rows ({time.time() - t0:.0f}s)")
        logging.info(
            f"process_meta_local: {len(item2meta)} items, "
            f"{n_null} null fields patched to '' (expect 0), {time.time() - t0:.0f}s"
        )
        provenance["meta_null_fields_patched"] = n_null
        return item2meta

    prep_mod.AmazonDataProcessor.download = download_fixed
    prep_mod.AmazonDataProcessor.process_meta = process_meta_local

    dp = prep_mod.get_common_preprocessors(text_embedding_model="blair")[prefix]
    t0 = time.time()
    n_items = dp.preprocess_rating()          # THEIR pipeline end-to-end
    dt = time.time() - t0

    for rel in (f"tmp/{prefix}/sasrec_format.csv",
                f"tmp/{prefix}/data_maps",
                f"tmp/{prefix}/item_text_embeddings_blair.pt"):
        if os.path.isfile(rel):
            provenance["files"][rel] = {"sha256": sha256(rel),
                                        "bytes": os.path.getsize(rel)}
    provenance["num_unique_items_returned"] = int(n_items)
    provenance["expected_num_unique_items"] = dp.expected_num_unique_items()
    provenance["elapsed_sec"] = round(dt, 1)
    provenance["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    out_json = os.path.join(RUNROOT, f"preprocess_provenance_{prefix}.json")
    with open(out_json, "w") as f:
        json.dump(provenance, f, indent=2)
    logging.info(f"DONE {prefix}: {n_items} items in {dt:.0f}s; provenance -> {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
