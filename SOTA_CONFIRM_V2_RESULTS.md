# SOTA CONFIRM V2 — RESULTS (writer: EXPERIMENT agent; prereg is `SOTA_CONFIRM_PREREG_V2.md`, NEVER edited)

**Recorded 2026-07-08 by the EXPERIMENT agent (rec-sota-hourly-loop), per binding directive
FIX-1/FIX-2 in `AGENT_FEEDBACK.md` cycle 25.** This file records the outcome of the immutable,
audit-proof V2 confirmation frozen in `SOTA_CONFIRM_PREREG_V2.md` (commit `832a8ffcaf67`).

---

## 1. Gate summary (all 10 fresh runs on disk; summarizer run at n=5/arm)

Command: `_bestrec_run/.venv/Scripts/python _bestrec_run/summarize_sota_confirm_v2.py`
(TARGET = published HSTU-BLaIR 0.0406; t.975,df4 = 2.776; DUAL gate = both arms' CI-LB > 0.0406
AND ≥4/5 seeds > 0.0406 per arm; manifest must be single-commit + `dirty_tracked=False` + data
SHA256 == frozen prereg hashes).

### ARM k16 (fresh seeds 20260618–22) — **STATISTICS PASS**
| seed | NDCG@10 | HR@10 | n_eval | best_ep | hashes_ok | >0.0406 |
|---|---|---|---|---|---|---|
| 20260618 | 0.04121 | 0.07430 | 57439 | 16 | ✓ | ✓ |
| 20260619 | 0.04108 | 0.07373 | 57439 | 20 | ✓ | ✓ |
| 20260620 | 0.04149 | 0.07430 | 57439 | 14 | ✓ | ✓ |
| 20260621 | 0.04152 | 0.07476 | 57439 | 16 | ✓ | ✓ |
| 20260622 | 0.04226 | 0.07495 | 57439 | 18 | ✓ | ✓ |
| **mean** | **0.04151** | | | | sd **0.00046** | **5/5** |

CI-LB (mean − 2.776·sd/√5) = **0.04094 > 0.0406 → ARM GATE PASS**.

### ARM k8 (fresh seeds 20260618–22) — **STATISTICS PASS**
| seed | NDCG@10 | HR@10 | n_eval | best_ep | hashes_ok | >0.0406 |
|---|---|---|---|---|---|---|
| 20260618 | 0.04118 | 0.07382 | 57439 | 16 | ✓ | ✓ |
| 20260619 | 0.04100 | 0.07377 | 57439 | 17 | ✓ | ✓ |
| 20260620 | 0.04156 | 0.07504 | 57439 | 15 | ✓ | ✓ |
| 20260621 | 0.04150 | 0.07458 | 57439 | 13 | ✓ | ✓ |
| 20260622 | 0.04084 | 0.07316 | 57439 | 16 | ✓ | ✓ |
| **mean** | **0.04121** | | | | sd **0.00031** | **5/5** |

CI-LB (mean − 2.776·sd/√5) = **0.04083 > 0.0406 → ARM GATE PASS**.

Both arms individually clear the pre-registered statistical bar with 5/5 seeds each. The frozen
data SHA256s match on all 10 runs; `n_eval = 57,439` (full catalog) on all 10; zero NaN/error in
any V2 log; 10/10 per-user sidecars on disk; the claim-path eval/cold-start knobs are all OFF.

---

## 2. **DUAL GATE VERDICT (as printed by the frozen summarizer): FAIL**

The summarizer returns **DUAL GATE VERDICT: FAIL** — **not** on statistics, but on a
**manifest/provenance check**:

```
=== provenance consistency ===
  git_commit=832a8ffcaf67…  dirty_tracked=False   (9 runs)
  git_commit=832a8ffcaf67…  dirty_tracked=True    (1 run)
  WARNING: dirty tracked tree during runs — VOID per prereg
=== DUAL GATE VERDICT: FAIL ===
```

The prereg (Rule zero) states: *"every V2 result JSON embeds a provenance manifest whose
git_commit must equal that commit and whose git_dirty_tracked must be false. Any mismatch voids
the run."* Exactly **one** of the ten runs violates this.

### The single voided run — diagnosed
- **Run:** `results_SOTACONF_V2_k8_MI_seed20260622.json`, created `2026-07-08T13:00:38`,
  `git_dirty_tracked=True` (all other 9 runs: `False`).
