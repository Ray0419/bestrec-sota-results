#!/usr/bin/env python
"""RELEASE_MANIFEST.json maintenance (round-3 audit F1/F3: keep the manifest
mechanically in sync with the submitted tree instead of chasing HEAD by hand).

    python _bestrec_run/update_release_manifest.py --verify
    python _bestrec_run/update_release_manifest.py --regen

--verify (run by rebuild_hstu_submission.py --strict): recompute the SHA256 of
every manifested file and FAIL (exit 2) on any mismatch, or on any missing
file that is tracked in git (protocol_code, submission_docs, result_families).
Files distributed only as release assets (splits, text_caches, pinned-parity
scratch) may be absent locally: reported as SKIPPED-missing, not a failure.

--regen: re-verify the immutable data sections byte-for-byte (abort on drift
-- released evidence must never change), recompute protocol_code and
submission_docs hashes, refresh pinned_parity_artifacts, and stamp the current
HEAD. Ritual: edit files -> render PDF -> --regen -> commit everything
together; the strict wrapper's --verify then passes at that commit and every
later commit that leaves manifested files untouched (and fails closed the
moment one changes without a --regen).

The manifest cannot hash itself; its own commit is the child of the state it
describes. RELEASE_MANIFEST.json is therefore excluded from its own sections.
"""
import argparse
import hashlib
import io
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MPATH = os.path.join(ROOT, "RELEASE_MANIFEST.json")

SUBMISSION_DOCS = [
    "PAPER_SUBMISSION.md", "PAPER_SUBMISSION.pdf", "PAPER_DRAFT.md",
    "CANONICAL_SUBMISSION.md", "THEIRS_ON_OURS_REPORT.md",
    "PINNED_ENV_PARITY_REPORT.md", "HSTU_PARITY_REPORT.md",
    "_bestrec_run/test_hstu_parity.py", "_bestrec_run/test_pinned_env_parity.py",
    "_bestrec_run/fbgemm_shims.py", "_bestrec_run/rebuild_hstu_submission.py",
    "_bestrec_run/update_release_manifest.py",
    # generated TORS LaTeX (derived output, VENUE_PLAN.md) + its table generator
    "paper_tex/PAPER_TORS.pdf", "_bestrec_run/emit_latex_tables.py",
]
# reference-implementation local runs (git-tracked source artifacts)
REFERENCE_RUN_DIRS = ["_bestrec_run/theirs_runs/music_hstu_blair",
                      "_bestrec_run/theirs_runs/office_sasrec_final",
                      "_bestrec_run/theirs_runs/office_hstu_blair"]
REFERENCE_RUN_LOGS = ["_bestrec_run/theirs_runs/music_hstu_blair.log",
                      "_bestrec_run/theirs_runs/office_sasrec_final.log",
                      "_bestrec_run/theirs_runs/office_hstu_blair.log"]
PINNED_PARITY_DIR = "_bestrec_run/theirs_runs/tmp/pinned_parity"
PINNED_PARITY_FILES = [
    "inenv_results.json", "replay_results_Linux-torch2.2.2pcpu-shims.json",
    "replay_results_Windows-torch2.11.0pcu128-shims.json",
    "pinned_ops.pt", "pinned_block.pt", "pinned_pip_freeze.txt",
    "setup_pinned_env.sh", "negative_control.py", "negative_control.log",
]
# sections whose files ship only as v0.9-audit-evidence release assets
RELEASE_ASSET_SECTIONS = {"splits", "text_caches", "pinned_parity_artifacts"}


def sha(p, _bufsz=1 << 20):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while True:
            b = f.read(_bufsz)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def build_index():
    skip = {".git", ".venv", "node_modules", "external", "ckpts", "tb",
            "_release", "archive_noncanonical", "__pycache__", "exps"}
    idx = {}
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames
                       if d not in skip and not (d == "tmp" and "theirs_runs" not in dirpath)]
        for fn in filenames:
            idx.setdefault(fn, []).append(os.path.join(dirpath, fn))
    return idx


def locate(idx, key):
    cands = list(idx.get(key, []))
    for fn, paths in idx.items():
        if fn != key and fn.startswith(key + "."):
            cands.extend(paths)
    return cands


