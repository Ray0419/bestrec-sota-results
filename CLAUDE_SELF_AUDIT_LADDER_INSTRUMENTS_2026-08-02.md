# Claude — turning the ladder's audit instruments on our own campaigns

**STATUS: advisory same-team red-team evidence. Creates no independent confirmation.**
Date: 2026-08-02. Reviewed `codex/bestrec-sota-results` @ `1f76214a`. **No run launched; no artifact
modified; no sealed endpoint read.**

```text
WORKSTREAM:        apply the three checks developed on the external ladder to OUR campaigns
OBJECTIVE:         do our own FIR contrasts survive the audits that caught problems elsewhere?
EVIDENCE QUESTION: equal exposure? recorded hardware? backend sensitivity?
FILES I MAY EDIT:  this memo; a Claude section in HANDOFF_CODEX.md
FILES I WILL NOT EDIT: PAPER_REVIEW_AUDIT.md, manuscript, TeX, cover letter, preregs,
                   adjudicators, graph, tables, manifest, results_*.json, checklist, experiments/**
EXPECTED OUTPUT:   pass/fail per check + one transport trap preempted
STOP CONDITION:    memo committed and pushed
```

Three ticks of auditing an external experiment produced three reusable checks. Fair auditing means
pointing them at our own work, and reporting the result whichever way it falls.

---

## 1. Equal training exposure — **our campaign PASSES; the ladder failed**

Read from the committed `FIRCTRL` result JSONs (training files only, `.finaleval`/`.started`
excluded):

| arm | runs | validation epochs completed |
|---|---:|---|
| identity | 8 | **{20}** |
| fixed_ma | 8 | **{20}** |
| fixed_hp | 8 | **{20}** |
| nonlinear | 8 | **{20}** |
| learned | 8 | **{20}** |
| shared | 8 | **{20}** |

**All 48 runs completed exactly 20 epochs.** Our campaign uses a **fixed budget**, not
early-stopping-with-patience, so every arm receives identical exposure by construction — where the
external ladder's arms diverged by **22%–45%**.

Combined with the convergence measurement I recorded on 2026-08-01 (final/best **0.9995–0.9999** for
every arm; uniform 1–2/8 seeds still rising), **both conditions hold for our internal contrasts:
equal epochs and approximately equal convergence.** So the phrase the ladder cannot use is
*defensible here* — with the precise wording being **"identical fixed epoch budget with
approximately equal convergence"**, still not the bare forbidden term "equal budget", and still
saying nothing about the external comparators, where A3 found the asymmetry is real and OPEN.

## 2. Hardware provenance — **a minor gap**

No `device` / `gpu` / `cuda` / `hardware` key appears in the `FIRCTRL` result JSONs or their config
blocks. The manuscript states the hardware in prose (a single RTX 5060 Ti, Blackwell sm_120), so
this is not undisclosed — but it is **not machine-checkable per run**, unlike seeds, init hashes and
parameter counts, which are. Cheap to fix going forward; not worth re-running anything over.

## 3. Backend sensitivity — **unmeasured, and a transport trap I am declining**

Last tick I measured a cross-backend noise floor of **0.00176–0.00470** NDCG@10 in the BSARec
harness. Our headline MI effect is **+0.002265**. The tempting inference is that our headline sits
at or below the noise floor.

**I decline that inference, and it is important to say why, because a reviewer may attempt it.**
The two quantities are not commensurable:

| | ladder cross-backend delta | our FIR contrasts |
|---|---|---|
| pairing | independent runs, different machines | **paired on shared per-seed `init_state_sha256`**, adjudicator-enforced |
| what varies | init + data order + kernels + hardware | **only the module** |
| measured sd | 0.00176 – 0.00470 | **≈0.000246** (from `fir_controls` learned−identity, CI half-width 0.000206, n=8) |

Our paired standard deviation is **7×–19× smaller** than the ladder's cross-backend sd, precisely
because shared initialisation removes the dominant variance component. **Comparing our paired effect
to an unpaired cross-backend spread is the same category error I made earlier this cycle when I
applied the 45×–96.8× cross-corpus figure to a within-corpus question, and was corrected. I am not
repeating it.**

**What is genuinely open:** our contrasts have **never been executed on a second compute backend**,
so the backend sensitivity *of the paired contrast* is unmeasured. Pairing removes initialisation
variance; it does not obviously remove kernel and reduction-order differences. That is a real gap,
it is cheap to close (one arm pair, one category, second backend), and it is worth closing
**precisely because the naive transport above is available to a reviewer** — a measured answer is
better than my argument that the transport is invalid.

## 4. Net effect on the claim set

**Nothing changes.** Counted claim boundary unchanged: Musical_Instruments (vs 0.0406) and
Office_Products V3 (vs 0.0271 and 0.0279); **Office V1 VOID forever**; TFV2 outcome-visible, not
confirmatory. No frozen analysis is reopened.

What this adds is one defensible strengthening and one honest gap:

- **Strengthening (Codex may use):** *"All six arms trained under an identical fixed 20-epoch budget
  from a shared per-seed initialisation, and every arm finished within 0.05% of its own best
  validation score, so the comparison is not confounded by differential training exposure or
  differential convergence."* Every number in that sentence is measured and committed.
- **Gap to disclose or close:** no second-backend execution of any counted contrast.

## 5. Standing on the loop

This is the fourth consecutive tick with no Codex commit, no new audit, no checklist movement and no
human answer. My recommendation from three ticks ago stands: **pause or lengthen this loop** until
Codex rules on the accumulated proposals or a human gate is answered. I am not disabling it —
`AUDIT_LOOP_STOP` is the maintainer's, and every remaining blocker is a decision I must not make.

## Limits

Exposure equality is read from `history` lengths in committed result JSONs, which record validation
entries rather than optimizer steps; equal epochs at equal batch size and cohort implies equal
updates, which holds within this campaign but was not separately logged. The paired-sd figure is
back-computed from a published CI rather than from per-seed differences. Both runs of the external
ladder and all of our campaigns are same-investigator; nothing here is independent replication.
