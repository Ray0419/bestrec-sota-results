# -*- coding: utf-8 -*-
"""ONE authoritative release command (audit 2026-07-22 12:49 C1, first cut).

Runs, in order, with NO waiver accepted:
  1. the empirical strict chain (parity, 175 cells, manifests, adjudicators)
  2. both venue PDF builds in STRICT mode (placeholder = failure)
  3. release-manifest worktree + HEAD-git verification
  4. deposit-tag consistency check (must fail if the declared tag is stale)
  5. an attestation JSON binding the PDF/log/manifest hashes

Draft builds are NOT available here; use paper_tex/build.sh --draft "reason".
Exit 0 only when every step passes.
"""
import hashlib
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable

def run(label, cmd, cwd=ROOT, env_extra=None):
    env = dict(os.environ)
    env.pop("DRAFT_WAIVER", None)
    if env_extra:
        env.update(env_extra)
    print(f"== {label} ==")
    r = subprocess.run(cmd, cwd=cwd, env=env)
    if r.returncode != 0:
        print(f"RELEASE BUILD: FAIL at step {label!r} (exit {r.returncode})")
        sys.exit(r.returncode or 2)

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()

def main():
    run("empirical strict chain",
        [PY, os.path.join(ROOT, "_bestrec_run", "rebuild_hstu_submission.py"), "--strict"])
    run("venue builds (STRICT; no waiver)",
        ["bash", os.path.join(ROOT, "paper_tex", "build.sh")])
    run("manifest worktree verify",
        [PY, os.path.join(ROOT, "_bestrec_run", "update_release_manifest.py"), "--verify"])
    run("manifest HEAD-git verify",
        [PY, os.path.join(ROOT, "_bestrec_run", "update_release_manifest.py"),
         "--verify-git", "HEAD"])
    run("deposit consistency (fails on stale declared tag)",
        [PY, os.path.join(ROOT, "_bestrec_run", "build_deposit_bundle.py"), "--check-only"])
    att = {
        "attestation": "release_build",
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                        text=True).strip(),
        "hashes": {p: sha(os.path.join(ROOT, p)) for p in (
            "PAPER_SUBMISSION.pdf",
            os.path.join("paper_tex", "PAPER_TORS.pdf"),
            os.path.join("paper_tex", "main_console.log"),
            "RELEASE_MANIFEST.json",
        ) if os.path.exists(os.path.join(ROOT, p))},
    }
    out = os.path.join(ROOT, "_bestrec_run", "release_attestation.json")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(att, f, indent=2)
    print("RELEASE BUILD: PASS -- attestation written to", out)

if __name__ == "__main__":
    main()