def head_commit():
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                   text=True).strip()


def verify(m):
    idx = build_index()
    bad, missing_asset = [], []
    checked = 0

    def check_named(section, key, digest):
        nonlocal checked
        cands = locate(idx, key)
        if not cands:
            (missing_asset if section in RELEASE_ASSET_SECTIONS else bad).append(
                f"{section}/{key}: MISSING" +
                ("" if section in RELEASE_ASSET_SECTIONS else " (git-tracked file)"))
            return
        if any(sha(c) == digest for c in cands):
            checked += 1
        else:
            bad.append(f"{section}/{key}: hash mismatch vs manifest")

    for sec in ("splits", "text_caches"):
        for key, ent in m.get(sec, {}).items():
            check_named(sec, key, ent["sha256"])
    for rel, ent in m.get("protocol_code", {}).items():
        ap = os.path.join(ROOT, rel)
        if not os.path.exists(ap):
            bad.append(f"protocol_code/{rel}: MISSING")
        elif sha(ap) != ent["sha256"]:
            bad.append(f"protocol_code/{rel}: hash mismatch vs manifest")
        else:
            checked += 1
    for rel, ent in m.get("submission_docs", {}).items():
        ap = os.path.join(ROOT, rel)
        if not os.path.exists(ap):
            bad.append(f"submission_docs/{rel}: MISSING")
        elif sha(ap) != ent["sha256"]:
            bad.append(f"submission_docs/{rel}: hash mismatch vs manifest "
                       "(edit without --regen?)")
        else:
            checked += 1
    for fam, files in m.get("result_families", {}).items():
        for fn, digest in files.items():
            check_named(f"result_families/{fam}", fn, digest)
    for rel, ent in m.get("reference_runs", {}).get("files", {}).items():
        ap = os.path.join(ROOT, rel)
        if not os.path.exists(ap):
            bad.append(f"reference_runs/{rel}: MISSING (git-tracked file)")
        elif sha(ap) != ent["sha256"]:
            bad.append(f"reference_runs/{rel}: hash mismatch vs manifest")
        else:
            checked += 1
    for fn, ent in m.get("pinned_parity_artifacts", {}).get("files", {}).items():
        ap = os.path.join(ROOT, PINNED_PARITY_DIR, fn)
        if not os.path.exists(ap):
            missing_asset.append(f"pinned_parity_artifacts/{fn}: not on disk "
                                 "(regenerable scratch; archived as release asset)")
        elif sha(ap) != ent["sha256"]:
            bad.append(f"pinned_parity_artifacts/{fn}: hash mismatch vs manifest")
        else:
            checked += 1

    for w in missing_asset:
        print("  SKIPPED-missing (release asset):", w)
    if bad:
        print(f"RELEASE MANIFEST VERIFY: FAIL ({len(bad)} problem(s); "
              f"{checked} files verified)")
        for b in bad:
            print("  FAIL:", b)
        print("Fix: rerun `update_release_manifest.py --regen` and commit the "
              "manifest together with the changed files.")
        return 2
    print(f"RELEASE MANIFEST VERIFY: OK ({checked} files verified, "
          f"{len(missing_asset)} release-asset files not local)")
    return 0


