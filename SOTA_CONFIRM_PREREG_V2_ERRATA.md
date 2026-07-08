# Errata to SOTA_CONFIRM_PREREG_V2.md (2026-07-08, post-resubmission-audit)

The prereg file itself is frozen (never edited after its introducing commit `832a8ff…`); per its
own no-edit rule, corrections are recorded here. Three errata, all raised by the Codex
resubmission audit (`CLAUDE_SOTA_RESUBMISSION_AUDIT_2026-07-08.md`).

## E1 — Interaction-count wording (audit R4)

The prereg wrote: *"interactions: train 396,958 / valid 57,439 / test 57,439 (matches the
comparator paper's reported 511,835 total)."* The per-split counts are correct, but their sum is
**511,836 — one more than the paper's 511,835**. "Matches" was wrong; the correct statement is
"differs by exactly one interaction (+0.0002%)".

**Investigation (2026-07-08, verified from the frozen CSVs):** our 511,836 rows are all unique —
zero exact-duplicate rows, zero duplicate (user,item) pairs within or across splits — and
users (57,439) and items (24,587) match the paper exactly. The single-interaction difference
therefore originates in the comparator paper's own counting or a one-row difference in their
export; it cannot be localized further without their pipeline.

**Materiality:** none. Leave-last-out evaluation ranks exactly one held-out target per user
(57,439 targets under both counts, since user counts match exactly); a ±1 difference in one
user's training history length cannot materially change full-catalog LLOO metrics. The frozen
split SHA256s in the prereg remain the ground truth of what was evaluated.

## E2 — "Sidecar SHA256s recorded in the results file" (audit R2)

The prereg promised sidecar hashes would be recorded. The gated EXEC2 result JSONs do **not**
contain them (the manifest code at gate time recorded data hashes but not sidecar hashes).
Correction delivered in two parts:

1. `_bestrec_run/SOTACONF_V2_sidecar_manifest.json` — bytes, row count (57,439 each), and SHA256
   for **all 20** sidecars (10 gated EXEC2 + 10 preserved EXEC1), committed to git.
2. The manifest emitter in `run_sasrec_sbert.py` now embeds `user_records_path`,
   `user_records_n`, and `user_records_sha256` (plus a `code_sha256` family for the three
   protocol scripts) in every future result JSON — demonstrated by the clean-rebuild runs.

The gated EXEC2 JSONs are NOT regenerated (they are the adjudicated artifacts; rewriting them
post-gate would be worse than the omission). All 20 sidecars are now tracked in git (audit R1),
with the `.gitignore` exception documented inline.

## E3 — Commit-equality rule (audit R3)

The prereg's Rule zero requires manifests to record the prereg-introducing commit (`832a8ff…`).
The gated EXEC2 manifests record `86816be…` — two documentation-only commits later, the result of
absorbing autonomous-agent doc edits that had voided EXEC1. **The literal rule was NOT followed;
this is a documented protocol deviation**, not a claimed pass: immateriality evidence is the
empty `git diff 832a8ff..86816be -- '*.py' '*.sh'`, the untouched prereg file, and identical
data hashes. Wording anywhere that implies the exact rule was satisfied is superseded by this
erratum. For future campaigns the manifest now embeds `code_sha256` for the protocol scripts, so
code identity is verifiable from the artifact itself regardless of doc-only commits.
