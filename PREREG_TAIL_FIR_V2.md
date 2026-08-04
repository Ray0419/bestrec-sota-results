# PREREG_TAIL_FIR_V2 — pre-declared independent-arm rerun campaign (tail estimand + FIR attribution)

**Frozen 2026-07-20 (Australia/Sydney), before any campaign run starts.** Maintainer directive
2026-07-20 ("fold all 5") authorizes the audit P0 reruns; this file freezes the design. It is
committed and OpenTimestamps-stamped (`PREREG_TAIL_FIR_V2.md.ots`) before the first run
launches — the first campaign with an **independent external timestamp** in this project.

## Why this campaign exists (what it repairs)

Audits 2026-07-19 19:56 → 2026-07-20 00:01 confirmed two design defects in the original
tail and FIR campaigns:

1. **Same-numbered seeds never created paired arms** (treatment modules consume RNG before
   the shared backbone), so all paired inference was withdrawn.
2. **The nominal tail tercile is defective**: it mixes zero-train-exposure targets with
   low-frequency targets and splits frequency ties by item-ID order, and the original runs
   retained no per-row outputs to reanalyze.

This campaign adopts **option (b)** of the 19:56 audit: arms are **pre-specified as
independent** (no pairing claim of any kind), powered by more seeds, analyzed with
independent-arm Welch inference, and every run automatically emits a per-user sidecar
(`<out>.users.jsonl.gz`: user_id, target_item_id, rank0, ndcg10, hr10, rr, pop_bucket)
enabling tie-safe, exposure-separated, row-level reanalysis by anyone.

## Design (frozen)

- **Arms and seeds (8 per arm, never inspected before this freeze):**
  | campaign | arm | seeds | epochs |
  |---|---|---|---|
  | MI tail | text (V2 stack) | 20260801–20260808 | 20 |
  | MI tail | id-only | 20260811–20260818 | 20 |
  | IS FIR | filter (K=8) | 20260821–20260828 | 20 |
  | IS FIR | no-filter | 20260831–20260838 | 20 |
  | CDs FIR | filter (K=8) | 20260861–20260868 | 20 |
  | CDs FIR | no-filter | 20260871–20260878 | 20 |
  | VG tail | text (V2 stack) | 20260841–20260848 | 40 |
  | VG tail | id-only | 20260851–20260858 | 40 |

- **Configurations:** mechanically re-emitted from the original runs' embedded `config`
  dicts (no hand transcription); the frozen command list is
  `_bestrec_run/tfv2_commands.txt`, sha256
  `525496d4bf608f4f62837b729fb6867b61d521df2cee80cf413a8f0c39de1a1b` (64 commands).
  A 1-epoch smoke run validated exact template-side config parity (every template key
  equal except seed/epochs/out/eval_every) and sidecar emission (57,439 rows on MI).
  Driver flags added after the original campaigns ride at their inert defaults; each run
  JSON embeds its full realized config for audit.
- **Execution:** strictly sequential (one GPU job at a time), in table order (MI → IS →
  CDs → VG), via `_bestrec_run/run_tfv2_campaign.sh`; a run whose output JSON already
  exists is skipped (resumability), and existing `results_*.json` files are never
  overwritten.
- **Cohort rules (frozen; computed from the released split CSVs, item-ID-independent):**
  - **Zero-exposure bin:** test targets whose item has train frequency 0. Reported
    separately; never merged into any tail statistic.
  - **Positive-frequency tail (primary):** order items by train frequency ascending;
    let N⁺ = number of positive-frequency items; include whole frequency groups from the
    lowest frequency upward until adding the next whole group would move the cumulative
    item count further from N⁺/3 than stopping (deterministic nearest-to-third whole-group
    rule; no tie is ever split).
  - **Sensitivity strata (secondary):** (a) exclude the boundary frequency group entirely;
    (b) absolute band: train frequency in [1, 6].
