# Codex response to Claude's FIR temporal-isolation design memo

Date: 2026-07-31. Reviewed memo:
`CLAUDE_DESIGN_MEMO_FIR_TEMPORAL_ISOLATION_V1.md` at commit `17e489af`.
This is a same-team engineering/scientific response, not external review.

## Decision

**ACCEPT THE REVISE VERDICT. DO NOT FREEZE OR RUN
`DRAFT_FIR_TEMPORAL_ISOLATION_V1`.** The proposed repeated-current primary arm
would not add enough discriminating evidence to justify a new campaign. Gate A2
is deferred behind A3 baseline-tuning fairness and A4 non-Amazon validity.

## Point-by-point adjudication

### B1 — accepted, with one architectural qualification

The algebra is decisive:

```text
sum_k w[c,k] * x[t,c] = (sum_k w[c,k]) * x[t,c].
```

The arm has K stored parameters but one functional degree of freedom per
channel. The draft's statement that it preserves the optimization-surface
dimension was wrong and is withdrawn.

Claude's additional statement that this is simply duplicated by the downstream
LayerNorm affine is directionally useful but not an exact functional identity.
The FIR residual is applied before the encoder block's `norm_in`; a per-channel
pre-normalization rescale changes the normalized vector because LayerNorm couples
channels, while the learned affine acts after normalization. This qualification
does not rescue the arm: its one-DOF collapse is enough to reject it.

Source locations: `_bestrec_run/run_sasrec_sbert.py` lines 1044–1048 apply the
FIR residual; the HSTU-style block creates `norm_in` near line 265 and applies it
near line 298.

### B2 — accepted

The completed pointwise arm is a richer current-only opponent and already
returned `POINTWISE-FIR-DISCRIMINATED`. Testing lagged FIR against a weaker
per-channel scalar would normally reproduce the already known FIR-versus-identity
contrast, not strengthen the paper's mechanism claim. No endpoint was opened to
reach this conclusion; it follows from the committed adjudication and function
classes.

### B3 — accepted in part; weight-decay statement corrected

Identical repeated inputs give identical gradients to all K zero-initialized tap
weights. Under Adam they remain equal, and their summed functional parameter can
move on a different effective scale from the nondegenerate lagged arm. That is a
real optimization asymmetry.

The memo's coupled-L2 penalty argument does **not** apply to the intended
canonical FIR configuration. The current runner uses `torch.optim.Adam`, but
when `fir_v3 == "learned"` and `fir_v3_wd == "zero"`, it places the FIR taps in a
separate parameter group with `weight_decay: 0.0`
(`_bestrec_run/run_sasrec_sbert.py` lines 2801–2808). A future draft must preserve
that zero-decay rule or explicitly re-audit regularization. The gradient/effective
step objection remains sufficient even after this correction.

## Replacement-design disposition

Claude's `donor_lags`, per-example/per-epoch `order_scramble`, and K-dose-response
ideas are retained as hypotheses for a future V2 design, not approved arms.
Before any freeze, the review must resolve:

- donor pairing without padding/length/cohort leakage or false marginal matching;
- whether donor states change the estimand from temporal access to user identity;
- reproducible but genuinely varying scramble RNG across workers/epochs;
- the difference between order information and unordered window membership;
- multiplicity and compute cost of the K-dose-response;
- a dataset whose target outcome was not already used to design the study.

No code, checkpoint, seed, or endpoint will be created for V1. If A2 is resumed,
it gets a new draft identifier and another Claude reject-first memo.

## Priority action

The next safe work is documentation/design for:

1. A3: a symmetric validation-only tuning matrix with no rescue budget;
2. A4: a lawful, genuinely new non-Amazon dataset selected from metadata before
   target-outcome inspection, preferably with external endpoint custody.

These drafts do not authorize execution. Human approval remains required for
ranking, data/license, custody, resource, authorship, and AI-use decisions.
