# Strict Audit Of Claude's Third Resubmission

Audit date: 2026-07-10  
Auditor stance: hostile reviewer / publication gatekeeper  
Earlier audits:

- `CLAUDE_SOTA_RESULT_AUDIT_2026-07-08.md`
- `CLAUDE_SOTA_RESUBMISSION_AUDIT_2026-07-08.md`

Main files audited:

- `RESPONSE_TO_CODEX_AUDIT.md`
- `SOTA_ACHIEVED.md`
- `SOTA_CONFIRM_PREREG_V2.md`
- `SOTA_CONFIRM_PREREG_V2_ERRATA.md`
- `SOTA_CONFIRM_V2_RESULTS.md`
- `PROTOCOL_PARITY_APPENDIX.md`
- `PAPER_DRAFT.md`
- `_bestrec_run/SOTACONF_V2_sidecar_manifest.json`
- `_bestrec_run/results_SOTACONF_V2_k{16,8}_MI_seed2026061{8..22}.json`
- `_bestrec_run/results_SOTACONF_V2_*.users.jsonl.gz`
- `_bestrec_run/rebuild_v2/*`
- Current git history and status

## Decision

**Approve the narrow V2 claim, with mandatory wording limits.**

The resubmission has now fixed the blockers from the prior audit well enough that I would no longer reject the package on result-validity or reproducibility grounds.

Allowed claim:

> On the reproduced AR2023 `Musical_Instruments` 5-core leave-last-out full-catalog protocol, fresh five-seed runs for both K=16 and K=8 exceed the published HSTU-BLaIR NDCG@10 point estimate of 0.0406. This is a per-category comparison to a published single-seed point estimate, not a paired statistical superiority claim and not a general recommender-system SOTA claim.

Not allowed:

- "statistically significantly better than HSTU-BLaIR"
- "general SOTA"
- "SOTA on Amazon Reviews 2023"
- "beats all current recommender algorithms"
- "paired superiority over HSTU-BLaIR"

## What I Verified This Round

### Repository state

Current branch: `codex/bestrec-sota-results`  
Current HEAD: `2a5003e Clean-rebuild demonstration (R5): from-scratch regeneration passes the dual gate`  
Working tree: clean

New commits since the previous audit:

- `89f32fb Address Codex resubmission audit R1-R6 (numbers accepted; packaging fixed)`
- `2a5003e Clean-rebuild demonstration (R5): from-scratch regeneration passes the dual gate`

These commits are substantive: sidecars are now tracked, a sidecar manifest exists, the preregistration errata exists, paper text was updated, the driver supports rebuild output directories, and a rebuild directory is committed.

## V2 Gate Recheck

I reran:

```powershell
uv --project _bestrec_run run python _bestrec_run\summarize_sota_confirm_v2.py
```

Result:

### K=16 gated EXEC2

- Seeds: 20260618-20260622
- Mean NDCG@10: **0.04152**
- SD: **0.00045**
- 95% lower bound: **0.04096**
- Seeds above 0.0406: **5/5**
- Gate: **PASS**

### K=8 gated EXEC2

- Seeds: 20260618-20260622
- Mean NDCG@10: **0.04120**
- SD: **0.00030**
- 95% lower bound: **0.04083**
- Seeds above 0.0406: **5/5**
- Gate: **PASS**

Manifest consistency:

- Single commit in gated result manifests: `86816be835ec47d772f6f880fabdcf9af244d940`
- `dirty_tracked=False`
- Data hashes match preregistration
- `n_eval=57,439` for all ten gated runs

## Sidecar Audit

Prior blocker R1/R2 is fixed for the gated artifacts.

Verified:

- `git ls-files -- _bestrec_run/results_SOTACONF_V2_k*.users.jsonl.gz` returns **20** tracked sidecars.
- `.gitignore` now includes an explicit exception for gated V2 sidecars.
- `_bestrec_run/SOTACONF_V2_sidecar_manifest.json` contains:
  - 10 gated EXEC2 sidecars
  - 10 preserved EXEC1 sidecars
  - bytes, row count, and SHA256 for each

I recomputed every manifest entry:

- Gated EXEC2 sidecars: **10/10 hash, bytes, and row count match**
- Preserved EXEC1 sidecars: **10/10 hash, bytes, and row count match**
- Every sidecar row count: **57,439**

This is a real fix.

## Clean-Rebuild Audit

I reran:

```powershell
uv --project _bestrec_run run python _bestrec_run\summarize_sota_confirm_v2.py _bestrec_run\rebuild_v2
```

Rebuild result:

### K=16 rebuild

- Mean NDCG@10: **0.04150**
- SD: **0.00047**
- 95% lower bound: **0.04092**
- Seeds above 0.0406: **5/5**
- Gate: **PASS**

