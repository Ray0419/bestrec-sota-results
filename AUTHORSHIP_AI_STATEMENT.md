# Authorship and AI-use statement

**For: "Coverage Was Never the Binding Constraint: Break-Even Arithmetic and a Degree-Indexed
Screen for Cold-Start Retrieval" — ACM RecSys short-paper submission.**

Two versions: the short form for the manuscript (ACM policy requires disclosure but not a full
appendix), and the long form for a transparency appendix / supplementary material, which this
paper's methods make advisable. Drafted 2026-08-19; the human author must review, edit the
bracketed placeholders, and confirm the factual accuracy of every sentence before submission.

---

## Short form (manuscript, end of paper before references)

> **Authorship and AI disclosure.** The sole human author is [FULL NAME], [AFFILIATION], who
> directed this research, made all decisions at the pre-registration checkpoints, and takes full
> responsibility for the correctness of every claim, number, and citation. In accordance with ACM
> policy, no generative-AI system is listed as an author. This work made substantial use of a
> generative-AI research assistant (Claude, Anthropic): it contributed to hypothesis generation,
> prior-art searches, experiment code, experiment execution and monitoring, statistical analysis,
> and manuscript drafting, in an interactive loop in which the human author set direction, approved
> or redirected each stage, and adjudicated all pre-registered decision rules. All pre-registration
> documents, analysis scripts, per-seed outputs, and the session-level research log are included in
> the reproducibility package so that the division of labour is inspectable rather than asserted.

## Long form (transparency appendix / supplementary)

> **A. Roles.**
> *Human author ([FULL NAME]):* research direction and scope decisions; selection among competing
> research directions at each decision point; approval of every pre-registration before execution;
> the venue, framing, and title decisions; final verification of the manuscript; accountability for
> the whole work under the ACM authorship policy.
> *AI assistant (Claude, Anthropic; agentic sessions in Claude Code):* literature and novelty
> searches (including parallel sub-agent searches whose verbatim verdicts are in the research log);
> derivation drafts; design and implementation of the measurement instruments
> (`poc_pool_conversion.py`, `poc_coverage_trade.py`) and frozen analyzers; scheduling and
> execution of training and evaluation runs; drafting of the pre-registration documents and of the
> manuscript text; maintenance of the corrections log.
>
> **B. Safeguards against AI-specific failure modes.** (1) Every confirmatory claim was
> pre-registered with frozen falsification rules and frozen analyzers *before* the corresponding
> runs; three frozen predictions failed (C2 in part, E2's P1, E4) and are reported as failures in
> the abstract and corrections log rather than repaired. (2) Prior-art boundaries were established
> by targeted searches whose negative space is documented (claims-and-non-claims box, §5); where a
> search could not verify a source (unparseable PDFs), that is recorded rather than assumed.
> (3) All numbers in the paper trace to on-disk per-seed JSON artifacts regenerable by the frozen
> analyzers; no number in the text was produced by a language model without a script behind it.
> (4) AI-written prose was constrained by the numbers-verbatim rule: assembly steps were forbidden
> from altering any figure, and discrepancies found during assembly are listed in the research log.
>
> **C. Known residual risks the reader should weigh.** The searches that ground the novelty
> boundaries were AI-conducted and time-boxed; a human literature check of the six boundary
> clusters in §5 [HAS / HAS NOT] been completed. The human author [HAS / HAS NOT] independently
> re-run the frozen analyzers end-to-end. These boxes must be resolved truthfully before
> submission; the statement must not ship with them unresolved.
>
> **D. What the AI did not do.** It did not choose the research question's final framing against
> the author's judgement, did not approve its own pre-registrations, and did not decide what to do
> when frozen predictions failed — the frozen consequences were written in advance and executing
> them was a mechanical act. It is not an author: it cannot take responsibility, and under ACM
> policy responsibility is constitutive of authorship.

---

## Submission-blocking checklist (human-only, from the program log)

- [ ] Fill [FULL NAME] / [AFFILIATION]; decide whether any other person merits authorship or
      acknowledgement (nobody else appears in this program's log).
- [ ] Resolve the two [HAS / HAS NOT] boxes in C **truthfully** — doing the human re-verification
      is strongly advised, not just marking it.
- [ ] Check RecSys 2027 CFP for its current AI-disclosure format (checkbox vs free text) and adapt
      the short form; ACM's generative-AI policy wording should be re-checked at submission time.
- [ ] Gate-A0-style ranking verification (carried over from the host program's stop-condition
      list): human spot-check of a handful of per-event ranks against raw scores.
- [ ] Reproducibility package: preregs, analyzers, per-seed JSONs, corrections log, and the
      research log export.
