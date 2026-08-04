> **TOMBSTONE (audit 2026-07-25 04:00): the as-frozen protocol below (down to ERRATUM E1) is SUPERSEDED, NON-NORMATIVE and NON-COUNTABLE.** The V2 factorial as executed is OUTCOME-VISIBLE / protocol-deviated / representation-package-confounded. The AUTHORITATIVE disposition is ERRATUM E1 (bottom) + the hardened `adjudicate_ee_v2.py`, which emits `classification=OUTCOME_VISIBLE_PROTOCOL_DEVIATED_NONCOUNTABLE, countable=false, import_allowed=false, manuscript_allowed=false, verdict=DESCRIPTIVE_ONLY` and a `representation_package_contrast` (NOT a fusion effect). The original lines and the 6464d581 output are retained UNCHANGED as immutable forensic artifacts; this correction is ADDITIVE, not a history rewrite. No E-E V2 value is countable or manuscript-permitted; a clean E-E V3 is required.

# PREREG_EE_V2 — matched-backbone fusion factorial (the countable E-E test)

**Status: FROZEN before the factorial runs exist (committed-before-existence,
§5.3 disclosure ii).** Supersedes the quarantined E-E V1 pilot (PREREG_EE
ERRATUM E2). The adjudicator `_bestrec_run/adjudicate_ee_v2.py` is committed in
the same commit. NO factorial run has been executed or read at freeze time.

## Why this design (audit 2026-07-24 16:00, fix #2)
The V1 pilot compared two whole systems (our stack vs AlphaFuse), which differ in
model family, dims, loss, optimiser, tuning and biases — so it could not isolate
the fusion mechanism, and its cross-evaluator scoring was not the same estimand.
V2's PRIMARY test is a **matched-backbone factorial** that changes ONE thing —
AlphaFuse's text/ID null-space fusion, ON vs OFF — with everything else held
identical, and scores BOTH arms through the single shared evaluator
(`ee_baselines/ee_shared_eval.py`, frozen policy). This isolates the fusion
effect and removes the estimand confound by construction.

## Arms (identical except the ONE factor)
- **Arm ON — AlphaFuse** (`model_type=AlphaFuse`): ID embeddings learned in the
  null space of the MiniLM-384 language embeddings + text in the row space.
- **Arm OFF — SASRec** (`model_type=SASRec`): the SAME AlphaFuse-repo SASRec
  backbone with pure ID embeddings (no text/null-space fusion).
Everything else is IDENTICAL and FROZEN for both arms: our AR2023 5-core VG split
via the same adapter (left-pad L=50, per-prefix, minilm re-index); `hidden_dim=128`,
`num_blocks=2, num_heads=1, dropout_rate=0.1`; training `loss_type=infoNCE,
neg_ratio=64, lr=1e-3, batch_size=256, epoch=500, patience=50, temperature=0.07`;
`ID_embs_init_type=zeros`; seeds `{22,23,24}` (paired by seed). AlphaFuse-specific
`null_dim=64, language_embs_scale=40` apply to the ON arm only (they don't exist
in the OFF arm). **Equal tuning budget = ZERO per-arm search** (same frozen config
both arms), so the only difference is the fusion factor.

## Shared evaluation (the SINGLE estimand)
Both arms produce per-user full-catalogue scores (`ee_alphafuse_scores.py`,
generalised to `--model_type`) fed through `ee_shared_eval.target_rank0`:
full-catalogue eligibility, mask_seen=True (target never masked), strict-greater
ties, HR/NDCG/MRR@{5,10,20,50}. The ON arm may reuse the VALIDATED V1 AlphaFuse
checkpoints (config/seed-identical; the V1 quarantine was about the evaluator,
not the training; their unmasked re-score reproduced the pilot exactly); the OFF
arm is trained fresh under the identical config. Both checkpoints' SHA-256 are
recorded.

## Estimand + result (DESCRIPTIVE)
Primary quantity: the **fusion effect** on VG under our protocol,
`Δ = NDCG@10(ON) − NDCG@10(OFF)`, PAIRED by seed, reported as mean ± sd over the
3 seeds, plus the full metric family for each arm. This is a within-AlphaFuse
ablation ("does the null-space text fusion change ranking on our data?"), NOT a
comparison to our stack, NOT SOTA, NOT a superiority claim of any system over
another. A near-zero or negative Δ is reported with equal prominence to a positive
one.

