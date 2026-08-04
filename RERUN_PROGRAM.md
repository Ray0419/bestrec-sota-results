# RERUN_PROGRAM — maintainer "fold all 5" directive (2026-07-20)

The maintainer folded the five maintainer-gated audit items into the automation loop.
This file is the loop's tracker; quiet ticks service THIS program before companion work
(maintainer directive 2026-07-20 supersedes the earlier quiet-tick default).

## 1. Tail estimand rerun (P0) — IN PROGRESS
- [x] Design frozen: `PREREG_TAIL_FIR_V2.md` (independent arms, 8 seeds/arm, per-row
      sidecars, tie-safe whole-group strata + zero-exposure bin, Welch + Holm).
- [x] Command list mechanically generated + smoke-validated (`_bestrec_run/gen_tfv2.py`,
      `tfv2_commands.txt`, config parity exact).
- [x] Campaign launched (sequential single-GPU queue: MI → IS → CDs → VG; 64 runs;
      resumable; logs `_bestrec_run/tfv2_logs/`).
- [x] `adjudicate_tfv2.py` committed before inspection (+ degenerate-bin reporting guard).
- [x] ADJUDICATED 2026-07-20: **E1/E2/E3 ALL PASS under Holm** (TFV2_ADJUDICATION.md).
      Honest secondaries folded into the papers verbatim: zero-exposure bin degenerate
      at 0.0 both arms; exclude-boundary sensitivity n.s. (boundary-group concentration
      stated); cross-dataset MI-VG contrast DID NOT replicate (p=0.13; descriptive now).
      Papers updated; tfv2 graph family + counted strict-gate step wired (175 cells /
      15 families).

## 2. FIR cloned-backbone / valid-design rerun (P0) — IN PROGRESS (same campaign)
- Executed as the IS/CDs arms of PREREG_TAIL_FIR_V2 under the pre-specified
  independent-arm design (audit 19:56's option (b)). Component-level attribution
  (cloned backbones, weight-decay controls, tap/gate release) remains a possible
  V3 follow-up — out of scope for V2 and stated so in the prereg.

## 3. Public release — IN PROGRESS
- [x] 12 splits + 4 caches (1.09 GB) uploading to `v0.9-audit-evidence` (background).
- [x] Tracked-file secret scan (pattern pass): no credential-shaped hits (jsonl matches
      are product-text false positives).
- [x] Verify uploaded asset list + hashes against `RELEASE_MANIFEST.json` (2026-07-20: auditor API sweep matched all 129 data digests; 138 release-class assets incl. nine current parity files).
- [x] Flip repository visibility to PUBLIC (done 2026-07-20).
- [x] Clean unauthenticated clone (2026-07-20): from-zero clone + submodules + 138-asset bootstrap + full strict PASS at `9603902e` (`_bestrec_run/CLEANCLONE_TRANSCRIPT_20260720.log`); `--verify-git HEAD` OK.
- [x] `v1.1.10-deposit` CUT 2026-07-20 (this tick) with README/§8/DOI docs synced to the
      now-true public state.

## 4. Front-end rewrite + typography — QUEUED (next ticks)
- [x] Concise ~225-word abstract in place (2026-07-20); long form moved verbatim to
      Appendix E ("Extended summary") in both formats.
- [x] Dataset table: raggedright wrapped columns (0.20/0.30 linewidth) + footnotesize.
- [x] Three-panel figure now a rotated full-page float in TORS (~30% larger type).
- [x] Re-render, rebuild, full gate chain (green through the 17:54 round; H8 added).

## 5. External timestamps + venue check — IN PROGRESS
- [x] OpenTimestamps chosen (no account creation needed; Bitcoin-anchored).
- [x] Stamped `PREREG_TAIL_FIR_V2.md`, `tfv2_commands.txt`, HEAD-state attestation; Bitcoin attestations complete — chronology limits disclosed (§5.3 (vii): earliest attestation postdates first result; TFV2 labeled outcome-visible);
      commit the `.ots` proofs; upgrade stamps when calendars aggregate (later tick).
- [ ] Papers: past campaigns keep the "no independent external timestamp" limitation
      verbatim; the V2 campaign may state its OTS anchoring once proofs are committed.
- [ ] TORS portal/author-guideline check: automated fetch attempted; if blocked (403),
      this remains the one truly manual maintainer step and is flagged as such.

## Standing rules
One GPU job at a time; never overwrite `results_*.json`; claim set only narrows until
adjudication; every number that enters a paper is recomputed/graphed first.
