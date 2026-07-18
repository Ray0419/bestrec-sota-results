# -*- coding: utf-8 -*-
"""Build the archival deposit bundle (currently v1.1.4) deterministically.

The bundle is the small archival companion to the repository: papers, pre-registrations,
results documentation, protocol code, provenance manifests, audit chain, and the comparator
reference-run artifacts. Large evidence (splits, text caches, result JSONs) is NOT bundled --
it is tracked in the repository and byte-pinned by RELEASE_MANIFEST.json, which IS bundled.

Usage:  python _bestrec_run/build_deposit_bundle.py            # writes _release/bestrec_deposit_<VERSION>.zip
"""
import hashlib
import io
import os
import zipfile

VERSION = "v1.1.4"
DATE = "2026-07-18"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "_release", f"bestrec_deposit_{VERSION}.zip")
PREFIX = f"bestrec_deposit_{VERSION}/"

# v1.0 inventory (46 repo files), carried forward unchanged in role
V10_FILES = [
    ".zenodo.json",
    "CANONICAL_SUBMISSION.md",
    "CITATION.cff",
    "HSTU_PARITY_REPORT.md",
    "LICENSE",
    "PAPER_ACCEPTANCE_REPAIR_PLAN_2026-07-11.md",
    "PAPER_DRAFT.md",
    "PAPER_SUBMISSION.md",
    "PAPER_SUBMISSION.pdf",
    "RELEASE_MANIFEST.json",
    "RESPONSE_TO_CODEX_AUDIT.md",
    "RESPONSE_TO_FULL_METHOD_AUDIT.md",
    "RESPONSE_TO_NOVELTY_AUDIT.md",
    "RESPONSE_TO_RESUBMISSION_AUDIT_2026-07-11.md",
    "SOTA_CONFIRM_OFFICE_RESULTS.md",
    "SOTA_CONFIRM_PREREG_OFFICE.md",
    "SOTA_CONFIRM_PREREG_V2.md",
    "SOTA_CONFIRM_PREREG_V2_ERRATA.md",
    "SOTA_CONFIRM_V2_RESULTS.md",
    "STRICT_RESUBMISSION_AUDIT_2026-07-11.md",
    "THEIRS_ON_OURS_REPORT.md",
    "_bestrec_run/build_hstu_tables.py",
    "_bestrec_run/fbgemm_shims.py",
    "_bestrec_run/hstu_results_manifest.json",
    "_bestrec_run/hstu_tables.json",
    "_bestrec_run/office_prereg_tools.py",
    "_bestrec_run/preprocess_5core_standard.py",
    "_bestrec_run/rebuild_hstu_submission.py",
    "_bestrec_run/run_fir_ablations.sh",
    "_bestrec_run/run_office_program.sh",
    "_bestrec_run/run_sasrec_sbert.py",
    "_bestrec_run/run_sota_confirm_v2.sh",
    "_bestrec_run/summarize_sota_confirm_v2.py",
    "_bestrec_run/test_hstu_parity.py",
    "_bestrec_run/theirs_preprocess.py",
    "_bestrec_run/theirs_run_music_hstu_blair.sh",
    "_bestrec_run/theirs_run_office_hstu_blair.sh",
    "_bestrec_run/theirs_run_office_sasrec.sh",
    "_bestrec_run/theirs_runs/music_hstu_blair/metrics.jsonl",
    "_bestrec_run/theirs_runs/music_hstu_blair/run_meta.json",
    "_bestrec_run/theirs_runs/office_sasrec_final/metrics.jsonl",
    "_bestrec_run/theirs_runs/office_sasrec_final/run_meta.json",
    "_bestrec_run/theirs_runs/preprocess_provenance_amzn23_music.json",
    "_bestrec_run/theirs_runs/preprocess_provenance_amzn23_office.json",
    "_bestrec_run/theirs_summarize.py",
    "_bestrec_run/theirs_train.py",
]

