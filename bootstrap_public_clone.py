# -*- coding: utf-8 -*-
"""Fresh-public-clone bootstrap (audit 2026-07-20 16:53): downloads every release-class
asset named by RELEASE_MANIFEST.json to its canonical local path and hash-verifies it.
Usage:  git clone <repo> && cd <repo> && git submodule update --init
        python bootstrap_public_clone.py
        _bestrec_run/.venv (or your env) -> rebuild_hstu_submission.py --strict
"""
import hashlib
import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
URL = ("https://github.com/Ray0419/bestrec-sota-results/releases/download/"
       "v0.9-audit-evidence/")
DEST = {
    "splits": os.path.join("data_5core", "5core", "last_out"),
    "text_caches": "cache_5core",
    "tfv2_sidecars": os.path.join("_bestrec_run",),
}

def main():
    m = json.load(open(os.path.join(ROOT, "RELEASE_MANIFEST.json"), encoding="utf-8"))
    ok = bad = 0
    for sec, sub in DEST.items():
        for key, ent in m.get(sec, {}).items():
            name = key + ".csv" if sec == "splits" else key
            dst_dir = os.path.join(ROOT, sub)
            os.makedirs(dst_dir, exist_ok=True)
            dst = os.path.join(dst_dir, os.path.basename(name))
            if os.path.exists(dst):
                h = hashlib.sha256(open(dst, "rb").read()).hexdigest()
                if h == ent["sha256"]:
                    ok += 1
                    continue
                print("LOCAL HASH MISMATCH (refusing to overwrite):", dst)
                bad += 1
                continue
            try:
                print("fetching", name, f"({ent['bytes']:,} bytes)")
                h = hashlib.sha256()
                with urllib.request.urlopen(URL + os.path.basename(name), timeout=300) as r, \
                        open(dst + ".part", "wb") as f:
                    for chunk in iter(lambda: r.read(1 << 20), b""):
                        f.write(chunk)
                        h.update(chunk)
                if h.hexdigest() != ent["sha256"]:
                    os.remove(dst + ".part")
                    print("REMOTE HASH MISMATCH:", name)
                    bad += 1
                    continue
                os.replace(dst + ".part", dst)
                ok += 1
            except Exception as e:
                print("FETCH FAILED:", name, e)
                bad += 1
    print(f"bootstrap: {ok} assets in place, {bad} failures")
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())
