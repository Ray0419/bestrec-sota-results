# Contingency Playbook — if the V2/EXEC2 confirmation still fails (2026-07-08)

**Plan A (primary, in flight):** EXEC2 completes under the clean tree → committed summarizer
adjudicates the pre-registered dual gate (k16 AND k8 fresh CI-LB > 0.0406, manifests single-commit
+ clean + hash-matched) → results recorded in `SOTA_CONFIRM_V2_RESULTS.md` → final commit →
resubmit to Codex with `RESPONSE_TO_CODEX_AUDIT.md`.

## Hard rules that bind EVERY backup plan (anti-gaming discipline)

- **R1 — No seed shopping.** A statistically failed gate is never "retried" on the same config
  with new seeds. New runs require a *materially different hypothesis* (new config/claim) under a
  *new committed prereg*.
- **R2 — No post-hoc gate edits.** A prereg is never reworded after its results exist. Deviations
  are documented, never silently patched.
- **R3 — Voided ≠ failed.** A provenance void (tripwire) is cured by *re-executing the identical
  pinned protocol* under clean provenance — that is re-execution, not seed shopping (the seeds
  were frozen before any result existed).
- **R4 — Every outcome is recorded**, including permanent downgrades. Negative results ship.
- **R5 — Disclosure beats deletion.** Ensembles, protocol differences, dependency changes — usable
  only with explicit disclosure in the claim wording.

---

## Failure mode 1 — provenance tripwire fires again (dirty tree / multi-commit / hash mismatch)

**B1. Iterated cure (cheapest).** Diagnose the writer (`git status -uno` + file mtimes), absorb
the drift into a commit, re-execute ONLY the voided runs (per R3; ~9 min each). Guard for the next
attempt: verify 0 tracked modifications immediately before launch and immediately after each run.
*Trigger:* any dirty manifest in EXEC2. *Cost:* minutes–1 h. *Resolves:* ~90% of tripwire cases.

**B2. Isolated-worktree execution (structural fix).** `git worktree add` a pristine checkout of
the prereg commit in a directory no agent/bot ever writes to; run the campaign there (data via
absolute paths). The main working tree can then drift freely without contaminating manifests.
*Trigger:* B1 fails twice, or a writer can't be eliminated (e.g., un-killable stale agent procs).
*Cost:* ~30 min setup + rerun. *Resolves:* essentially all tree-contamination risk.

**B3. Process quarantine.** The ~70 stale headless agent processes are the last uncontrolled
writers; ask the user to quit+reopen the Claude app (kills them all), confirm all 5 scheduled
tasks disabled, then rerun. *Trigger:* evidence a stale agent (not a scheduled dispatch) wrote
mid-campaign. *Cost:* user action + rerun.

## Failure mode 2 — the fresh statistics miss the gate (either arm CI-LB ≤ 0.0406)

**B4. Honor the prereg, publish the downgrade (mandatory first step).** Record "statistical
near-tie with the published single-seed point estimate" in `SOTA_CONFIRM_V2_RESULTS.md`,
exactly as the prereg's fail-clause requires. All subsequent plans build on top of this honest
baseline — none replaces it.

**B5. Pooled-evidence descriptive claim (no new runs).** Report the full labeled evidence:
15 seeds (10 exploratory + 5 confirmatory), N/15 above 0.0406, both arms, with the confirmatory
CI as the headline. If e.g. 14/15 seeds clear, the honest wording is "matches, and nominally
exceeds in 14 of 15 runs" — weaker than SOTA, still a strong result for the paper. *Cost:* zero.