# Added in v1.1: Office V3 + FIR-breadth prereg/results docs and adjudicators, the pinned-env
# parity chain, the venue/DOI decision docs, the TORS PDF, and the completed Office HSTU-BLaIR
# reference-run artifacts.
V11_ADDITIONS = [
    "README.md",
    "PREREG_OFFICE_V3.md",
    "OFFICE_V3_RESULTS.md",
    "PREREG_FIR_BREADTH.md",
    "FIR_BREADTH_RESULTS.md",
    "PINNED_ENV_PARITY_REPORT.md",
    "DOI_DEPOSIT_INSTRUCTIONS.md",
    "VENUE_PLAN.md",
    "paper_tex/PAPER_TORS.pdf",
    "_bestrec_run/adjudicate_office_v3.py",
    "_bestrec_run/adjudicate_fir_breadth.py",
    "_bestrec_run/update_release_manifest.py",
    "_bestrec_run/emit_latex_tables.py",
    "_bestrec_run/test_pinned_env_parity.py",
    "_bestrec_run/run_impact_program.sh",
    "_bestrec_run/theirs_runs/office_hstu_blair/metrics.jsonl",
    "_bestrec_run/theirs_runs/office_hstu_blair/run_meta.json",
    "_bestrec_run/theirs_runs/office_hstu_blair/hstu-sampled-softmax-n512-blair.gin",
]

FILES = V10_FILES + V11_ADDITIONS

