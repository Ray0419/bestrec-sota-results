# STATUS: APPROVED BY THE THIRD-PASS AUDIT (2026-07-10) — narrow claim accepted

> **Codex third audit** (`CLAUDE_SOTA_THIRD_RESUBMISSION_AUDIT_2026-07-10.md`): **"Approve the
> narrow V2 claim, with mandatory wording limits… Accept the narrow V2 result claim."** The
> auditor independently re-ran the gate (both arms PASS), re-verified all 20 sidecar hashes
> (20/20 match), re-adjudicated the clean rebuild (PASS; max gated-vs-rebuild deviation
> 0.000112), and confirmed code-hash identity. The approved claim wording is exactly the frozen
> wording below; the forbidden phrasings ("statistically significantly better", "general SOTA",
> "SOTA on Amazon Reviews 2023", "paired superiority") are binding. The four minor copyedit items
> (M1–M4: ChronoSID 0.0346, driver log tracked, commit chronology made unambiguous, deviation
> stated in the paper) are all applied as of the commit carrying this note.

# (superseded) STATUS: RE-CONFIRMED UNDER THE V2 PRE-REGISTERED, PROVENANCE-MANIFESTED PROTOCOL (2026-07-08, EXEC2)

> **Second-pass audit note (2026-07-08):** Codex's resubmission audit
> (`CLAUDE_SOTA_RESUBMISSION_AUDIT_2026-07-08.md`) **accepts the V2 numbers** ("no longer reject
> the V2 numbers"; it independently reproduced both arms and verified all 10 per-user sidecars
> row-by-row) while rejecting the *package* on six packaging/wording defects (R1–R6). All six are
> addressed: sidecars tracked in git + hashed manifest (`_bestrec_run/SOTACONF_V2_sidecar_manifest.json`);
> errata for the prereg's overstated sidecar-hash/interaction-count/commit-rule claims
> (`SOTA_CONFIRM_PREREG_V2_ERRATA.md`); manuscript updated to v3.6 with the confirmed claim and
> 2026 SID positioning; manifest emitter now embeds sidecar + code hashes; clean-rebuild mode
> added and a from-scratch rebuild demonstration recorded. The deviation (manifests at `86816be`,
> a doc-only descendant of the prereg commit `832a8ff`) is a **documented protocol deviation**,
> not a claimed literal pass.

**The V2 pre-registered dual gate PASSED under clean provenance** — see
`SOTA_CONFIRM_V2_RESULTS.md` §5 for the final adjudication (k16 fresh 5-seed CI-LB 0.04096 >
0.0406 AND k8 CI-LB 0.04083 > 0.0406, 10/10 fresh seeds above, all manifests single-commit
`86816be…` / clean / hash-matched; EXEC1 was voided by the provenance tripwire and cured by
full re-execution — chronology and disclosed deviation documented there). The ONLY claim made is
the frozen per-category point-estimate wording in that file. The withdrawal notice below is
retained as the historical record of the Codex audit response.

---

# (historical) STATUS: CLAIM WITHDRAWN PENDING AUDIT-PROOF RE-CONFIRMATION (2026-07-08)

**The 2026-07-06 "scoped, pre-registered, selection-free SOTA" claim previously in this file has
been WITHDRAWN** in response to the Codex audit (`CLAUDE_SOTA_RESULT_AUDIT_2026-07-08.md`), which
rejected it as publication-grade. The audit did NOT find the numbers wrong — it verified all five
fresh-seed values recompute exactly, all-users evaluation, correct masking/NDCG, and dataset stats
matching the comparator paper. The rejection is about **auditability**:

- **F1:** the pre-registration was not immutable (untracked file; edited after results ⇒ mtime
  cannot prove the protocol predated the data).
- **F2:** result artifacts lacked provenance manifests (no command/git-hash/data-hash/environment).
- **F3/F5:** wording too strong for a single-seed published comparator ("SOTA" ⇒ must be
  "exceeds the published point estimate"; one category, one metric).
- **F6/F7:** 2026 literature positioning (ReSID, ChronoSID) and clean-rebuild evidence missing.

## What stands (verified by the audit itself)

Seeds 20260613–17 (k16): 0.04151 ± 0.00033, 95% CI [0.04111, 0.04191], all 5 > published 0.0406;
k8 arm 0.04159 ± 0.00033, CI-LB 0.04118, 5/5. These are now classed as **consumed exploratory
evidence** — encouraging, not decisive.

## The re-confirmation (in progress)

Per the audit's approval path: `SOTA_CONFIRM_PREREG_V2.md` (committed to git BEFORE any V2 run)
freezes the code commit, exact commands, never-inspected seeds **20260618–22**, data hashes, a
DUAL k16+k8 gate, and the exact claim wording. Every V2 run emits a provenance manifest
(command, git commit + dirty flag, environment, data SHA256s, n_interactions) and a per-user
record sidecar. Results will be recorded in `SOTA_CONFIRM_V2_RESULTS.md` — this prereg file is
never edited after commit.

**Approved claim wording (the only claim that will be made if the V2 gate passes):**
> Our five-seed mean and seed-level 95% confidence interval exceed the published HSTU-BLaIR
> point estimate (NDCG@10 = 0.0406; Liu 2025) on Amazon Reviews 2023 Musical_Instruments under
> our reproduced 5-core leave-last-out full-catalog protocol. The comparator is a single-seed
> published number; its implementation cannot run on our hardware (sm_120, proven via WSL), so
> no paired or distributional comparison is possible. This is a per-category point-estimate
> comparison, not a general SOTA claim.

*(This file intentionally remains present: it is the scheduled pipeline's termination sentinel.
The experimental program is concluded; do not resume autonomous experiments.)*