**B6. Stronger model, clean two-dataset methodology (the real second shot).** Build a V3 config
with more headroom, tuned ONLY on Video_Games (independent dataset), then frozen and confirmed
once on MI under a new committed prereg (new seeds 20260623+; R1-compliant because the
hypothesis/config is new). Ranked candidate levers, all evidence-backed and untested on MI:
richtext encoder (title+brand+category — helped Beauty; MI is text-rich), BLaIR-on-MI (domain
encoder; only ever tested on VG where text matters less), epochs 30–40 (MI only ever ran 20;
VG's best used 40), d_model 96–128, augment-factor 2, n_layers 6. Expected headroom: +1–4%.
*Trigger:* B4 recorded and margin was close (CI-LB ≥ ~0.0400). *Cost:* ~1 day GPU.

**B7. Disclosed ensemble arm (last-resort margin builder).** c4 showed 2-model rank-fusion adds
+5.8% on VG. A 2-model MI ensemble would likely clear 0.0406 with a wide margin. Usable ONLY as
an explicitly-labeled "ensemble of two" row next to the single-model row (R5) — the claim then
reads "a two-model ensemble of our method exceeds…; the single model matches…". Weaker
scientifically; Codex/venues may discount it; still an honest, quantified statement.
*Trigger:* B6 fails or is unavailable. *Cost:* ~1 h GPU.

## Failure mode 3 — Codex rejects the EXEC2 package on the commit-mismatch deviation

**B8. Flawless-letter EXEC3.** New prereg V3 (content identical, fresh seeds 20260623–27),
committed; then ZERO further commits until the campaign completes, enforced by B2's isolated
worktree (bots can't dirty it, and nothing needs committing mid-run). Manifests then equal the
prereg-introducing commit exactly — no deviation note needed at all. *Trigger:* Codex flags the
86816be≠832a8ff letter-violation as blocking. *Cost:* ~90 min. *Note:* R1 is satisfied — this is
a provenance re-execution (R3), and if Codex explicitly requests it, it is the audit's own
prescribed path.

## Failure mode 4 — Codex insists on a comparator distribution (single-seed 0.0406 insufficient)

**B9. Compatible-hardware comparator rerun (the definitive fix).** Rent an sm_80/sm_90 GPU
(A100/RTX 4090 — RunPod/Lambda/vast.ai, ~$10–50) and run the official HSTU-BLaIR repo (their
pinned env installs cleanly there) on OUR exported MI split for 3–5 seeds → a true comparator
distribution → paired seed-level test, upgrading the claim to "statistically exceeds the
reproduced comparator." Also finally answers the VG-0.0760 question. *Trigger:* F3-style
objection repeated. *Cost:* small $ + a day; **requires user approval** (external service).

**B10. Local comparator port, time-boxed.** Attempt their repo on THIS GPU with a modern stack
(torch 2.7+cu128 supports sm_120; swap fbgemm/torchrec pins for newer builds or CPU fallbacks).
Previously judged likely-breaking — but one time-boxed day is a legitimate backup; any success
yields a local comparator distribution with a disclosed dependency deviation (R5).
*Trigger:* B9 not approved. *Cost:* ≤1 day; success odds ~25–40%.

## Failure mode 5 — rejection on thin margin / single-category scope

**B11. Second front: pre-registered tail-metric confirmation.** The VG tail@50/@100 text-vs-ID
effect is huge and already replicated informally (z = 6.3–9.1, 5/5 seeds). Freeze it into its own
committed prereg (new seeds) and confirm — giving the paper a second independent confirmed claim
that does not depend on the 1–2% MI margin. *Trigger:* "margin too thin to carry a paper."
*Cost:* ~2 h GPU.

**B12. Third category expansion.** Preprocess + encode a new sparse, text-rich AR2023 category
(Office_Products, Digital_Music, or Arts_Crafts — the regime where our stack wins per the
connectivity law), tune nothing (frozen MI/VG config), pre-register, run 5 seeds vs that
category's published numbers. A per-category win on a *second* category transforms the claim's
robustness. *Trigger:* single-category scope flagged as blocking. *Cost:* data download +
~half a day.

**B13. Drop the SOTA framing; ship the bulletproof paper.** The six-audit sweep certified that
the architecture claims (causal spectral filter, label smoothing, +2.7% text, MI transfer,
negative-result map) and the cross-dataset Welch contrast survive ANY correction. Submit the
paper on those, reporting MI as "matches/nominally exceeds the published point estimate" in one
table row without SOTA language anywhere. The paper never needed the SOTA line to be publishable.
*Trigger:* SOTA claim unrecoverable within budget. *Cost:* wording only.

## Failure mode 6 — systemic / gatekeeper disagreement

**B14. Third-party referee.** Package the complete evidence chain (prereg commits, manifests,
per-user records, EXEC1+EXEC2 artifacts, both audits) and put the single question "what one
change would make this acceptable?" to an independent auditor (a fresh Codex session, another
model, or a human reviewer). Prevents an endless two-party loop and converts taste disputes into
a concrete requirement list. *Cost:* ~1 h.

**B15. Preprint + artifact release.** Post the honest version (B13 framing) to arXiv with the
full reproducibility bundle (rebuild script, manifests, per-user sidecars, prereg chain) and let
open review adjudicate; resubmit to the gatekeeper with community feedback incorporated. The
reproducibility bundle itself is also submittable to artifact/reproducibility tracks where the
audit-proof process is the contribution. *Trigger:* all local avenues exhausted. *Cost:* packaging
day; **publishing is an external action — requires explicit user approval.**

---

## Execution order (decision tree)

```
EXEC2 adjudication
├─ PASS clean ──────────────→ finalize results + response + final commit → resubmit (Plan A)
├─ provenance void ────────→ B1 → (repeat once) → B2 → B3
├─ statistical miss ───────→ B4 (mandatory) → close? → B6 → B7
│                                        └─ not close? → B11/B12 pivot or B13
└─ Codex re-rejects:
   ├─ commit-mismatch letter → B8
   ├─ comparator demand ────→ B9 (ask user) → B10
   ├─ margin/scope ─────────→ B11 → B12 → B13
   └─ anything else / loop ─→ B14 → B15 (ask user)
```

Standing constraints across all plans: loops stay disabled; one GPU job at a time; no result file
ever deleted (rename-preserve only); every outcome — pass, void, miss, downgrade — is recorded in
the results file and the ledger.
