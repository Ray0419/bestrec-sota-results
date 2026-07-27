# Errata and evidence classification — canonical FIR breadth

This file does not modify the frozen decision rule or the mechanically reproduced
`CANON-BREADTH-POS` artifact verdict. It corrects the interpretation and reporting
boundary after the 2026-07-27 paper audit.

1. The frozen wording “Holm-corrected 95% CI” is mathematically imprecise. The
   reported intervals are ordinary paired Student-t 95% confidence intervals.
   Holm adjustment applies to the two primary p-values and pass decisions, not to
   those intervals. The manuscript now says this explicitly and prints adjusted
   p-values.
2. Industrial_and_Scientific and CDs_and_Vinyl were chosen after favorable
   results from the legacy package were known, and the trainer evaluated TEST at
   every epoch. Committing this campaign before its own runs protects its within-
   campaign analysis choices, but it does not create outcome-independent category
   confirmation. The graph and manuscript therefore classify the result as
   outcome-known/test-exposed descriptive robustness of the canonical
   reparameterization.
3. The primary learned arms used `--fir-v3-wd backbone`; the paper no longer says
   those taps were excluded from weight decay. The E-A zero-FIR-weight-decay
   sensitivity detected no difference but is neither an equivalence test nor a
   pathway/mediation result.
4. Registered HR@10 and MRR supportive endpoints are now artifact-bound and
   reported. The broader registered cutoff family was not emitted by the trainer
   and is explicitly not claimed.

The surviving scope is an internal matched-initialization contrast on the exact
fixed categories/splits and configuration. It is not independent confirmation,
population transfer, an external-comparator comparison, or a system-ranking claim.
