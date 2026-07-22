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
import datetime as _dt
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
ARGS = None
RELEASE_ASSET_SECTIONS = {"splits", "text_caches", "pinned_parity_artifacts", "tfv2_sidecars"}
RELEASE_URL = ("https://github.com/Ray0419/bestrec-sota-results/releases/download/"
               "v0.9-audit-evidence/")
FIGURE_ASSETS = [
    "figures/fig_tail_law_mechanism_data.csv",
    "figures/fig_tail_law_mechanism.png",
    "figures/fig_tail_law_mechanism.pdf",
    "figures/fig_r1r2_plane.png",
    "figures/fig_r1r2_plane.pdf",
    "_bestrec_run/make_fig_tail_law_mechanism.py",
    "_bestrec_run/make_fig_r1r2_plane.py",
]
AUX_GRAPH_SOURCES = [
    "_bestrec_sota_lab/runs/hstu_blair_eval_export_full_20260609_fg/hstu_blair_eval_export_summary.json",
    "_bestrec_run/run_CONNGATE_MI_k8_seed20260608.log",
    "_bestrec_run/run_CONNGATE_5seed_driver.log",
]


def sha(p, _bufsz=1 << 20):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while True:
            b = f.read(_bufsz)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


BINARY_EXT = (".pdf", ".zip", ".gz", ".png", ".pt", ".npz")