README = f"""BEST-Rec / HSTU-style causal-FIR study -- DOI deposit bundle {VERSION} ({DATE})
================================================================================

This bundle is the archival companion to the manuscript
`PAPER_SUBMISSION.md` / `PAPER_SUBMISSION.pdf` (reader edition) and
`paper_tex/PAPER_TORS.pdf` (ACM TORS manuscript format). It contains the code,
pre-registrations, results documentation, provenance manifests, audit chain,
and small evaluation artifacts needed to verify every number printed in the
paper. Large evidence (data splits, text-encoder caches, per-run result JSONs)
is tracked in the repository and byte-pinned by `RELEASE_MANIFEST.json`
(included here), so nothing printed depends on any file outside the pinned set.

Canonical verification command (from a checkout of the full repository):

    python _bestrec_run/rebuild_hstu_submission.py --strict

which runs: the bitwise HSTU core-block parity test -> the fail-closed
artifact-graph build (every printed numeral recomputed from source artifacts;
exits nonzero on any mismatch/untraceable cell/missing claim family) ->
release-manifest verification -> the pre-registered Musical_Instruments
dual-kernel gate adjudicator -> the Office_Products V1 adjudicator (VOID under
its own prereg; descriptive only).

New in v1.1/v1.1.1 (vs v1.0, 2026-07-11; v1.1.1 supersedes the v1.1 tag, whose uploaded assets had gone stale against later same-day commits):
  * Office_Products V3 redesigned pre-registration and its PASS record
    (`PREREG_OFFICE_V3.md`, `OFFICE_V3_RESULTS.md`, `_bestrec_run/adjudicate_office_v3.py`).
  * FIR-breadth pre-registered campaign on two further categories, both CONFIRMED
    (`PREREG_FIR_BREADTH.md`, `FIR_BREADTH_RESULTS.md`, `_bestrec_run/adjudicate_fir_breadth.py`).
  * The pinned-environment parity chain (`PINNED_ENV_PARITY_REPORT.md`,
    `_bestrec_run/test_pinned_env_parity.py`).
  * The completed Office HSTU-BLaIR reference-run artifacts
    (`_bestrec_run/theirs_runs/office_hstu_blair/`).
  * The ACM TORS manuscript PDF (`paper_tex/PAPER_TORS.pdf`), the venue/DOI
    decision records (`VENUE_PLAN.md`, `DOI_DEPOSIT_INSTRUCTIONS.md`), and the
    self-policing manifest tool (`_bestrec_run/update_release_manifest.py`).
  * `RELEASE_MANIFEST.json` now also pins the 20 Office V3 result/tree-state
    files and the 20 FIR-breadth result JSONs (result_families
    `OFFICEV3_gate`, `FIR_breadth`).

Claim boundary (unchanged; `CANONICAL_SUBMISSION.md` governs): two counted
pre-registered per-category point-estimate comparisons (Musical_Instruments;
Office_Products V3 under its frozen wording); Office V1 remains VOID and is
never counted; the causal FIR filter is confirmed on four categories as an
internal paired contrast; no SOTA claim of any kind; no paired or
distributional superiority over any comparator.

This bundle was generated by `_bestrec_run/build_deposit_bundle.py` (included
in the repository); `SHA256SUMS.txt` inside the bundle covers every bundled
file.
"""


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def consistency_gate():
    """Fail-closed: refuse to build a bundle whose surrounding metadata disagrees with VERSION.

    Prevents the staleness class caught by the 2026-07-18 12:16/13:16 audits (bundled
    CITATION/zenodo/manifest naming an older deposit version than the tag being cut).
    Also enforces the release-topology rule: build AFTER the manifest regen and BEFORE the
    single commit that gets tagged, so tag tree == bundle == uploaded assets.
    """
    import json as _json
    import subprocess as _sp
    plain = VERSION.lstrip("v")
    fails = []

    def read(rel):
        with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
            return f.read()

    if 'version: "%s"' % plain not in read("CITATION.cff"):
        fails.append("CITATION.cff version != %s" % plain)
    if _json.loads(read(".zenodo.json")).get("version") != plain:
        fails.append(".zenodo.json version != %s" % plain)
    if "bestrec_deposit_%s.zip" % VERSION not in read("DOI_DEPOSIT_INSTRUCTIONS.md"):
        fails.append("DOI_DEPOSIT_INSTRUCTIONS.md does not name bestrec_deposit_%s.zip" % VERSION)
    if "%s-deposit" % VERSION not in read("README.md"):
        fails.append("README.md does not name %s-deposit" % VERSION)
    if "%s-deposit" % VERSION not in read("CANONICAL_SUBMISSION.md"):
        fails.append("CANONICAL_SUBMISSION.md does not name %s-deposit" % VERSION)
    head = _sp.run(["git", "-C", ROOT, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    mc = _json.loads(read("RELEASE_MANIFEST.json")).get("git_commit")
    if mc != head:
        fails.append("RELEASE_MANIFEST git_commit (%s) != HEAD (%s) -- run --regen immediately "
                     "before building, then make ONE commit and tag it" % (str(mc)[:8], head[:8]))
    if fails:
        print("CONSISTENCY GATE FAILED -- bundle NOT built:")
        for f in fails:
            print("  -", f)
        raise SystemExit(2)
    print("consistency gate OK (metadata versions + manifest boundary agree with %s)" % VERSION)


def main():
    consistency_gate()
    missing = [f for f in FILES if not os.path.exists(os.path.join(ROOT, f))]
    if missing:
        for f in missing:
            print("MISSING:", f)
        raise SystemExit(2)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    sums = []
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(PREFIX + "README_DEPOSIT.txt", README)
        sums.append((hashlib.sha256(README.encode("utf-8")).hexdigest(), "README_DEPOSIT.txt"))
        for rel in sorted(FILES):
            ap = os.path.join(ROOT, rel)
            z.write(ap, PREFIX + rel)
            sums.append((sha256(ap), rel))
        body = "\n".join(f"{d}  {n}" for d, n in sums) + "\n"
        z.writestr(PREFIX + "SHA256SUMS.txt", body)
    digest = sha256(OUT)
    with io.open(OUT + ".sha256", "w", encoding="utf-8") as f:
        f.write(f"{digest}  {os.path.basename(OUT)}\n")
    n_entries = len(FILES) + 2  # + README + SHA256SUMS
    print(f"wrote {OUT}")
    print(f"entries: {n_entries} | bytes: {os.path.getsize(OUT)} | sha256: {digest}")


if __name__ == "__main__":
    main()
