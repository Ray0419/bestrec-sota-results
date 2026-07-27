# -*- coding: utf-8 -*-

"""Build the archival deposit bundle (currently v1.1.9) deterministically.



Text payloads are normalized to LF at bundle time (audit 2026-07-18 15:17), so the bundle

is byte-stable across Windows/Linux checkouts; .gitattributes pins the same policy in Git.



The bundle is the small archival companion to the repository: papers, pre-declarations,

results documentation, protocol code, provenance manifests, core historical audit
documents, and the comparator

reference-run artifacts. Large evidence is NOT bundled -- result JSONs are git-tracked;

splits/text caches are SHA-256-pinned by RELEASE_MANIFEST.json (which IS bundled) but are
not yet public release assets (upload pending).



Usage:  python _bestrec_run/build_deposit_bundle.py            # writes _release/bestrec_deposit_<VERSION>.zip

"""

import hashlib

import io

import os
import sys as _sys

import zipfile



VERSION = "v1.2.0"

def _manifest_date():
    # DOI-facing date basis is explicit and single-sourced (audit 2026-07-19 09:34):
    # the manifest's regen date (stamped local time, Australia/Sydney).
    import json as _j
    with open(os.path.join(ROOT, "RELEASE_MANIFEST.json"), encoding="utf-8") as f:
        return _j.load(f).get("date", "unknown") + " (local, Australia/Sydney)"


DATE = None  # resolved at build time via _manifest_date()

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



V12_ADDITIONS = [
    "AUDIT_RESPONSE_2026-07-27.md",
    "CLAIM_ARTIFACT_MAP.md",
    "COVER_LETTER_TORS.md",
    "MOCK_REVIEW_2026-07-27.md",
    "PHASE_COMPLETION_AUDIT_2026-07-28.md",
    "PREREG_FIR_V3.md",
    "PREREG_FIR_CANONICAL_BREADTH.md",
    "PREREG_FIR_CANONICAL_BREADTH_ERRATA.md",
    "PREREG_FIR_CONTROLS.md",
    "PREREG_FIR_CONTROLS_ERRATA.md",
    "PREREG_TAIL_FIR_V2.md",
    "PREREG_EE_V2.md",
    "bootstrap_public_clone.py",
    "RESPONSE_TO_PAPER_REVIEW_AUDIT.md",
    "EXPERIMENT_PROGRAM.md",
    "figures/fig_fir_response_data.csv",
    "figures/fig_fir_response.pdf",
    "_bestrec_run/build_claim_artifact_map.py",
    "_bestrec_run/build_deposit_bundle.py",
    "_bestrec_run/test_fir_causality.py",
    "_bestrec_run/make_fig_fir_response.py",
    "_bestrec_run/adjudicate_fir_v3.py",
    "_bestrec_run/adjudicate_fir_canonical_breadth.py",
    "_bestrec_run/adjudicate_fir_controls.py",
    "_bestrec_run/adjudicate_tfv2.py",
    "_bestrec_run/adjudicate_ee_v2.py",
]

FILES = sorted(set(V10_FILES + V11_ADDITIONS + V12_ADDITIONS))



README_TMPL = """Artifact-gated causal-FIR study -- deposit bundle {VERSION} ({DATE})
================================================================================

This bundle is the candidate archival companion to `PAPER_SUBMISSION.md` /
`PAPER_SUBMISSION.pdf` (reader edition) and `paper_tex/PAPER_TORS.pdf` (ACM
TORS manuscript format). It contains code, pre-declarations, result records,
provenance manifests, core historical audit documents, and small evaluation
artifacts needed to verify paper-facing numbers.

Large evidence is hash-pinned by `RELEASE_MANIFEST.json`: compact per-run JSONs
are git-tracked, while splits, text caches, and large per-user/checkpoint
payloads are public release assets. `bootstrap_public_clone.py` hydrates and
verifies that public evidence boundary. `SHA256SUMS.txt` pins exactly this zip's
payload bytes; the release manifest pins the larger repository/asset boundary.

Canonical verification command:

    python _bestrec_run/rebuild_hstu_submission.py --strict

It runs fail-closed: bitwise HSTU core-block parity; the strict 192-cell,
18-family artifact graph; release-manifest verification; the governed MI,
TFV2, COUNTED Office_Products V3, FIR-breadth adjudicator, canonical FIR,
active-control, and reproduction checks; the permanent Office V1 VOID; the
16-case FIR causality test; and deterministic claim-to-artifact-map verification.

New in the v1.2.0 candidate: canonical nonsingular FIR and breadth campaigns,
active controls, TFV2 repaired-estimand evidence, learned-tap/frequency-response
diagnostics, the current audit response/mock review/cover letter, a phase ledger,
a deterministic claim-to-artifact map, and two public reconstruction paths.

Claim boundary (`CANONICAL_SUBMISSION.md` governs): two counted pre-declared
per-category point-estimate comparisons; Office V1 remains VOID; canonical FIR
evidence is outcome-known/test-exposed internal evidence; active controls do not
isolate temporal specificity from generic trainable-residual capacity; no SOTA
claim and no paired/distributional superiority over a single-run comparator.

PUBLICATION WARNING: this candidate intentionally contains creator placeholders.
It is not a published release or DOI. Replace and verify author/legal metadata
before tagging, uploading, or minting.

Generated by `_bestrec_run/build_deposit_bundle.py`; the bundle-internal
`SHA256SUMS.txt` covers every bundled payload file.
"""





