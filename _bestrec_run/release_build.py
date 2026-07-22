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

STAGES = []

def run(label, cmd, cwd=ROOT, sentinel=None):
    """Run a stage; on failure name the exact stage. If `sentinel` is given the
    captured output MUST contain it (a nonzero exit alone is never proof of a
    specific gate -- audit 2026-07-22 13:50 problem 1)."""
    env = dict(os.environ)
    env.pop("DRAFT_WAIVER", None)
    print(f"== {label} ==")
    r = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True,
                       errors="replace")
    sys.stdout.write(r.stdout[-4000:])
    if r.stderr:
        sys.stdout.write(r.stderr[-1500:])
    STAGES.append({"stage": label, "cmd": [str(c) for c in cmd],
                   "exit": r.returncode})
    if r.returncode != 0:
        print(f"RELEASE BUILD: FAIL at step {label!r} (exit {r.returncode})")
        sys.exit(r.returncode or 2)
    if sentinel and sentinel not in (r.stdout + r.stderr):
        print(f"RELEASE BUILD: FAIL at step {label!r} -- expected sentinel "
              f"{sentinel!r} not found in output")
        sys.exit(3)

def venue_build_cmd():
    """Platform-native venue build (audit 13:50: never hand a Windows path to
    a POSIX shell)."""
    ps1 = os.path.join(ROOT, "paper_tex", "build.ps1")
    sh = os.path.join(ROOT, "paper_tex", "build.sh")
    if os.name == "nt":
        return ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                "-File", ps1]
    return ["bash", sh]

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()

def self_test():
    """Expected-failure test: the placeholder gate must fire with its exact
    sentinel when no waiver is set (proof by sentinel, not exit code)."""
    env = dict(os.environ)
    env.pop("DRAFT_WAIVER", None)
    r = subprocess.run([PY, os.path.join(ROOT, "paper_tex", "check_tex_health.py")],
                       cwd=os.path.join(ROOT, "paper_tex"), env=env,
                       capture_output=True, text=True, errors="replace")
    sent = "'[Maintainer:' placeholder present"
    ok = (r.returncode != 0) and (sent in (r.stdout + r.stderr))
    print(f"self-test placeholder gate: exit={r.returncode}; sentinel "
          f"{'FOUND' if sent in (r.stdout + r.stderr) else 'MISSING'}")
    if not ok:
        print("SELF-TEST FAIL: gate did not fire with its sentinel")
        sys.exit(4)
    print("SELF-TEST PASS: strict default fails AT THE PLACEHOLDER GATE")

def main():
    if "--self-test" in sys.argv:
        self_test()
        return
    run("empirical strict chain",
        [PY, os.path.join(ROOT, "_bestrec_run", "rebuild_hstu_submission.py"), "--strict"])
    run("venue builds (STRICT; no waiver)", venue_build_cmd(),
        sentinel="BUILD OK")
    run("manifest worktree verify",
        [PY, os.path.join(ROOT, "_bestrec_run", "update_release_manifest.py"), "--verify"])
    run("manifest HEAD-git verify",
        [PY, os.path.join(ROOT, "_bestrec_run", "update_release_manifest.py"),
         "--verify-git", "HEAD"])
    run("deposit consistency (fails on stale declared tag)",
        [PY, os.path.join(ROOT, "_bestrec_run", "build_deposit_bundle.py"), "--check-only"])
    tool_versions = {}
    for name, cmd in (("python", [PY, "--version"]),
                      ("tectonic", [os.path.join(os.environ.get("LOCALAPPDATA", ""),
                                                 "tectonic", "tectonic.exe"),
                                    "--version"])):
        try:
            tool_versions[name] = subprocess.check_output(
                cmd, text=True, errors="replace").strip()
        except Exception as e:
            tool_versions[name] = f"unavailable: {e}"
    att = {
        "attestation": "release_build",
        "stages": STAGES,
        "tool_versions": tool_versions,
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                        text=True).strip(),
        "hashes": {p: sha(os.path.join(ROOT, p)) for p in (
            "PAPER_SUBMISSION.pdf",
            os.path.join("paper_tex", "PAPER_TORS.pdf"),
            os.path.join("paper_tex", "PAPER_TORS_acmsmall.pdf"),
            os.path.join("paper_tex", "main_console.log"),
            os.path.join("figures", "fig_tail_law_mechanism_data.csv"),
            os.path.join("figures", "fig_tail_law_mechanism.pdf"),
            os.path.join("figures", "fig_r1r2_plane.pdf"),
            "RELEASE_MANIFEST.json",
        ) if os.path.exists(os.path.join(ROOT, p))},
    }
    os.makedirs(os.path.join(ROOT, "_release"), exist_ok=True)
    out = os.path.join(ROOT, "_release", "release_attestation.json")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(att, f, indent=2)
    print("RELEASE BUILD: PASS -- attestation written to", out)
    print("(publish the attestation as a release asset; it is deliberately outside the git tree so the verified HEAD is not recursively changed)")

if __name__ == "__main__":
    main()
