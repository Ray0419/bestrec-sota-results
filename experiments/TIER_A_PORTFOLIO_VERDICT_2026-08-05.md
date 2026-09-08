# Tier-A cold-start experiment portfolio: final verdict

Date: 2026-08-05 (Australia/Sydney)

## Executive verdict

All four prospective mechanism screens returned `NEW_DIRECTION`. RQ1--RQ3
completed their frozen integrity protocols. RQ4's computation and independent
deep verifier were clean, but a deterministic Windows path-separator check
failed after verification and before commit-marker publication. RQ4 is
therefore scientifically valid negative evidence with an explicitly
uncommitted control-plane status.

There is currently **no validated Tier-A main contribution** in this portfolio.
This is not a "run more seeds" or "tune a little more" outcome. Each screen
failed the prospective gate that would have authorized its next stage. The
conditional EB-NeRD, four-domain RQ2 confirmation, natural-data CR-UOT upgrade,
and temporal RQ4 K1 were therefore correctly not run.

| Direction | Integrity | Decisive result | Frozen action |
|---|---|---|---|
| RQ1: pool-offset degeneracy and warm-safe wrapper | Clean four-domain run | Only Software met the material span gate; no domain met the useful improvement-over-zero trade-off; wrapper had 0/4 positive paired CIs | `NEW_DIRECTION`; retain theorem/diagnostic only |
| RQ2: representation-selective semantic FIR | Clean two-domain GPU screen and two independent post-run audits | Semantic FIR selected epoch-zero identity in both domains; strict-cold gain, within-cold gain, and changed-rank fraction were exactly zero; 3/6 gates failed | `NEW_DIRECTION`; no multi-seed/four-domain confirmation |
| RQ3: anchored cost-regularized UOT | Clean 12-seed, four-regime synthetic screen | Failed clean safety, shifted mapping, unmatched retrieval, recovery, and relative runtime; fixed UOT/ridge were stronger where it mattered | `NEW_DIRECTION`; no natural-data upgrade |
| RQ4: fixed-UOT support-mass router | Clean child run and independent deep-chain verifier; commit marker absent after a path-string mismatch | Mass AUROC was 0.507 and 0.486; Spearman rho was 0.017 and -0.010; all five efficacy gates failed in both domains while stability/resource/integrity gates passed | `NEW_DIRECTION`; no K1, sweep, or outcome rerun |

## What the experiments actually establish

### RQ1

The exact diagnostic is real: a uniform cold-pool offset preserves every
within-pool ordering, moves cold- and warm-target metrics in opposite
directions, and can reverse method ordering. The stronger empirical claim did
not generalize. Across four large Amazon domains, zero domains passed the
prospective useful-improvement trade-off gate, and zero wrapper confidence
intervals were strictly positive. This is defensible appendix or evaluation-
audit material, not the main claim of a Tier-A paper.

### RQ2

The representation premise was observable: semantic histories had more lag
predictability than collaborative residuals. The proposed 256-parameter
semantic FIR did not convert that signal into retrieval gains. On 11,078 and
11,150 strict-cold test targets, respectively, semantic FIR selected the exact
identity operator and produced zero full-catalog NDCG@10 gain in both domains.
Musical Instruments had a tiny early-fusion within-cold gain, but no full-
catalog cold gain; every active Industrial & Scientific arm selected identity.

This falsifies this selective-FIR construction. It does not prove that all
semantic temporal modeling is useless; it exposes a full-catalog retrieval
floor that a minor FIR variant is unlikely to solve.

### RQ3

Anchoring was necessary for identifiability, blockwise transport was feasible,
and transport mass contained an error signal. Alternating learned-cost CR-UOT
did not translate those properties into better maps. It was 8.01% worse than
fixed UOT under unmatched mass and 138.03% worse than ridge under semantic
shift. Its corrupted-anchor point estimate was promising, but downstream
NRMSE uncertainty crossed zero. The current mapper should not be tuned or
promoted to natural data.