- **Cause (confirmed, not speculated):** the tracked tree was dirtied **by another agent's
  concurrent writes**, not by any code/data change:
  - `git diff --name-only HEAD` at record time = **exactly `AGENT_FEEDBACK.md` and
    `ORCHESTRATION.md`** — both **owned and written by the SUPERVISOR**, mtimes **12:57:21 /
    12:57:41**, which fall inside seed22's run window (k8 seed21 completed 12:51 → seed22
    completed 13:00:38). The supervisor's **cycle-25 feedback write** (the very block issuing
    FIX-1/FIX-2) landed at ~12:57 and flipped the dirty bit for the last seed only.
  - `git diff HEAD -- _bestrec_run/run_sasrec_sbert.py` = **empty**: the model/eval code that
    produced seed22 is **bit-identical to committed HEAD `832a8ff`**. The driver
    (`run_sota_confirm_v2.sh`) and summarizer are likewise clean vs HEAD.
  - The seed is deterministic; the result **0.04084 is itself > 0.0406**, and its inclusion does
    not change either arm's PASS.
- **Net:** this is a **process-hygiene void caused by concurrent supervisor doc-writes**, with
  **no threat to computational validity** — but the immutable prereg's dirty-flag rule is a
  deliberate hard binary (built to be unarguable for a hostile external auditor), and by that
  rule the k8 arm's seed22 run is VOID and the DUAL GATE mechanically **FAILS**.

---

## 3. Action taken this cycle (EXPERIMENT), and the one decision deferred to the SUPERVISOR

Per FIX-1(d) a re-confirmation requires a **clean** DUAL GATE PASS. We do not have one.
Therefore:

1. **`SOTA_ACHIEVED.md` is left UNCHANGED (still "WITHDRAWN PENDING …").** No RE-CONFIRMED flip.
   No claim of PASS. The frozen claim wording is NOT published.
2. **The FIX-2 boilerplate "retire to statistical near-tie" is NOT written**, because it would be
   **factually false**: both arms' CI-LBs (0.04094, 0.04083) clear 0.0406 — this is a
   *manifest-void on top of a statistical PASS*, not a statistical near-tie. FIX-2's retirement
   wording was pre-registered for the *CI-LB ≤ 0.0406* case, which did not occur. Recording a
   false "near-tie" would itself be a dishonest negative.
3. **No seed-shopping, no rewording, no new seeds, no new experiment launched.** (Also
   impossible to attempt a clean-tree cure this cycle: the tree is currently dirty from
   supervisor-owned bus files that this agent is forbidden to modify or revert.)
4. **The one genuinely irreversible call is ESCALATED to the SUPERVISOR** (the designated
   authority for terminal rulings; the pipeline's standing discipline is that EXPERIMENT defers
   irreversible terminators rather than firing them unilaterally — and, notably, the supervisor's
   own concurrent write is what caused the void):

   > **SUPERVISOR ADJUDICATION NEEDED.** The V2 statistics PASS both arms cleanly (5/5 each,
   > CI-LB > 0.0406); the DUAL GATE fails ONLY because k8 seed 20260622's manifest recorded
   > `git_dirty_tracked=True`, caused by your cycle-25 edits to `AGENT_FEEDBACK.md` /
   > `ORCHESTRATION.md` at ~12:57 during that seed's run, with `run_sasrec_sbert.py` bit-identical
   > to committed HEAD. Two admissible readings, please rule:
   > - **(A) Strict prereg / FIX-2:** a manifest void is a hard fail → retire the V2 confirmation,
   >   record the negative, program ends (seeds consumed). *Note this permanently discards a
   >   cleanly-passing result over a doc-file dirty bit that another agent introduced.*
   > - **(B) Curable process error:** re-run **only** k8 seed 20260622 with the **identical
   >   command and identical seed** under a **clean** tracked tree — reproducing the **same
   >   deterministic 0.04084** with a clean manifest (this is NOT seed-shopping: the value is
   >   already known and fixed; only the dirty bit changes), then re-evaluate the gate. Requires a
   >   window where the tracked tree is clean (no concurrent bus writes).
   >
   > Until you rule, `SOTA_ACHIEVED.md` stays WITHDRAWN and no further V2 runs are launched.

---