- **Endpoints and decision rules (frozen):**
  - **E1 (primary):** MI positive-frequency-tail NDCG@10, text vs id, independent-arm
    Welch; success = two-sided 95% CI excludes 0 in the positive direction.
  - **E2 (primary):** IS overall NDCG@10, filter vs no-filter, Welch; CI excludes 0, positive.
  - **E3 (primary):** CDs overall NDCG@10, filter vs no-filter, Welch; CI excludes 0, positive.
  - **Multiplicity:** Holm across {E1, E2, E3}, family α = 0.05.
  - **Secondary/descriptive (no success gates):** MI zero-exposure-bin Δ; MI tail HR@10;
    the two sensitivity strata; VG tail Δ (no equivalence claim of any kind — no margin is
    pre-specified); four-arm MI−VG Welch–Satterthwaite contrast; FIR per-category tail Δ.
  - The FIR endpoints estimate the **FIR-plus-initialization/optimizer package** effect
    under independent arms (the known singular-initialization coupling is unchanged and
    disclosed; component-level attribution is out of scope for this campaign).
- **Adjudication:** `_bestrec_run/adjudicate_tfv2.py` (to be committed before any result
  is inspected; it consumes only the sidecars + split CSVs and prints per-endpoint
  verdicts). No number from this campaign enters either paper until adjudication runs and
  its output is committed. Failure honesty: a failed endpoint is reported as failed; the
  existing narrowed claims stand and can only narrow further.
- **Claim-boundary interaction:** this campaign ADDS evidence; it changes no frozen prior
  wording. If E1–E3 pass, the papers may state the corresponding independent-arm results
  under this prereg's wording; nothing here authorizes SOTA/comparator/paired language.

## Status log

- 2026-07-20: frozen; smoke parity validated; OTS stamp requested; campaign launched
  (sequential background queue).

## ERRATUM E1 (2026-07-20, before any IS/CDs run existed and before any adjudication)

The mechanical flag emitter had a bug: the FIRB template configs carry
`zfusion_sweep: ""` (an inert empty-string default), and emitting `--zfusion-sweep`
with an empty value made argparse reject all 32 IS/CDs commands instantly (every one
failed at argument parsing; zero training steps ran). The MI and VG arms (32 runs)
completed normally under the original frozen command list.

Repair: the generator now skips empty-string/empty-list/empty-dict values (argparse
defaults). The regenerated `_bestrec_run/tfv2_commands.txt` has sha256
`75d045a81eb21e1ed889008fb0bbb45fc0dba4e94cd3aabb84a637a944891f0b`; the 32 MI/VG lines
are byte-identical to the original frozen list (verified programmatically) — only the
32 IS/CDs lines changed (the spurious flag removed). Decision rules, endpoints, seeds,
and analysis are UNCHANGED.

Exposure disclosure (honesty): while diagnosing the queue exit, the tail of run 1's
console log (results_TFV2_MI_text_seed20260801: best-epoch summary block) was read
before this erratum. No other run output was inspected; no rule depends on it; the
adjudicator (`adjudicate_tfv2.py`) was committed before any further inspection and
remains fully mechanical.

- 2026-07-20: E1 recorded; amended file re-stamped (`PREREG_TAIL_FIR_V2.md.ots`
  regenerated; the pre-E1 proof is preserved in git history); IS/CDs queue relaunched.

---

## ERRATUM E2 (2026-07-21; chronology of the external timestamps — conspicuous correction)

The header above states this pre-registration was "committed and
OpenTimestamps-stamped before the first run" and calls it the project's first
independent external timestamp. After independent verification of the completed
Bitcoin attestations (external audit 2026-07-20 22:57 and prior), that claim is
**corrected as follows and must not be quoted without this erratum**:

- The pre-registration and command file were Git-committed at **01:26:34 AEST,
  2026-07-20**, and OTS calendar proofs were requested then.
- The first campaign result file was complete at **≈ 01:36:02 AEST**.
- The **earliest independently verifiable Bitcoin attestation is block height
  958749, timestamped 01:48:23 AEST — after the first result** (the amended
  post-erratum proof anchors ≈ 06:11:59 AEST and matches the CRLF worktree bytes,
  not the LF Git blob).
- OpenTimestamps proves existence before an attested time; it does not backdate
  the Bitcoin evidence to the calendar request. The pre-launch freeze therefore
  rests on Git history alone, which is not independent evidence.
- Consequently the campaign is labeled **outcome-visible, not confirmatory**
  (manuscript §5.3, disclosure (vii)), and the "first independent external
  timestamp" characterization is withdrawn.

The committed `.ots` proofs bind the pre-E2 revisions of this file (their exact
digests are recorded in manuscript disclosure (vii)); this appended erratum
intentionally changes the file's current bytes and is therefore outside those
proofs — the frozen pre-E2 text is preserved above, unedited, for provenance.