def sha256(path):

    h = hashlib.sha256()

    with open(path, "rb") as f:

        for chunk in iter(lambda: f.read(1 << 20), b""):

            h.update(chunk)

    return h.hexdigest()





def consistency_gate(candidate=False):

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

    placeholder = "CREATOR METADATA REQUIRED BEFORE PUBLICATION"
    has_placeholder = placeholder in read("CITATION.cff") or placeholder in read(".zenodo.json")
    if has_placeholder and not candidate:
        fails.append("creator metadata placeholder remains (normal/tagged builds require verified creators; use --candidate for an unpublished local bundle)")
    if candidate and not has_placeholder:
        print("candidate warning: creator placeholder has been replaced; verify metadata manually before publication")

    n_entries = len(FILES) + 2
    if "(%d entries" % n_entries not in read("DOI_DEPOSIT_INSTRUCTIONS.md"):
        fails.append("DOI_DEPOSIT_INSTRUCTIONS.md entry count != %d (README+SHA256SUMS+payloads)" % n_entries)
    if "bestrec_deposit_%s.zip" % VERSION not in read("DOI_DEPOSIT_INSTRUCTIONS.md"):

        fails.append("DOI_DEPOSIT_INSTRUCTIONS.md does not name bestrec_deposit_%s.zip" % VERSION)

    if "%s-deposit" % VERSION not in read("README.md"):

        fails.append("README.md does not name %s-deposit" % VERSION)

    if "%s-deposit" % VERSION not in read("CANONICAL_SUBMISSION.md"):

        fails.append("CANONICAL_SUBMISSION.md does not name %s-deposit" % VERSION)

    # Current-only sweep: submission-support docs (bundled or not) may reference NO deposit
    # tag other than the current one -- historical registries (README releases list, CANONICAL
    # supersession chain, DOI prior-tags row) are exempt because they intentionally list priors.
    import re as _re
    for doc in ("VENUE_PLAN.md", "COVER_LETTER_TORS.md"):
        body = read(doc)
        for m in sorted(set(_re.findall(r"v\d+(?:\.\d+)*-deposit", body))):
            if m != "%s-deposit" % VERSION:
                fails.append("%s names stale deposit tag %s (use version-agnostic wording)" % (doc, m))

    # Manifest-vs-bundle cross-check (audit 2026-07-18 20:24): for every file that will be
    # bundled AND appears in a git-backed manifest section, the manifest digest must equal
    # the LF-normalized payload hash the bundle will carry.
    man = _json.loads(read("RELEASE_MANIFEST.json"))
    man_map = {}
    for sec in ("protocol_code", "submission_docs"):
        man_map.update(man.get(sec, {}))
    man_map.update(man.get("reference_runs", {}).get("files", {}))
    fam_by_name = {}
    for fam in man.get("result_families", {}).values():
        fam_by_name.update(fam)
    for rel in FILES:
        ent = man_map.get(rel) or ({"sha256": fam_by_name[rel.rsplit("/", 1)[-1]]}
                                   if rel.rsplit("/", 1)[-1] in fam_by_name else None)
        if ent is None:
            continue
        data = open(os.path.join(ROOT, rel), "rb").read()
        if not rel.lower().endswith((".pdf", ".zip", ".gz", ".png")):
            data = data.replace(b"\r\n", b"\n")
        if hashlib.sha256(data).hexdigest() != ent["sha256"]:
            fails.append("bundle payload %s != RELEASE_MANIFEST digest (regen the manifest "
                         "immediately before building)" % rel)
    if man.get("intended_deposit_tag") != "%s-deposit" % VERSION:
        fails.append("RELEASE_MANIFEST intended_deposit_tag (%r) != %s-deposit -- regen with "
                     "--deposit-tag %s-deposit" % (man.get("intended_deposit_tag"), VERSION, VERSION))
    # Boundary check (audit 2026-07-19 00:35): git_commit is documented as the PARENT
    # recorded at --regen, so requiring git_commit == HEAD false-fails for a reviewer
    # rebuilding at the released tag. The real invariant is "the manifest describes THIS
    # tree", which holds in exactly two ways:
    #   CUT mode      : fresh regen, pre-commit  -> git_commit == HEAD
    #   REBUILD mode  : at the tag / descendant  -> --verify-git HEAD passes
    head = _sp.run(["git", "-C", ROOT, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    mc = _json.loads(read("RELEASE_MANIFEST.json")).get("git_commit")
    if mc != head:
        vg = _sp.run([_sys.executable, os.path.join(ROOT, "_bestrec_run", "update_release_manifest.py"),
                      "--verify-git", "HEAD"], capture_output=True, text=True, cwd=ROOT)
        if vg.returncode != 0:
            fails.append("manifest does not describe this tree: git_commit (%s) != HEAD (%s) AND "
                         "--verify-git HEAD failed -- at cut time run --regen immediately before "
                         "building; at rebuild time check out the deposit tag" % (str(mc)[:8], head[:8]))
        elif candidate:
            print("boundary: CANDIDATE mode (--verify-git HEAD OK; no tag equality claimed)")
        else:
            tag = "%s-deposit" % VERSION
            tc = _sp.run(["git", "-C", ROOT, "rev-parse", tag + "^{commit}"],
                         capture_output=True, text=True).stdout.strip()
            if tc and tc != head:
                fails.append("REBUILD mode but declared tag %s (%s) is not this tree's "
                             "commit (%s) -- the deposit is stale against this content; "
                             "cut a NEW deposit version instead of rebuilding "
                             "(audit 2026-07-20 22:57)" % (tag, tc[:8], head[:8]))
            else:
                print("boundary: REBUILD mode (--verify-git HEAD OK; tag == HEAD)")
    else:
        print("boundary: CUT mode (git_commit == HEAD after fresh --regen)")

    # Bundle-content linter (audit 2026-07-19 08:32): the README template must describe
    # the FULL strict chain and must not overpromise the audit-chain contents.
    README = README_TMPL.format(VERSION=VERSION, DATE=_manifest_date())
    if "COUNTED Office_Products" not in README or "FIR-breadth adjudicator" not in README:
        fails.append("README template omits the counted Office V3 / FIR-breadth gate steps")
    if "core historical" not in README:
        fails.append("README template lacks the core-historical-audit-documents wording")
    _lower = README.lower()
    for _k in range(len(_lower)):
        if _lower.startswith("audit chain", _k) and "historical" not in _lower[max(0, _k - 80):_k]:
            fails.append("README template uses bare 'audit chain' wording (must be scoped historical)")
            break

    if fails:

        print("CONSISTENCY GATE FAILED -- bundle NOT built:")

        for f in fails:

            print("  -", f)

        raise SystemExit(2)

    print("consistency gate OK (metadata versions + manifest boundary agree with %s)" % VERSION)





def main():

    import argparse
    ap = argparse.ArgumentParser(description="archival deposit bundle builder (fail-closed)")
    ap.add_argument("--check-only", action="store_true",
                    help="run the consistency gate and exit without building")
    ap.add_argument("--candidate", action="store_true",
                    help="build/validate an explicitly unpublished current-tree candidate without requiring a tag")
    args = ap.parse_args()
    consistency_gate(candidate=args.candidate)

    # payload-completeness scan runs in BOTH modes (audit 23:08: the check-only branch
    # previously returned before this scan -- a latent fail-open).
    missing = [f for f in FILES if not os.path.exists(os.path.join(ROOT, f))]
    if missing:
        for f in missing:
            print("MISSING:", f)
        raise SystemExit(2)

    if args.check_only:
        print("check-only: consistency gate + payload-completeness scan passed; no bundle written")
        return

    os.makedirs(os.path.dirname(OUT), exist_ok=True)

    def zinfo(name):
        zi = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
        zi.compress_type = zipfile.ZIP_DEFLATED
        zi.external_attr = 0o644 << 16
        return zi

    sums = []

    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:

        README = README_TMPL.format(VERSION=VERSION, DATE=_manifest_date())
        z.writestr(zinfo(PREFIX + "README_DEPOSIT.txt"), README)

        sums.append((hashlib.sha256(README.encode("utf-8")).hexdigest(), "README_DEPOSIT.txt"))

        for rel in sorted(FILES):

            ap = os.path.join(ROOT, rel)

            data = open(ap, "rb").read()

            if not rel.lower().endswith((".pdf", ".zip", ".gz", ".png")):

                data = data.replace(b"\r\n", b"\n")
                assert b"\r\n" not in data

            z.writestr(zinfo(PREFIX + rel), data)

            sums.append((hashlib.sha256(data).hexdigest(), rel))

        body = "\n".join(f"{d}  {n}" for d, n in sums) + "\n"

        z.writestr(zinfo(PREFIX + "SHA256SUMS.txt"), body)

    digest = sha256(OUT)

    with io.open(OUT + ".sha256", "w", encoding="utf-8") as f:

        f.write(f"{digest}  {os.path.basename(OUT)}\n")

    n_entries = len(FILES) + 2  # + README + SHA256SUMS

    print(f"wrote {OUT}")

    print(f"entries: {n_entries} | bytes: {os.path.getsize(OUT)} | sha256: {digest}")





if __name__ == "__main__":

    main()

