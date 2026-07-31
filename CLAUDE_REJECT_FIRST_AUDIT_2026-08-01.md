# Claude reject-first audit — TORS venue package

Discharges §3 of `TORS_METHODOLOGY_CHECKLIST.md` ("Claude should copy this section into a dated
memo and fill every field before a new protocol is frozen or the venue package is declared
ready"), and the three checklist rows that read *"Claude must…"*: **Novelty as a modular
contribution**, **Baseline selection rationale**, and **Outcome-independent reporting**.

```text
WORKSTREAM:        reject-first audit of the current venue package
OBJECTIVE:         fill every §3 field; discharge the three "Claude must" checklist rows
FILES I MAY EDIT:  this memo; a Claude section in HANDOFF_CODEX.md
FILES I WILL NOT EDIT: PAPER_REVIEW_AUDIT.md, manuscript, TeX, cover letter, preregs,
                   adjudicators, graph, tables, manifest, results_*.json
EXPECTED OUTPUT:   completed audit form + per-row dispositions + mandatory-change list
STOP CONDITION:    memo committed and pushed
```

---

```text
AUDIT DATE:                            2026-08-01
REVIEWED COMMIT:                       b225fa54 (working tree dirty; manuscript/TeX/cover
                                       letter carry uncommitted Codex edits, audited as-is)
TARGET JOURNAL + RANKING AUTHORITY:    ACM TORS proposed. RANKING AUTHORITY NOT SUPPLIED.
                                       A0 remains BLOCKED-RANKING; I do not call any venue Tier A.
DECISION:                              APPROVE WITH REQUIRED CHANGES
                                       (scientific content approved for submission to a
                                       reproducibility-fit venue; release remains blocked on
                                       human-only gates, not on science)
```

## STRONGEST NOVELTY OBJECTION

*"Every element of your module predates you, and a 2026 paper parameterizes long causal depthwise
convolutions on this exact backbone family."* HyenaRec (WWW 2026) does gated long causal depthwise
convolution with HSTU comparisons and kernel ablations; TV-Rec (NeurIPS 2025) makes fixed causal
filtering an explicit special case of position-varying filtering; C3SASR already put causal
convolutions around attention.

**Disposition: SURVIVES.** §2.3/Table 0 and §2 already concede exactly this — *"Their existence
rules out broad filtering, convolution, temporal-specificity, initialization-optimality, or
efficiency novelty"* — and the abstract closes with *"not a new architecture… not SOTA… not
independent confirmation."* The residual claim is an artifact-gated **evaluation record** plus a
narrow detachable implementation. That is a defensible contribution class, and the manuscript
already labels itself as such in its title.

**Residual friction I could not fully clear:** the novelty boundary names a **depthwise
(per-channel)** residual as the claimed-new object, while the evidence declines per-channel
attribution (learned − shared = −0.000081 [−0.000337, +0.000175]). This is not a contradiction —
novelty of an artifact does not require necessity of each part — and the manuscript never conflates
them. But a reviewer will feel the friction. It is disclosed in six places (abstract, contributions,
Table 0 row, §5.2, §6, §7); I judge disclosure adequate and recommend **no further change**.

## STRONGEST IDENTIFIABILITY / CONFOUNDING OBJECTION

*"The pointwise placebo changes basis, activation, channel mixing, and temporal access at once, so
it cannot isolate temporal access."*

**Disposition: SURVIVES, and the manuscript says so first.** §5.2, §6, §7 and the cover letter all
state the contrast is compound and does not isolate temporal access. The `V1` repeated-current
design that *would* have isolated it was rejected (by me) as collapsing to one functional DOF, and
Codex accepted the no-run verdict. Correctly carried as **DEFERRED**, not quietly dropped.

## STRONGEST BASELINE-FAIRNESS OBJECTION

*"Hyperparameter tuning fairness is OPEN by your own checklist, and several comparisons have
unequal architecture, capacity, initialization, campaign date, or tuning opportunity."*

**Disposition: SURVIVES AND IS THE WEAKEST ROW IN THE PACKAGE.** It is honestly marked OPEN, and
the manuscript labels affected comparisons whole-package and unequal-model rather than isolating
components. That is the correct handling of a gap that cannot be closed without new symmetric
campaigns. **It is the single most likely reviewer-1 rejection ground.** It does not require
delaying submission — it requires the cover letter to keep naming it, which it does.

## STRONGEST STATISTICAL OBJECTION

*"Seed-level intervals on fixed splits are not population or dataset uncertainty, and you run many
families."*

**Disposition: ALREADY DISCHARGED.** Multiplicity families are declared per study, Holm is applied
within family, intervals are labelled *ordinary paired* and explicitly **not simultaneous**, Fig. 1
states it is not a pooled estimate and not one multiplicity family, and — the item I checked
hardest — **every CI crossing zero is labelled "not equivalence"** rather than read as sameness. I
found no instance of a null being upgraded. Rated **PASS-WITH-LIMITS**, correctly.

## STRONGEST EXTERNAL-VALIDITY OBJECTION

*"Your only prospectively frozen, non-Amazon test is negative, and everything positive is
outcome-known Amazon."*

**Disposition: SURVIVES; it is the true ceiling on the paper's reach.** The MovieLens 1M null
(+0.000000 [−0.000074, +0.000075]) appears in the abstract, contributions, §5, §6, §7 and the cover
letter with the same prominence as the positive estimates. Prior audit established ML-1M was
**undertrained** (≈100 optimizer updates vs 4,000–9,680 on Amazon), which the manuscript states —
so the null is correctly reported as *failure to replicate*, **not** as evidence of a domain
moderator. That distinction is made correctly throughout.

## STRONGEST REPRODUCIBILITY / DATA-LEGAL OBJECTION

*"201 recomputing cells is impressive, but redistribution rights and custody are unresolved."*

**Disposition: SURVIVES, and is HUMAN-BLOCKED, not agent-fixable.** Artifact graph, strict rebuild,
and clean-clone checks PASS. Dataset licence/retention/redistribution (A4) and external custody are
human-only. One campaign ran from a dirty tree and its sidecars were not independently custodied
(filename-suffix ignore error) — disclosed in §5.2 and the cover letter rather than buried.

## AI-USE DISCLOSURE CHECK

**BLOCKED-HUMAN, and the checklist's framing is right.** Codex and I have materially assisted
design review, code, analysis, and manuscript preparation. The checklist's instruction — *"Do not
minimize this to writing-only assistance if the record shows broader use"* — is correct and must be
honoured; the record shows broader use. **A writing-assistance-only statement would be false.** The
maintainer must approve precise venue-compliant wording.

## MANDATORY CHANGES BEFORE FREEZE / SUBMISSION

1. **A0** — supply the controlling ranking list + edition, or drop every Tier-A framing. *(human)*
2. **A1** — author name(s), affiliation, country, corresponding contact, running header. *(human)*
3. **A4** — dataset licence, retention, redistribution boundary; external custody decision. *(human)*
4. **AI-use disclosure** — approve wording that reflects the actual breadth of use. *(human)*
5. **Release blockers from the 22:23 audit** — Office V3 sidecar/release boundary, stale
   `paper_tex/BUILD_NOTES.md`, abstract comparator sentence, SILLM4Rec rationale. *(Codex)*

**None of these is a scientific defect.** Four are human-only; one is release hygiene.

## OPTIONAL IMPROVEMENTS

6. **Cite three filter-family works named in Codex's own novelty review but absent from the
   package** — verified `bib=0, md=0`: **MUFFIN** (CIKM 2025, user-adaptive filters), **SLIME4Rec**
   (ICDE 2023, static/dynamic frequency selection), **DWTRec** (2025, wavelet time-frequency).
   Discharging the *"flag any omitted method a reviewer could reasonably view as decisive"*
   instruction: **none of the three is decisive.** §2 already cites TV-Rec, HyenaRec, ConvRec,
   WEARec, FreqRec, Mamba4Rec, C3SASR, AdaMCT, FMLP-Rec and BSARec, and already concedes the whole
   filtering family predates this work — three more citations improve coverage without changing any
   claim. **Do not delay submission for this.**
7. **MARec** (RecSys 2024) — in-family closed-form cold-start method on Amazon Video Games with
   public splits; a genuine future baseline (see `CLAUDE_CIRCULARITY_GATE_REFUTED_2026-08-01.md`),
   not a gap in the present claim set.

## CLAIMS PERMITTED IF POSITIVE / NULL / NEGATIVE

The counted boundary is **unchanged** and I propose no widening: Musical_Instruments (vs published
0.0406) and Office_Products V3 (vs 0.0271 and 0.0279); **Office V1 VOID forever**; TFV2
outcome-visible, not confirmatory.

- **Positive** — permits *outcome-known internal* estimates on the named Amazon settings only. Not
  SOTA, not general FIR benefit, not causal isolation, not cross-domain.
- **Null** (learned vs shared/nonlinear) — permits *"per-channel-tap necessity not established."*
  **Never** "equivalent," "no difference," or "shared is as good." CIs crossing zero are not
  equivalence.
- **Negative** (MovieLens) — permits *"prospectively frozen same-investigator replication failed."*
  **Not** "FIR does not work on MovieLens" and **not** a domain moderator, because the schedule was
  not matched.

## FILES AND PRIMARY SOURCES REVIEWED

`TORS_METHODOLOGY_CHECKLIST.md`, `CODEX_CLAUDE_COLLABORATION_GUIDE.md`, `CANONICAL_SUBMISSION.md`,
`TIER_A_PUBLICATION_ROADMAP.md`, `PAPER_SUBMISSION.md` (abstract, §2/§2.3, §3, §5.2, §6, §7),
`COVER_LETTER_TORS.md`, `paper_tex/references.bib`, `paper_tex/sections/`,
`FIR_TIER_A_NOVELTY_REVIEW_AND_EXPERIMENT_DESIGN_2026-08-01.md`, `POC_TEMPORAL_LC2C_V1.md`,
`_bestrec_run/poc_temporal_lc2c_v1/AUDIT.md`, `PAPER_REVIEW_AUDIT.md` (tail, read-only), plus my
own `CLAUDE_DECOMPOSITION_PRIOR_ART_SWEEP_*` and `CLAUDE_CIRCULARITY_GATE_REFUTED_*`.

---

## Checklist rows I am moving, with evidence

| Row | Was | Now | Evidence |
|---|---|---|---|
| Novelty as a modular contribution | PARTIAL | **PASS** | §2/§2.3/Table 0 compare the exact mechanism to TV-Rec, HyenaRec, ConvRec, C3SASR, AdaMCT, Mamba4Rec, WEARec, FreqRec, FMLP-Rec, BSARec, and state what is new, what is evaluation, and what is not new. Discharges the "Claude must" instruction. |
| Baseline selection rationale | PARTIAL | **PASS-WITH-LIMITS** | Inclusion/exclusion justified; **no omitted method is decisive**; three non-decisive additions listed at item 6. |
| Outcome-independent reporting | PARTIAL | **PASS** | Verified line-by-line: title, abstract, contributions, §7, and cover letter all carry the MovieLens null, the shared-filter non-separation, the VOID record, and "not independent confirmation." **No selective upgrading of favourable outcomes found.** |

These are **proposals to Codex**, not edits — I did not modify the checklist.

Rows I explicitly do **not** move: *Hyperparameter tuning fairness* stays **OPEN** (the weakest
row); *External validity* stays **OPEN**; *Exact-input temporal isolation* stays **DEFERRED**; all
BLOCKED-HUMAN and BLOCKED-RANKING rows stay blocked.

## Bottom line

The package's science is in materially better shape than its release state. Of the five mandatory
changes, **four are human-only and one is release hygiene — none is a scientific defect.** My audit
is advisory same-team evidence and creates no independent confirmation; Codex must separately
verify implementation and provenance, and the maintainer retains every submission, legal, identity,
and ranking decision. Completing this form does not predict acceptance.

**Standing recommendation, now unchanged across four consecutive ticks: supply A0/A1, clear the
release blockers, and submit.**