## Secondary (lower prominence, descriptive)
The two whole systems under the SAME shared evaluator — AlphaFuse-masked (from
`ee_alphafuse_scores.py`, ~0.048 dev-probe) vs our stack (0.064, recorded, also
masked) — explicitly labelled CONFOUNDED (architecture/training/tuning differ),
positioning only, never the primary and never a superiority claim.

## Provenance + custody
Register exact checkpoint filenames, seeds, and SHA-256; require exactly seeds
{22,23,24} for BOTH arms (else INCOMPLETE, nonzero exit); per-user rank sidecars
written so HR/NDCG + clustered CIs reconstruct; endpoints (`results_EE_*`) sealed
(gitignored + seal hook); pin the upstream AlphaFuse commit SHA in the results.

## Decision rule (adjudicate_ee_v2.py — REPORTING gate)
1. Load ON and OFF per-seed shared-eval results; require exactly seeds {22,23,24}
   for each arm and `shared_evaluator==True`; else `INCOMPLETE`.
2. Assert every metric finite; compute each arm's mean±sd and the PAIRED
   per-seed Δ (ON−OFF) mean±sd for NDCG@10 (+ family).
3. Emit `ee_v2_adjudication.json`; verdict vocab = `REPORTABLE` / `INCOMPLETE`
   only; NO pass/fail, NO superiority. The adjudicator scans its OWN output for
   forbidden superiority/SOTA tokens and fails closed if any appear.
4. LLM2Emb remains a separate item: a fair benchmark OR an executable exclusion +
   narrowed novelty (not folded into this factorial).

## Admissible manuscript wording (template)
"Under our full-catalogue leave-last-out protocol on Video_Games and a single
shared masked evaluator, AlphaFuse's null-space text/ID fusion changes NDCG@10 by
Δ (mean of 3 paired seeds) relative to the same SASRec backbone without fusion.
We report this as a within-method ablation on our split under the disclosed
MiniLM-384 substitution; it is not a comparison to our own model and asserts no
best-system claim."

## ERRATUM E1 (2026-07-24 21:59 audit, ACCEPTED) — V2 is descriptive, not countable
The audit CONFIRMED seven defects; V2 is preserved as OUTCOME-VISIBLE / protocol-
deviated DESCRIPTIVE material and is NOT integrated:
1. **Outcome-visible before freeze:** the ON arm's shared-masked scores were
   validated at `a19781f3` (18:21) before V2 froze at `7b3cf952` (19:23) — so V2
   is descriptive, not confirmatory (§5.3 disclosure vii class).
2. **NOT a one-factor fusion isolation:** ON (frozen projected text + 64-d
   trainable ID residual) vs OFF (128-d learned ID) change text, initialization,
   capacity AND parameter allocation together. Reframed as a **representation-
   package ablation**; the +0.00878±0.00137 is a package effect, not a null-space
   fusion effect.
3. **Incomplete-history masking:** `ee_shared_eval` masks the length-50 input, not
   the full paper history (`run_sasrec_sbert.py` masks train+val complete); ~0.48%
   of users have >50 history. Not the paper's estimand for those users.
4. **Selection mismatch:** checkpoints chosen by AlphaFuse's native UNMASKED
   validation, then tested under the shared masked evaluator.
5. **Fail-open adjudicator:** accepts self-asserted `shared_evaluator`, exits 0 on
   INCOMPLETE, no identity/hash/rank checks, no reconstruction from ranks.
6. **No terminal lifecycle / provenance:** ad-hoc queue (completion inferred from
   filename), no immutable attempts, no per-user rank sidecars, no SHA bundle.
7. **Weak pairing:** same numeric seeds != common randomness across arm shapes;
   3 seeds descriptive.

**E-E V3 (required before any countable/integrated use):** fresh UNSEEN ON+OFF
seeds (>=8); complete-history masking; the SAME masked evaluator for validation
selection AND test; exact tie/target rules + synthetic+real conformance test vs
`run_sasrec_sbert.py`; fail-closed runner+adjudicator (immutable attempts, atomic
completion, rank sidecars, reconstructive metrics, exact schema, nonzero on
incomplete); full source/data/config/env/checkpoint identities; a
representation-package framing OR added controls (standard-init ID-only,
zero/shuffled text, random basis, capacity/param-matched); report params/FLOPs/
mem/latency; independent-arm inference or frozen shared RNG streams.
