# Standalone artifact repositories (2026-09-10)

The two papers now live in separate private repositories, split out of this monorepo on
2026-09-09/10. This file is the pointer of record in the parent.

## 1. TORS measurement paper — `bestrec-tors-artifact`

- **URL:** https://github.com/Ray0419/bestrec-tors-artifact (private)
- **Content:** verbatim extraction of `_release/bestrec_deposit_v1.2.0.zip` (intended deposit tag
  `v1.2.0-deposit`, manifest hash-parent `fe8ceac9`), 908 files + one `.gitattributes` (`* -text`)
  that pins byte-exact checkouts so the internal `SHA256SUMS.txt` remains verifiable.
- **Verification:** `uv --project _bestrec_run run python _bestrec_run/rebuild_hstu_submission.py --strict`
- **Update rule:** never commit new files into that repository — it would diverge from the deposit
  hashes. To update it, cut a new deposit here, then regenerate the repository from the new zip.

## 2. ρ(k)/π* RecSys short paper — `rhok-coverage-screen`

- **URL:** https://github.com/Ray0419/rhok-coverage-screen (private)
- **Content:** sigconf paper (tex + built PDF), `RESULTS.md` of record, preregs
  (`PREREG_RHO_K_V1`, `PREREG_SCALE_LOSS_V1`), derivation/design/related-work docs, AI-use
  statement, 14 code files (forced-coverage ρ(k) instrument, quota-mix coverage trade, frozen
  analyzers, ladder drivers, shared trainer), and 591 per-seed JSON evidence files.
- **Verification (no GPU):** from `_bestrec_run/`, `python poc_rho_k_analyze.py` and
  `python poc_cov_trade_analyze.py` regenerate every published verdict from the shipped JSONs
  (verified byte-identical at split time: C1 SUPPORTED; E2 P1 REFUTED on both datasets).
- **Source of truth:** extracted from this branch (`claude/brave-rhodes-0a7d09`) at commit
  `d8967913`; a README-command fix and an argv-robustness fix to `poc_rho_k_analyze.py` were made
  there first and backported to this branch in the same commit as this file.
- **Data:** splits and text caches are not redistributed in either artifact repo; the reproduction
  path of record is this project's immutable data release `v0.9-audit-evidence`.

## Deposit-builder defects found while verifying repository 1 (2026-09-26) — fix before the DOI upload

Running `rebuild_hstu_submission.py --strict` on the verbatim v1.2.0 deposit showed it cannot pass
its own one-command verification. Both causes are in `_bestrec_run/build_deposit_bundle.py`, so the
same defects are in `_release/bestrec_deposit_v1.2.0.zip`:

1. **34 required files are omitted.** The builder bundles only files named by the manifest sections
   and the active cell graph. Missing: `_bestrec_run/pyproject.toml`, `_bestrec_run/uv.lock` (so the
   README's `uv --project` command has no environment), `_bestrec_run/make_table_5_4_titration.py`
   (claim-map step fails), the 25 public COLDFUSE V1 `*.perusers.npz` (E-G step fails), and
   `run_5core_benchmark.py`, `run_fir_canonical_breadth.py`, `tfv2_commands.txt`,
   `run_tfv2_campaign.sh`, `test_fir_controls.py`, `PROTOCOL_PARITY_APPENDIX.md` (rerun procedures).
   All are tracked, public, and outside the seal patterns.
2. **LF normalisation breaks an integrity chain.** Text payloads are normalised to LF at bundle
   time, but run JSONs written on Windows were hashed over CRLF bytes, so the FIR active-control and
   pointwise-placebo adjudications fail `run_json_sha256` on an LF checkout (88/88 records match
   after restoring CRLF; 0 content differences).

Repository 1 carries the 34 files as byte-verified supplements plus a line-ending-aware integrity
check; with those and the 407 hydrated release assets, every other strict step passes (197 cells,
0 untraceable, 0 mismatches). The upstream fix: add the 34 files to the builder's inclusion set,
and either exempt run JSONs from LF normalisation or compare line-ending-normalised bytes in the
adjudicators; then cut v1.2.1 and re-run the verification from a fresh extraction.

## Anonymization note for review

Both repositories are private and named/attributed. RecSys review is mutually anonymous: before
sharing an artifact link with reviewers, create an anonymized mirror (e.g. Anonymous GitHub) of
`rhok-coverage-screen` with the AI statement's identity fields and this file removed.