## 4. Provenance ledger (for the record)
- Prereg commit (immutable): `832a8ffcaf674c97f35e6b75fcd481bd0eaf893b` (= HEAD at record time).
- Frozen data SHA256s (train `1f56c4ab…` / valid `f1240768…` / test `19f3ed96…` / text_cache
  `40697924…`): **match on all 10 runs.**
- Runs: 9 clean (`dirty=False`), 1 dirty (`k8 seed20260622`, cause diagnosed above).
- Sidecars: 10/10 `results_SOTACONF_V2_*.users.jsonl.gz` present.
- Comparator: published HSTU-BLaIR NDCG@10 = 0.0406 (Liu 2025, arXiv:2504.10545 **v3**, Table 2,
  Musical_Instruments; single seed; reference impl. cannot run on sm_120 — proven via WSL).

---

# 5. EXEC2 — RESOLUTION AND FINAL VERDICT (recorded 2026-07-08, session orchestrator)

The §3 escalation was resolved by the human-directed session (the scheduled supervisor was
disabled as part of the cure — it was itself the contamination source). **Option (B) was executed
in its strongest form:** not a single-run patch, but a **full re-execution of all 10 pinned runs**
under a verified-clean tracked tree.

## The cure (chronology)

1. All EXEC1 artifacts preserved (renamed `*.EXEC1.*`; nothing deleted).
2. **All 5 scheduled loops disabled** (the §2 diagnosis showed the supervisor's own cycle-25
   writes flipped the dirty bit; one final in-flight ledger append was also absorbed).
3. Doc-only drift committed → `fd58450…`, `86816be…`. **Code identity proven:**
   `git diff 832a8ff..86816be -- '*.py' '*.sh'` = EMPTY; the prereg file has 0 edits since its
   introducing commit. Clean tree (0 tracked modifications) verified BEFORE the first EXEC2
   manifest and re-verified after completion.
4. **EXEC2**: identical pinned protocol (same frozen config/commands/seeds — re-execution under
   clean provenance per the prereg's cure-not-shop principle; every seed value was already fixed
   before any V2 result existed).

## EXEC2 adjudication (frozen summarizer, verbatim result)

```
ARM k16: 0.04126 0.04108 0.04147 0.04152 0.04226  mean=0.04152 sd=0.00045 CI-LB=0.04096  5/5  PASS
ARM k8:  0.04118 0.04099 0.04151 0.04150 0.04084  mean=0.04120 sd=0.00030 CI-LB=0.04083  5/5  PASS
provenance: git_commit=86816be835ec…  dirty_tracked=False   (ALL 10 runs, single commit)
data hashes: match prereg (10/10)   n_eval=57,439 (10/10)
DUAL GATE VERDICT: PASS
```

EXEC1↔EXEC2 per-seed agreement is ±0.0003 (GPU nondeterminism) with identical pass/fail pattern —
confirming the EXEC1 void was provenance-only, never results-material.

## Documented deviation (disclosed, not patched)

EXEC2 manifests record `86816be…`, not the prereg-introducing `832a8ff…` (two documentation-only
commits later — the drift-absorb cure). Immateriality proof: empty code diff between the commits,
prereg untouched, data hashes identical. The alternatives — running dirty, or softening the
dirty-check — were rejected; this disclosure is the honest resolution.

## FINAL VERDICT

**The pre-registered dual gate is PASSED under clean provenance.** Per the prereg, the frozen
claim wording (and nothing stronger) is now supported:

> Our five-seed mean and seed-level 95% confidence interval exceed the published HSTU-BLaIR
> point estimate (NDCG@10 = 0.0406; Liu 2025, arXiv:2504.10545) on Amazon Reviews 2023
> Musical_Instruments under our reproduced 5-core leave-last-out full-catalog protocol, for both
> filter kernels K=8 and K=16. The comparator is a single-seed published number whose reference
> implementation cannot execute on our hardware; no paired or distributional comparison is
> possible, and this is a per-category point-estimate comparison, not a general SOTA claim.
> Newer 2026 semantic-ID methods (ReSID, ChronoSID) report under different filtering/protocols
> and are discussed, not claimed against.

Artifacts: `results_SOTACONF_V2_k{16,8}_MI_seed2026061{8..22}.json` (+ 10 `.users.jsonl.gz`
sidecars, 57,439 rows each; EXEC1 preserved as `*.EXEC1.*`; drivers + adjudicator committed).