def sha_norm(p, _bufsz=1 << 20):
    """SHA256 of LF-normalized bytes for text files; raw for binary types.

    Used for GIT-BACKED sections so digests are platform-independent: they equal the
    git blob hash content-wise (the index stores LF via .gitattributes) and the
    LF-normalized deposit-bundle payload hashes. Release-asset sections keep raw sha()
    because their uploaded asset bytes are immutable as-is. (Audit 2026-07-18 20:24.)
    """
    if p.lower().endswith(BINARY_EXT):
        return sha(p)
    with open(p, "rb") as f:
        data = f.read()
    h = hashlib.sha256()
    h.update(data.replace(b"\r\n", b"\n"))
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

    def check_named(section, key, digest, hasher=sha):
        nonlocal checked
        if "/" in key:  # path-qualified (CP-2, audit 2026-07-19 12:57): exact path only
            ap = os.path.join(ROOT, key.replace("/", os.sep))
            if not os.path.exists(ap):
                (missing_asset if section in RELEASE_ASSET_SECTIONS else bad).append(
                    f"{section}/{key}: MISSING (exact path)")
                return
            if hasher(ap) == digest:
                checked += 1
            else:
                bad.append(f"{section}/{key}: hash mismatch vs manifest (exact path)")
            return
        cands = locate(idx, key)
        if not cands:
            (missing_asset if section in RELEASE_ASSET_SECTIONS else bad).append(
                f"{section}/{key}: MISSING" +
                ("" if section in RELEASE_ASSET_SECTIONS else " (git-tracked file)"))
            return
        if any(hasher(c) == digest for c in cands):
            checked += 1
        else:
            bad.append(f"{section}/{key}: hash mismatch vs manifest")

    for sec in ("splits", "text_caches", "tfv2_sidecars"):
        for key, ent in m.get(sec, {}).items():
            check_named(sec, key, ent["sha256"])
    for rel, ent in m.get("protocol_code", {}).items():
        ap = os.path.join(ROOT, rel)
        if not os.path.exists(ap):
            bad.append(f"protocol_code/{rel}: MISSING")
        elif sha_norm(ap) != ent["sha256"]:
            bad.append(f"protocol_code/{rel}: hash mismatch vs manifest")
        else:
            checked += 1
    for rel, ent in m.get("submission_docs", {}).items():
        ap = os.path.join(ROOT, rel)
        if not os.path.exists(ap):
            bad.append(f"submission_docs/{rel}: MISSING")
        elif sha_norm(ap) != ent["sha256"]:
            bad.append(f"submission_docs/{rel}: hash mismatch vs manifest "
                       "(edit without --regen?)")
        else:
            checked += 1
    for rel, ent in m.get("figure_assets", {}).items():
        ap2 = os.path.join(ROOT, rel)
        h = sha_norm(ap2) if rel.endswith((".py", ".csv")) else sha(ap2)
        if not os.path.exists(ap2):
            bad.append(f"figure_assets/{rel}: MISSING (git-tracked file)")
        elif h != ent["sha256"]:
            bad.append(f"figure_assets/{rel}: hash mismatch vs manifest")
        else:
            checked += 1
    for rel, ent in m.get("aux_graph_sources", {}).items():
        ap2 = os.path.join(ROOT, rel)
        if not os.path.exists(ap2):
            bad.append(f"aux_graph_sources/{rel}: MISSING (git-tracked file)")
        elif sha_norm(ap2) != ent["sha256"]:
            bad.append(f"aux_graph_sources/{rel}: hash mismatch vs manifest")
        else:
            checked += 1
    for fam, files in m.get("result_families", {}).items():
        for fn, digest in files.items():
            check_named(f"result_families/{fam}", fn, digest, hasher=sha_norm)
    for rel, ent in m.get("reference_runs", {}).get("files", {}).items():
        ap = os.path.join(ROOT, rel)
        if not os.path.exists(ap):
            bad.append(f"reference_runs/{rel}: MISSING (git-tracked file)")
        elif sha_norm(ap) != ent["sha256"]:
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

    # round-9 audit structural fix: a manifested file that is git-dirty means the
    # manifest describes uncommitted content -- a clean clone would not verify.
    try:
        dirty = subprocess.check_output(["git", "status", "--porcelain", "-uno"],
                                        cwd=ROOT, text=True).splitlines()
        manifested = set()
        for sec in ("protocol_code", "submission_docs", "aux_graph_sources"):
            manifested.update(m.get(sec, {}).keys())
        for ln in dirty:
            rel = ln[3:].strip().replace("\\", "/")
            if rel in manifested:
                bad.append(f"{rel}: git-DIRTY manifested file -- commit it together "
                           "with a regenerated manifest (clean clones would fail)")
    except Exception as e:
        print("  (git dirty-check skipped:", e, ")")

    if missing_asset and getattr(ARGS, "fetch_missing", False):
        import urllib.request
        still = []
        for w in missing_asset:
            sec_key = w.split(":")[0]
            key = sec_key.split("/", 1)[1] if "/" in sec_key else sec_key
            sec = sec_key.split("/", 1)[0]
            if sec == "pinned_parity_artifacts":
                ent = m.get(sec, {}).get("files", {}).get(key)
            else:
                ent = m.get(sec, {}).get(key)
            if not isinstance(ent, dict) or "sha256" not in ent:
                still.append(w + " [no manifest entry to fetch against]")
                continue
            name = key + ".csv" if (sec == "splits" and not key.endswith(".csv")) else key
            url = RELEASE_URL + os.path.basename(name)
            try:
                h = hashlib.sha256()
                with urllib.request.urlopen(url, timeout=120) as r:
                    for chunk in iter(lambda: r.read(1 << 20), b""):
                        h.update(chunk)
                if h.hexdigest() == ent["sha256"]:
                    checked += 1
                    print(f"FETCH-VERIFIED release asset: {key}")
                else:
                    still.append(w + " [remote hash mismatch]")
            except Exception as e:
                still.append(w + f" [fetch failed: {e}]")
        missing_asset = still
    for w in missing_asset:
        print("  SKIPPED-missing (release asset):", w)
    if missing_asset and not getattr(ARGS, "allow_missing_assets", False):
        bad.append(f"{len(missing_asset)} release-class asset(s) missing locally and not "
                   "fetch-verified (fail-closed 2026-07-20, audit 16:53; use "
                   "--fetch-missing to stream-verify from the release, or "
                   "--allow-missing-assets to explicitly waive)")
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
            if "/" in fn:  # path-qualified: exact file must match
                ap = os.path.join(ROOT, fn.replace("/", os.sep))
                if not (os.path.exists(ap) and sha_norm(ap) == digest):
                    drift.append(f"result_families/{fam}/{fn}")
                continue
            cands = idx.get(fn, [])
            hashes = {sha_norm(c) for c in cands}
            if len(hashes) > 1:
                drift.append(f"result_families/{fam}/{fn}: AMBIGUOUS basename "
                             "(multiple distinct-hash files) -- path-qualify this entry")
                continue
            if not any(sha(c) == digest or sha_norm(c) == digest for c in cands):
                drift.append(f"result_families/{fam}/{fn}")
    if drift:
        print("DATA DRIFT -- ABORTING (released evidence must not change):")
        for d in drift:
            print("  -", d)
        return 2

    # migrate/refresh result_families digests to normalized hashing (content identity is
    # proven by the drift guard above, which accepts the legacy raw digest)
    for fam, files in m["result_families"].items():
        for fn in list(files.keys()):
            if "/" in fn:
                ap = os.path.join(ROOT, fn.replace("/", os.sep))
                if os.path.exists(ap):
                    files[fn] = sha_norm(ap)
                continue
            cands = idx.get(fn, [])
            if cands:
                files[fn] = sha_norm(cands[0])

    changed = []
    for rel, ent in m["protocol_code"].items():
        new = sha_norm(os.path.join(ROOT, rel))
        if new != ent.get("sha256"):
            ent["sha256"] = new
            changed.append(rel)
    docs = {}
    for rel in SUBMISSION_DOCS:
        ap = os.path.join(ROOT, rel)
        if not os.path.exists(ap):
            print("MISSING submission doc:", rel)
            return 2
        docs[rel] = {"sha256": sha_norm(ap), "bytes": os.path.getsize(ap)}
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

    # tfv2_sidecars (release-asset class; immutable once written -- drift aborts)
    import glob as _g
    tv = m.get("tfv2_sidecars", {})
    for ap in sorted(_g.glob(os.path.join(ROOT, "_bestrec_run", "results_TFV2_*.users.jsonl.gz"))):
        key = os.path.basename(ap)
        dig = sha(ap)
        if key in tv and tv[key]["sha256"] != dig:
            print("DATA DRIFT -- ABORTING: tfv2_sidecars/" + key)
            return 2
        tv[key] = {"sha256": dig, "bytes": os.path.getsize(ap)}
    m["tfv2_sidecars"] = tv
    # IS/CDs splits join the immutable splits inventory (added 2026-07-20; audit 16:53)
    for cat in ("Industrial_and_Scientific", "CDs_and_Vinyl"):
        for part in ("train", "valid", "test"):
            key = f"{cat}.{part}"
            if key not in m["splits"]:
                ap = os.path.join(ROOT, "data_5core", "5core", "last_out", f"{cat}.{part}.csv")
                m["splits"][key] = {"sha256": sha(ap), "bytes": os.path.getsize(ap)}
    # aux graph sources (git-backed; formerly ignored local-only cell inputs)
    ax = {}
    for rel in AUX_GRAPH_SOURCES:
        ap = os.path.join(ROOT, rel.replace("/", os.sep))
        if not os.path.exists(ap):
            print("MISSING aux graph source:", rel)
            return 2
        ax[rel] = {"sha256": sha_norm(ap), "bytes": os.path.getsize(ap)}
    m["aux_graph_sources"] = ax
    fa = {}
    for rel in FIGURE_ASSETS:
        ap = os.path.join(ROOT, rel.replace("/", os.sep))
        if not os.path.exists(ap):
            print("MISSING figure asset:", rel)
            return 2
        fa[rel] = {"sha256": (sha_norm(ap) if rel.endswith((".py", ".csv")) else sha(ap)),
                   "bytes": os.path.getsize(ap)}
    m["figure_assets"] = fa

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
                rr[rel] = {"sha256": sha_norm(ap), "bytes": os.path.getsize(ap)}
    for rel in REFERENCE_RUN_LOGS:
        ap = os.path.join(ROOT, rel)
        if os.path.exists(ap):
            rr[rel] = {"sha256": sha_norm(ap), "bytes": os.path.getsize(ap)}
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
    m["date"] = _dt.date.today().isoformat()
    m["manifest_scope"] = (
        "Hashes describe the repository files as of git_commit — the parent "
        "commit whose tree was hashed at the most recent --regen (the manifest "
        "cannot hash itself, so its own commit is the immediate child of that "
        "state); commits that touch no manifested file leave the hashes valid "
        "without a regen, and every strict build re-verifies all hashes "
        "against the live tree. Kept in sync "
        "MECHANICALLY: rebuild_hstu_submission.py --strict runs "
        "update_release_manifest.py --verify, which fails the submission gate "
        "on any hash mismatch, so a manifested file cannot change without a "
        "--regen + commit. Hashing rule (2026-07-18 migration, content identity "
        "proven under the legacy raw rule at migration time): git-backed sections "
        "(protocol_code, submission_docs, result_families, reference_runs) digest "
        "LF-normalized bytes for text files -- platform-independent and equal to "
        "the git-blob and deposit-payload hashes; release-asset sections (splits, "
        "text_caches, pinned_parity_artifacts) digest raw bytes because their "
        "uploaded assets are immutable as-is. Data sections (splits, text_caches, result_families) "
        "are the unchanged v0.9-audit-evidence release assets, byte-verified at "
        "every --regen. The manifest cannot hash itself; its own commit is the "
        "immediate child of the state it describes.")
    m["hash_parent_commit"] = m.get("git_commit")
    m["git_commit_semantics"] = (
        "git_commit (alias hash_parent_commit) is the PARENT commit recorded at "
        "--regen; the digests describe the worktree that becomes the tree of the "
        "manifest's own introducing commit (the immediate child). The LITERAL "
        "reviewer-facing verification target is intended_deposit_tag when present: "
        "run  update_release_manifest.py --verify-git <intended_deposit_tag>  (or "
        "HEAD, or any descendant where manifested files are unchanged). Do NOT "
        "verify at git_commit itself when manifested files changed in the "
        "introducing commit. (Audits 2026-07-18 21:30 and 23:28.)")
    m.setdefault("supersedes_git_commit", None)

    io.open(MPATH, "w", encoding="utf-8").write(json.dumps(m, indent=2) + "\n")
    print(f"regenerated at {m['git_commit']}")
    print(f"protocol_code updated: {changed or 'none'}")
    print(f"submission_docs: {len(docs)} files; pinned_parity_artifacts: {len(pp)} files")
    try:
        dirty = subprocess.check_output(["git", "status", "--porcelain", "-uno"],
                                        cwd=ROOT, text=True).splitlines()
        hashed = set(m["protocol_code"]) | set(m["submission_docs"])
        need = [ln[3:].strip() for ln in dirty
                if ln[3:].strip().replace("\\", "/") in hashed]
        if need:
            print("COMMIT TOGETHER WITH RELEASE_MANIFEST.json (dirty manifested files):")
            for r in need:
                print("   +", r)
    except Exception:
        pass
    return 0