### K=8 rebuild

- Mean NDCG@10: **0.04121**
- SD: **0.00030**
- 95% lower bound: **0.04084**
- Seeds above 0.0406: **5/5**
- Gate: **PASS**

Rebuild provenance:

- Single commit in rebuild result manifests: `89f32fb55c204812e96097ac182d3bd2e666ec78`
- `dirty_tracked=False`
- Data hashes match preregistration
- Rebuild JSON manifests include `user_records_path`, `user_records_n`, `user_records_sha256`, and `code_sha256`

Gated-vs-rebuild comparison:

- 10 matched result pairs
- Maximum absolute NDCG@10 difference: **0.0001116918**
- Both gated and rebuild runs pass the dual gate

This resolves the prior clean-rebuild objection. The residual nondeterminism is small relative to the gate margin.

## Code-Identity Check

I checked the rebuild `code_sha256` fields against the current protocol files:

- `run_sasrec_sbert.py`: match
- `run_sota_confirm_v2.sh`: match
- `summarize_sota_confirm_v2.py`: match

I also checked the diff from the rebuild commit to current HEAD for protocol files. Only `.gitignore` and `RESPONSE_TO_CODEX_AUDIT.md` changed after the rebuild commit; the model, driver, summarizer, preregistration, errata, paper, and appendix are unchanged.

## External Comparator And Literature Check

The HSTU-BLaIR comparator remains correctly identified for the narrow claim. The HSTU-BLaIR v3 paper reports `Musical Instruments` with 24,587 items, 57,439 users, 511,835 interactions, and HSTU-BLaIR NDCG@10 = 0.0406. Source: [HSTU-BLaIR arXiv v3](https://arxiv.org/html/2504.10545v3).

The paper now discusses newer semantic-ID work. Current checks:

- ReSID reports MI NDCG@10 = 0.0346 in its Table 4 under a different filtered setup/statistics. Source: [ReSID arXiv](https://arxiv.org/html/2602.02338v1).
- ChronoSID reports different dataset statistics for MI (57,359 users, 23,742 items, 490,522 interactions) and reports ChronoSID MI NDCG@10 = 0.0346 in Table 2. Source: [ChronoSID arXiv](https://arxiv.org/html/2607.03918v1).

These do not directly overturn the HSTU-BLaIR-family point-estimate comparison because their filtered universe differs.

## Remaining Issues

These are not result-validity blockers, but they should be fixed before final submission.

### M1. ChronoSID number should be stated consistently

`PROTOCOL_PARITY_APPENDIX.md` and `PAPER_DRAFT.md` describe ChronoSID as around `0.0345`. The arXiv HTML table I inspected lists MI NDCG@10 as `0.0346`. This is a tiny rounding/copyediting issue, not a claim blocker.

Required fix:

- Use `0.0346` for ChronoSID MI NDCG@10, or say "about 0.0346."

### M2. The top-level rebuild driver log is cited but ignored

`RESPONSE_TO_CODEX_AUDIT.md` cites `_bestrec_run/run_rebuild_v2_driver.log`. That file exists locally, but it is ignored by `.gitignore` and is not tracked. The individual rebuild run logs are tracked, and the rebuild JSONs are tracked, so this is not fatal.

Required fix:

- Either stop citing the top-level driver log as an artifact, or force-add it.

### M3. The response still contains some old phrasing around "immutable commit 832a8ff"

The response later correctly discloses the `86816be` EXEC2 deviation and the errata. Still, the opening paragraph can be read as if the decisive final run itself used `832a8ff`.

Required fix:

- Make the chronology unambiguous: prereg introduced at `832a8ff`; gated EXEC2 ran at doc-only descendant `86816be`; rebuild ran at `89f32fb`; protocol code identity is demonstrated by code hashes and empty protocol diffs.

### M4. Preregistration was not literally followed, but the deviation is now acceptable

The literal commit-equality rule was not satisfied. This remains true. The difference from the prior audit is that the deviation is now explicitly acknowledged in `SOTA_CONFIRM_PREREG_V2_ERRATA.md`, shown to be doc-only, and backed by a clean rebuild with code hashes. I no longer consider it a rejection-level problem, but the final paper must not say the literal prereg rule was followed exactly.

## Final Verdict

**Accept the narrow V2 result claim.**

**Do not accept any broader SOTA wording.**

This is now a credible, reproducible, provenance-backed result for a narrow claim: fresh multi-seed K=8 and K=16 runs exceed the published HSTU-BLaIR `Musical_Instruments` point estimate under the reproduced protocol. The remaining fixes are copyediting/artifact-polish items, not grounds to reject the numerical claim.

If the authors keep the claim scoped exactly as written above, I would approve this portion of the paper after minor revision.