def regen(m):
    idx = build_index()
    # immutable data must never drift
    drift = []
    for sec in ("splits", "text_caches"):
        for key, ent in m[sec].items():
            if not any(sha(c) == ent["sha256"] for c in locate(idx, key)):
                drift.append(f"{sec}/{key}")
    for fam, files in m["result_families"].items():
        for fn, digest in files.items():
            if not any(sha(c) == digest for c in idx.get(fn, [])):
                drift.append(f"result_families/{fam}/{fn}")
    if drift:
        print("DATA DRIFT -- ABORTING (released evidence must not change):")
        for d in drift:
            print("  -", d)
        return 2

    changed = []
    for rel, ent in m["protocol_code"].items():
        new = sha(os.path.join(ROOT, rel))
        if new != ent.get("sha256"):
            ent["sha256"] = new
            changed.append(rel)
    docs = {}
    for rel in SUBMISSION_DOCS:
        ap = os.path.join(ROOT, rel)
        if not os.path.exists(ap):
            print("MISSING submission doc:", rel)
            return 2
        docs[rel] = {"sha256": sha(ap), "bytes": os.path.getsize(ap)}
    m["submission_docs"] = docs

    pp = {}
    for fn in PINNED_PARITY_FILES:
        ap = os.path.join(ROOT, PINNED_PARITY_DIR, fn)
        if os.path.exists(ap):
            pp[fn] = {"sha256": sha(ap), "bytes": os.path.getsize(ap)}
    m["pinned_parity_artifacts"] = {
        "note": ("Reproducible intermediates of test_pinned_env_parity.py "
                 "(three-leg commands in PINNED_ENV_PARITY_REPORT.md section 3); "
                 "archived as release asset pinned_env_parity_artifacts.zip on "
                 "v0.9-audit-evidence. Source of truth is the script + commands."),
        "files": pp,
    }

    rr = {}
    for d in REFERENCE_RUN_DIRS:
        ad = os.path.join(ROOT, d)
        if not os.path.isdir(ad):
            print("MISSING reference-run dir:", d)
            return 2
        for fn in sorted(os.listdir(ad)):
            ap = os.path.join(ad, fn)
            if os.path.isfile(ap):  # skip tb/ event dirs
                rel = f"{d}/{fn}"
                rr[rel] = {"sha256": sha(ap), "bytes": os.path.getsize(ap)}
    for rel in REFERENCE_RUN_LOGS:
        ap = os.path.join(ROOT, rel)
        if os.path.exists(ap):
            rr[rel] = {"sha256": sha(ap), "bytes": os.path.getsize(ap)}
    m["reference_runs"] = {
        "note": ("Git-tracked source artifacts of the local reference-implementation "
                 "runs (THEIRS_ON_OURS_REPORT.md): metrics.jsonl / run_meta.json / gin "
                 "copy / intended-TB-path / trainer log per run. Consumed by the "
                 "theirs_on_ours family of _bestrec_run/hstu_results_manifest.json."),
        "files": rr,
    }
    m["generated_artifacts_note"] = (
        "_bestrec_run/hstu_results_manifest.json and _bestrec_run/hstu_tables.json are "
        "git-tracked GENERATED artifacts: build_hstu_tables.py regenerates them "
        "deterministically from the source files hashed in this manifest, and the "
        "fail-closed --submission gate is itself their integrity check. They are "
        "intentionally outside this manifest's hash scope: the strict wrapper rewrites "
        "hstu_tables.json during the same run that verifies these hashes, so including "
        "them would make verification circular. Provenance layer: git tracking + the "
        "gate, per round-4 audit (PAPER_REVIEW_AUDIT.md) confirmed-problem 2. "
        "LaTeX source boundary (round-8 audit): the paper_tex/ SOURCE tree is governed "
        "by git at the recorded git_commit -- this manifest hashes only the rendered "
        "paper_tex/PAPER_TORS.pdf artifact; deposit bundles that require source ship "
        "the git archive of that commit.")

    m["git_commit"] = head_commit()
    m["date"] = "2026-07-12"
    m["manifest_scope"] = (
        "Hashes describe the repository files as of git_commit. Kept in sync "
        "MECHANICALLY: rebuild_hstu_submission.py --strict runs "
        "update_release_manifest.py --verify, which fails the submission gate "
        "on any hash mismatch, so a manifested file cannot change without a "
        "--regen + commit. Data sections (splits, text_caches, result_families) "
        "are the unchanged v0.9-audit-evidence release assets, byte-verified at "
        "every --regen. The manifest cannot hash itself; its own commit is the "
        "immediate child of the state it describes.")
    m.setdefault("supersedes_git_commit", None)

    io.open(MPATH, "w", encoding="utf-8").write(json.dumps(m, indent=2) + "\n")
    print(f"regenerated at {m['git_commit']}")
    print(f"protocol_code updated: {changed or 'none'}")
    print(f"submission_docs: {len(docs)} files; pinned_parity_artifacts: {len(pp)} files")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--verify", action="store_true")
    g.add_argument("--regen", action="store_true")
    args = ap.parse_args()
    m = json.load(open(MPATH, encoding="utf-8"))
    return verify(m) if args.verify else regen(m)


if __name__ == "__main__":
    sys.exit(main())
