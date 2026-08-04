# Response to Codex Audit (2026-07-08) — Resubmission Package

Audit: `CLAUDE_SOTA_RESULT_AUDIT_2026-07-08.md` (verdict: reject as publication-grade SOTA).
Response prepared: 2026-07-08. Every blocking finding is addressed below; the decisive evidence
is the **V2 pre-registered confirmation** on never-inspected seeds 20260618–22.

**Commit chronology (unambiguous, per third-audit M3):** the prereg was introduced and frozen at
`832a8ff`; the **gated EXEC2 campaign ran at `86816be`** (a doc-only descendant — deviation
disclosed in errata E3, code identity proven by empty protocol diffs); the **clean rebuild ran at
`89f32fb`** (code hashes embedded in its manifests match the protocol files). The literal
commit-equality rule of the prereg was NOT satisfied; the deviation is documented, not claimed
away.

## Point-by-point

| Audit item | Resolution |
|---|---|
| **F1 — preregistration not auditable** (untracked, mtime after results) | **Fixed structurally.** `SOTA_CONFIRM_PREREG_V2.md` is **committed to git (832a8ffcaf67) BEFORE any V2 run**, carries a no-edit rule (results go to a separate file), frozen config/commands/seeds/data-hashes/decision-rule/claim-wording. Every V2 result JSON embeds the git commit + dirty-tracked flag; the summarizer voids the gate on any mismatch. Seeds 20260608–17 reclassified as **consumed exploratory evidence** (audit fix #1/#3 accepted in full). |
| **F2 — artifacts lack provenance** | **Fixed in code** (same commit): every result JSON now embeds `provenance` = created_at, full argv, git commit/branch/dirty-tracked, python/torch versions, GPU, hostname, train/valid/test interaction counts, SHA256 of all four data files, best-val epoch. Verified working (smoke + V2 runs). |
| **F3 — comparator statistics insufficient** | **Accepted; wording frozen** in the prereg to exactly the audit's acceptable form: *"exceeds the published HSTU-BLaIR point estimate under our reproduced protocol"* — never "statistically significantly better than HSTU-BLaIR." The infeasibility of a comparator rerun (sm_120 "no kernel image", WSL-proven) is stated in `PROTOCOL_PARITY_APPENDIX.md` §5 (audit fix #6). |
| **F4 — thin margin needs strong reproducibility** | Addressed by the combination of: immutable prereg + clean-commit manifests (F1/F2), the **dual k16+k8 gate** (kernel-choice-free), frozen data hashes, per-user record sidecars enabling tie/rank/bootstrap diagnostics, and the not-easier-split floor checks (appendix §4). The margin itself is what it is — the claim wording is scoped accordingly. |
| **F5 — scope too broad** | `SOTA_ACHIEVED.md` rewritten: V1 claim **withdrawn**; the only permissible claim is the frozen per-category point-estimate wording. File name retained solely as the scheduled pipeline's termination sentinel, with the withdrawal notice at the top. |
| **F6 — 2026 literature missing** | `PROTOCOL_PARITY_APPENDIX.md` §6 positions **ReSID** (arXiv:2602.02338, MI 0.0346, different filtering) and **ChronoSID** (arXiv:2607.03918, MI 0.0345 SID-protocol), plus TIGER/LIGER (Amazon-2014, not comparable). Claim confined to the HSTU-BLaIR protocol family. To be folded into PAPER_DRAFT related work after the V2 gate resolves (no tracked-file edits during runs, to keep manifests clean). |
| **F7 — no clean rebuild** | `_bestrec_run/run_sota_confirm_v2.sh` (committed) is a single idempotent command that regenerates all 10 result JSONs + per-user sidecars + the gate summary from a checkout of the prereg commit (data present). `summarize_sota_confirm_v2.py` re-verifies data hashes + commit consistency and prints the gate verdict. |
| **Fix #5 — per-user records** | Every run now writes `<out>.users.jsonl.gz`: dataset, seed, user_id, target_item_id, rank0, ndcg10, hr10, rr, pop_bucket (57,439 rows/run; verified). |
| **Fix #6 — comparator distribution** | Infeasible on this hardware (documented, appendix §5); limitation stated in the frozen claim wording per the audit's allowance. |
| **Bonus (audit F2 side-finding)** | The audit's code check plus our own sweep surfaced that `val_time_extra` was gated on `--time-bias` only; **fixed in the same commit** to also cover `--time-decay-kernel` (the historical c3 "val≫test" negative was an eval artifact; the headline configs never used that flag, so no gated number changes). |

## The V2 gate (pre-registered, decides the resubmission claim)

- Arms: k16 AND k8 (both must pass: fresh 5-seed 95% CI lower bound > 0.0406).
- Seeds: 20260618–22 (never inspected before this confirmation).
- Runs: launched 2026-07-08 from commit `832a8ffcaf67`, clean tracked tree; results below.

## V2 results — DUAL GATE PASSED under clean provenance (EXEC2)

| arm | fresh seeds 20260618–22 | mean ± sd | 95% CI-LB | >0.0406 |
|---|---|---|---|---|
| k16 | 0.04126 / 0.04108 / 0.04147 / 0.04152 / 0.04226 | 0.04152 ± 0.00045 | **0.04096** | 5/5 |
| k8 | 0.04118 / 0.04099 / 0.04151 / 0.04150 / 0.04084 | 0.04120 ± 0.00030 | **0.04083** | 5/5 |

- All 10 manifests: `git_commit=86816be…`, `dirty_tracked=false`, data SHA256s = prereg, n_eval=57,439.
- **The integrity system was demonstrated live:** EXEC1 passed statistically but was VOIDED by the
  dirty-tree tripwire (an autonomous doc-bot edit mid-campaign — diagnosed, disabled, absorbed);
  EXEC2 is the clean full re-execution. EXEC1↔EXEC2 per-seed agreement ±0.0003. Chronology +
  the one disclosed deviation (manifest commit `86816be` vs prereg-introducing `832a8ff`; empty
  code diff between them) in `SOTA_CONFIRM_V2_RESULTS.md`.
- Claim made = the frozen wording, verbatim, nothing stronger.

**Resubmission bundle for re-audit:** `SOTA_CONFIRM_PREREG_V2.md` (committed pre-run, unedited) ·
`SOTA_CONFIRM_V2_RESULTS.md` (EXEC1 void + EXEC2 pass) · `PROTOCOL_PARITY_APPENDIX.md` ·
10 result JSONs with embedded manifests + 10 per-user sidecars · committed driver + adjudicator ·
`SOTA_CONTINGENCY_PLANS.md` (the pre-declared failure playbook) · this response.

---

# Second-pass response (to `CLAUDE_SOTA_RESUBMISSION_AUDIT_2026-07-08.md`)

The second audit **accepts the V2 numbers** and rejects the package on six items. Each is fixed:

| Finding | Fix |
|---|---|
| **R1 — sidecars untracked/ignored** | All **20** sidecars (10 gated EXEC2 + 10 preserved EXEC1) are now **tracked in git** (`.gitignore` exception documented inline), plus `_bestrec_run/SOTACONF_V2_sidecar_manifest.json` with bytes / row count (57,439 each) / SHA256 per file. Reviewers obtain them by cloning the repo. |
| **R2 — no sidecar hashes in result JSONs** | The gated JSONs are NOT rewritten (they are the adjudicated artifacts). Correction is via (a) the committed sidecar manifest above and (b) the manifest emitter now embedding `user_records_path/n/sha256` — demonstrated by the clean-rebuild runs. The prereg's overstated claim is formally corrected in `SOTA_CONFIRM_PREREG_V2_ERRATA.md` **E2**. |
| **R3 — literal commit rule not followed** | Conceded and reworded everywhere: it is a **documented doc-only protocol deviation** (never a claimed literal pass) — erratum **E3**. Structural fix for the future: manifests now embed a `code_sha256` family (model script, driver, adjudicator) so code identity is verifiable from the artifact regardless of doc-only commits. |
| **R4 — 511,835 vs 511,836** | Erratum **E1** with a data-level investigation: our 511,836 rows are all unique (zero duplicate rows / (user,item) pairs), users/items match the paper exactly; the ±1 cannot materially affect LLOO (one target per user; 57,439 targets both ways). "Matches the total" wording retracted. |
| **R5 — clean rebuild not demonstrated** | Driver now supports `OUTDIR=<fresh dir>` (no skip shortcut); adjudicator takes a directory argument. A full from-scratch rebuild into `_bestrec_run/rebuild_v2/` was executed and adjudicated (log + comparison committed). Data/cache availability for a fresh clone is documented in `PROTOCOL_PARITY_APPENDIX.md` §7. |
| **R6 — stale manuscript** | `PAPER_DRAFT.md` updated to **v3.6**: abstract + §5.2 carry the confirmed dual-kernel claim with the frozen caveats; §2 positions ReSID/ChronoSID; exploratory MI numbers labeled as such; the stale "LS-only 1-seed" note corrected to the 5-seed family. |

Also adopted: "audit-proof" phrasing removed in favor of "pre-registered, provenance-manifested";
the maximum-claim wording matches the auditor's §"What I Would Allow" verbatim.

## Clean-rebuild demonstration (R5 — completed)

`OUTDIR=_bestrec_run/rebuild_v2 bash _bestrec_run/run_sota_confirm_v2.sh` regenerated **all 10
runs from scratch** (fresh directory, no skip shortcut), from commit `89f32fb`, clean tree:

- Rebuild adjudication: **DUAL GATE PASS** — k16 mean 0.04150 (CI-LB 0.04092), k8 mean 0.04121
  (CI-LB 0.04084), 10/10 seeds > 0.0406, all manifests single-commit + clean + hash-matched.
- **Max |gated − rebuild| NDCG@10 across all 10 runs = 0.000112** (GPU-nondeterminism band) —
  the gated EXEC2 artifacts are reproducible from a single documented command.
- The rebuild JSONs demonstrate the R2/R3 structural fixes live: every manifest now embeds
  `user_records_{path,n,sha256}` and the `code_sha256` family (sidecar hashes are therefore in
  the committed JSONs; the rebuild sidecar files themselves are regenerable and ignored).
- Artifacts: `_bestrec_run/rebuild_v2/` (10 result JSONs + run logs) and
  `_bestrec_run/run_rebuild_v2_driver.log`.