### RQ4

The synthetic retained-mass clue did not survive the natural-data K0 screen.
On Musical Instruments, retained mass had AUROC 0.5072 and Spearman rho 0.0175;
on Industrial & Scientific it had AUROC 0.4861 and rho -0.0103. It did not beat
the strongest ordinary uncertainty baseline in either domain. Both domains
passed landmark stability, placebo invariance, runtime, memory, and every
artifact-integrity gate, so instability or resource failure cannot explain the
null. Fixed-UOT mass should not be tuned or promoted to a temporal router.

The runner and independent deep verifier exited zero with empty stderr and
asynchronous-error ledgers. The missing commit marker resulted solely from a
post-verification `\` versus `/` relative-path comparison. The exact status is
"independently verified, scientifically valid negative K0; control-plane
uncommitted." No outcome rerun was made.

## Scientific classification

- **Good/paper-ready:** no.
- **Needs more work in the same direction:** no.
- **New direction:** yes, for all four main claims.
- **Reusable evidence:** the RQ1 offset theorem/diagnostic, the RQ2 retrieval-
  floor falsification, the RQ3 anchor diagnostic, and the RQ4 falsification of
  retained mass as a natural-data reliability score.

The negative verdict is high confidence because the failures are large or
exact, occur at prospective kill gates, and survived independent reconstruction
of hashes, splits, event identities, masks, ranks, metrics, and adjudication.

## Best surviving research questions

The ranked post-screen agenda is in
`experiments/TIER_A_COLDSTART_RESEARCH_VERDICT_2026-08-05.md`.

1. Main program: cold-start rank-equivalence and reachability auditing under
   global time. This builds on the real RQ1 theorem and the RQ2 retrieval-floor
   evidence; it is an evaluation/measurement contribution, not the failed
   wrapper.
2. One bounded algorithm screen: identify the statistically recoverable shared
   semantic/collaborative subspace and reconstruct only those directions for a
   zero-interaction item. The contribution must be an estimability certificate,
   not another generic alignment or gate.
3. Conditional systems module: semantic cold-candidate injection with an
   explicit reachability versus warm-displacement certificate.
4. Deferred: anchor corruption validation and repair.

The SMAR/support-mass direction is closed. None of the remaining algorithmic
questions should be called novel or publishable until its focused literature
audit and prospective screen pass.

## Artifact index

- Frozen master protocol: `experiments/TIER_A_DECISION_PROTOCOL_2026-08-05.json`
- Original literature and research agenda:
  `TIER_A_COLDSTART_RESEARCH_AGENDA_2026-08-05.md`
- RQ1 final audit:
  `experiments/rq1_multidomain_offset/RQ1_MULTIDOMAIN_OFFSET_AUDIT_REPORT_2026-08-05.md`
- RQ2 decision report:
  `experiments/rq2_selective_fir/RESULTS_AND_DECISION.md`
- RQ2 independent reconstruction audit:
  `experiments/rq2_selective_fir/INDEPENDENT_AUDIT.md`
- RQ2 authoritative aggregate result SHA-256:
  `d24c5f19dbad5b567e38a31d1f9a2ddae9cdc27efcd74e954521c1ef10be032d`
- RQ3 independent audit:
  `experiments/rq3_anchored_cruot/INDEPENDENT_AUDIT.md`
- RQ4 result and decision:
  `experiments/rq4_support_mass_router/RESULTS_AND_DECISION.md`
- RQ4 Windows forensic audit:
  `experiments/rq4_support_mass_router/POST_RUN_FORENSIC_AUDIT_2026-08-05.md`
- Current ranked research verdict:
  `experiments/TIER_A_COLDSTART_RESEARCH_VERDICT_2026-08-05.md`

The temporary pause used to serialize the shared GPU was removed after RQ2
exited and released `experiments/GPU_EXPERIMENT.lock`.