def verify_git(m, commit):
    """Compare git-backed manifest sections against the git blobs at `commit`.

    This is the external auditor's check (2026-07-18 20:24) made runnable in-repo:
    every git-backed digest must equal the SHA256 of the LF-normalized blob bytes.
    """
    def blob_norm(path):
        try:
            raw = subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)
        except subprocess.CalledProcessError:
            return None
        if path.lower().endswith(BINARY_EXT):
            data = raw
        else:
            data = raw.replace(b"\r\n", b"\n")
        return hashlib.sha256(data).hexdigest()

    bad = []
    checked = 0
    for sec in ("protocol_code", "submission_docs", "aux_graph_sources",
                "figure_assets"):
        for rel, ent in m.get(sec, {}).items():
            d = blob_norm(rel)
            if d is None:
                bad.append(f"{sec}/{rel}: not in git tree {commit[:8]}")
            elif d != ent["sha256"]:
                bad.append(f"{sec}/{rel}: manifest != git blob")
            else:
                checked += 1
    for rel, ent in m.get("reference_runs", {}).get("files", {}).items():
        d = blob_norm(rel)
        if d is None:
            bad.append(f"reference_runs/{rel}: not in git tree {commit[:8]}")
        elif d != ent["sha256"]:
            bad.append(f"reference_runs/{rel}: manifest != git blob")
        else:
            checked += 1
    ls = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", commit],
                                 cwd=ROOT, text=True).splitlines()
    by_name = {}
    for pth in ls:
        by_name.setdefault(pth.rsplit("/", 1)[-1], []).append(pth)
    for fam, files in m.get("result_families", {}).items():
        for fn, digest in files.items():
            if "/" in fn:  # exact tree path (CP-2)
                d = blob_norm(fn)
                if d is None:
                    bad.append(f"result_families/{fam}/{fn}: not in git tree {commit[:8]}")
                elif d != digest:
                    bad.append(f"result_families/{fam}/{fn}: manifest != git blob (exact path)")
                else:
                    checked += 1
                continue
            paths = by_name.get(fn, [])
            if not paths:
                bad.append(f"result_families/{fam}/{fn}: not in git tree {commit[:8]}")
            elif not any(blob_norm(pth) == digest for pth in paths):
                bad.append(f"result_families/{fam}/{fn}: manifest != git blob")
            else:
                checked += 1
    if bad:
        print(f"VERIFY-GIT vs {commit[:12]}: {len(bad)} mismatches "
              f"({checked} OK):")
        for b in bad:
            print("  -", b)
        stored = m.get("git_commit", "")
        if commit.startswith(stored[:12]) or stored.startswith(commit[:12]):
            tag = m.get("intended_deposit_tag")
            print("HINT: this commit is the manifest's recorded PARENT; the digests "
                  "describe its introducing commit's tree. Try --verify-git "
                  + (repr(tag) if tag else "HEAD or the deposit tag")
                  + " (see git_commit_semantics).")
        return 1
    print(f"VERIFY-GIT vs {commit[:12]}: OK ({checked} git-backed entries match "
          "the git blobs exactly)")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--verify", action="store_true")
    g.add_argument("--regen", action="store_true")
    g.add_argument("--verify-git", nargs="?", const="HEAD", default=None,
                   metavar="COMMIT")
    ap.add_argument("--deposit-tag", default=None, metavar="TAG",
                    help="with --regen: stamp intended_deposit_tag (the literal tag "
                         "reviewers pass to --verify-git; audit 2026-07-18 23:28)")
    ap.add_argument("--fetch-missing", action="store_true",
                    help="stream-download + hash-verify missing release-class assets "
                         "from the public release instead of failing")
    ap.add_argument("--allow-missing-assets", action="store_true",
                    help="explicitly waive the fail-closed missing-asset check")
    args = ap.parse_args()
    global ARGS
    ARGS = args
    m = json.load(open(MPATH, encoding="utf-8"))
    if args.verify_git is not None:
        return verify_git(m, args.verify_git)
    if args.regen and args.deposit_tag:
        m["intended_deposit_tag"] = args.deposit_tag
    return verify(m) if args.verify else regen(m)


if __name__ == "__main__":
    sys.exit(main())
