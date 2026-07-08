# Strict Audit Of Claude's Resubmitted SOTA Claim

Audit time: 2026-07-08, second-pass audit after resubmission  
Auditor stance: hostile reviewer / publication gatekeeper  
Prior audit: `CLAUDE_SOTA_RESULT_AUDIT_2026-07-08.md`  
Resubmission materials audited:

- `RESPONSE_TO_CODEX_AUDIT.md`
- `SOTA_CONFIRM_PREREG_V2.md`
- `SOTA_CONFIRM_V2_RESULTS.md`
- `SOTA_ACHIEVED.md`
- `PROTOCOL_PARITY_APPENDIX.md`
- `_bestrec_run/results_SOTACONF_V2_k{16,8}_MI_seed2026061{8..22}.json`
- Local sidecars `_bestrec_run/results_SOTACONF_V2_*.users.jsonl.gz`
- `PAPER_DRAFT.md`
- `git` history and current repository state

## Decision

**Core V2 numeric result: provisionally passes the narrow point-estimate gate.**

**Publication/resubmission package: still not accepted as publication-ready. Major revision required.**

The resubmission is much stronger than V1. The fresh V2 runs are real local artifacts, the repo is clean, the result JSONs are tracked, the manifests record a single clean commit, and the per-user sidecars on disk exactly reproduce the headline metrics.

However, I still would not approve the paper/package as submitted because several audit claims are overstated or incomplete:

1. The per-user sidecars are **ignored and untracked**, despite the response saying they are part of the artifact bundle.
2. The result JSONs do **not** record sidecar SHA256s, despite the preregistration saying those hashes are recorded.
3. EXEC2 did **not** use the prereg-introducing commit required by the literal prereg rule. The code/script/prereg diff is empty, so this is likely harmless, but it is still a documented protocol deviation.
4. The protocol appendix admits a 511,836 vs 511,835 interaction-count discrepancy while the prereg says the total "matches" the comparator paper.
5. The manuscript file `PAPER_DRAFT.md` is stale and does not yet carry the V2 claim, V2 caveats, or V2 literature positioning.

So: **I no longer reject the V2 numbers. I still reject the resubmission package until the artifact and wording defects below are fixed.**

## What Improved Since V1

The resubmission fixed several of the original hard blockers:

- `SOTA_CONFIRM_PREREG_V2.md` was committed before V2 EXEC1 began.
- Seeds 20260608-20260617 were correctly demoted to consumed evidence.
- Fresh seeds 20260618-20260622 were used for V2.
- Both K=16 and K=8 were run, making the claim less dependent on one kernel setting.
- The current worktree is clean.
- V2 result JSONs are tracked in git.
- Result JSONs now include created time, argv, hostname, Python/Torch/GPU versions, data hashes, interaction counts, git commit, branch, and dirty-tracked flag.
- The claim wording is narrowed to "exceeds the published HSTU-BLaIR point estimate", not "statistically significantly beats HSTU-BLaIR."

These are real improvements, not cosmetic ones.

## Recomputed V2 Results

I recomputed the fresh V2 aggregation directly from the tracked JSONs and independently ran the summarizer:

Command checked:

```powershell
uv --project _bestrec_run run python _bestrec_run\summarize_sota_confirm_v2.py
```

### K=16

| Seed | NDCG@10 | HR@10 | n_eval | Best epoch | Manifest commit | Dirty |
|---:|---:|---:|---:|---:|---|---|
| 20260618 | 0.0412647461 | 0.0740785877 | 57,439 | 20 | 86816be835ec... | False |
| 20260619 | 0.0410805520 | 0.0737303922 | 57,439 | 20 | 86816be835ec... | False |
| 20260620 | 0.0414740849 | 0.0742700952 | 57,439 | 14 | 86816be835ec... | False |
| 20260621 | 0.0415161932 | 0.0747575689 | 57,439 | 16 | 86816be835ec... | False |
| 20260622 | 0.0422605757 | 0.0749664862 | 57,439 | 18 | 86816be835ec... | False |

Aggregate:

- Mean NDCG@10: **0.0415192304**
- Sample SD: **0.0004496780**
- 95% t lower bound: **0.0409608814**
- All 5 seeds > 0.0406: **yes**

### K=8

| Seed | NDCG@10 | HR@10 | n_eval | Best epoch | Manifest commit | Dirty |
|---:|---:|---:|---:|---:|---|---|
| 20260618 | 0.0411794697 | 0.0738174411 | 57,439 | 16 | 86816be835ec... | False |
| 20260619 | 0.0409920950 | 0.0737303922 | 57,439 | 17 | 86816be835ec... | False |
| 20260620 | 0.0415084445 | 0.0748794373 | 57,439 | 15 | 86816be835ec... | False |
| 20260621 | 0.0414965327 | 0.0745834712 | 57,439 | 13 | 86816be835ec... | False |
| 20260622 | 0.0408388393 | 0.0731558697 | 57,439 | 16 | 86816be835ec... | False |

Aggregate:

- Mean NDCG@10: **0.0412030762**
- Sample SD: **0.0002987915**
- 95% t lower bound: **0.0408320776**
- All 5 seeds > 0.0406: **yes**

The frozen summarizer also prints:

```text
DUAL GATE VERDICT: PASS
```

## Per-User Sidecar Check

All ten local `.users.jsonl.gz` sidecars exist on disk and contain **57,439 rows each**.

I streamed every sidecar and recomputed:

- mean NDCG@10
- mean HR@10
- mean MRR
- row-level NDCG from `rank0`

The sidecars exactly match the JSON summaries to floating-point tolerance, and all row-level NDCG formulas are correct:

```text
bad_ndcg_rows = 0 for all 10 sidecars
```

This is a strong positive. It means the per-user records are internally consistent with the headline JSONs.

## External Comparator Check

The HSTU-BLaIR comparator remains real and correctly cited as a point estimate. The HSTU-BLaIR v3 paper reports Amazon Reviews 2023 `Musical Instruments` with 24,587 items, 57,439 users, and 511,835 interactions, and reports HSTU-BLaIR NDCG@10 = 0.0406 for `Musical Instruments`. Source: [HSTU-BLaIR arXiv v3](https://arxiv.org/html/2504.10545v3).

The resubmission also correctly recognizes newer 2026 semantic-ID work as related but not protocol-identical. ReSID reports MI NDCG@10 = 0.0346, but with different dataset statistics: 57,359 users, 23,742 items, 490,522 interactions. Source: [ReSID arXiv](https://arxiv.org/html/2602.02338v1). ChronoSID reports MI NDCG@10 around 0.0347 under the SID protocol and states that its main results are averaged over five runs. Source: [ChronoSID arXiv](https://arxiv.org/html/2607.03918v1).

I agree with the resubmission's narrow framing: these SID papers must be discussed, but they are not direct same-split refutations of the HSTU-BLaIR-family point-estimate comparison.

## Blocking Findings

### R1. Per-user sidecars are not committed

This is the most concrete remaining artifact defect.

The response says the resubmission bundle includes:

> 10 result JSONs with embedded manifests + 10 per-user sidecars

But `git ls-files` shows **0 tracked sidecars**, and `git check-ignore` shows they are ignored:

```text
.gitignore:37:_bestrec_run/*.users.jsonl.gz
```

The files exist locally, but they will not be present for a reviewer who clones the repository unless they are separately archived. This directly weakens the claim that per-user bootstrap/tie/rank diagnostics are reproducible from the submitted artifact bundle.

Required fix:

- Either commit them with `git add -f`, or publish them in an external artifact archive.
- Add a manifest containing file size, row count, and SHA256 for every sidecar.
- Update the resubmission text to state exactly where reviewers obtain them.

### R2. Result JSONs do not record sidecar SHA256s

`SOTA_CONFIRM_PREREG_V2.md` says sidecar SHA256s are recorded in the results file. They are not.

The V2 JSON provenance keys are:

```text
argv, best_test_epoch, created_at, cuda_device, data_sha256,
git_branch, git_commit, git_dirty_tracked, hostname,
n_interactions, python, torch
```

There is no sidecar path, row count, or sidecar hash in the JSON. The sidecars are internally consistent, but the manifest story is overstated.

Required fix:

- Add `user_records_path`, `user_records_n`, and `user_records_sha256` to a separate manifest, or regenerate JSONs with those fields.
- Do not claim the result files already contain those hashes until they actually do.

### R3. EXEC2 violates the literal prereg commit rule

The prereg says every V2 result JSON must have a `git_commit` equal to the commit introducing `SOTA_CONFIRM_PREREG_V2.md`.

- Prereg-introducing commit: `832a8ffcaf674c97f35e6b75fcd481bd0eaf893b`
- EXEC2 manifest commit: `86816be835ec47d772f6f880fabdcf9af244d940`

I verified:

```text
git diff 832a8ff..86816be -- '*.py' '*.sh' SOTA_CONFIRM_PREREG_V2.md ...
```

returns no differences for the model code, driver, summarizer, or prereg file. So this is probably computationally harmless. But it is still not the literal frozen rule.

The summarizer also does not check against the prereg commit. It checks only that all runs use a single commit and `dirty_tracked=False`.

Required fix:

- Stop saying the exact prereg rule was followed. Say there was a documented doc-only commit deviation.
- Preferably add a source-tree hash or code-file hash family to the manifest so doc-only commits can be separated from source changes.
- If the authors want a fully literal pass, rerun from exactly `832a8ff` or produce an immutable code-hash rule that was frozen before the rerun.

### R4. Interaction-count parity is inconsistent

The prereg says:

```text
train 396,958 / valid 57,439 / test 57,439
(matches the comparator paper's reported 511,835 total)
```

But that sum is **511,836**, not 511,835.

`PROTOCOL_PARITY_APPENDIX.md` correctly admits:

```text
HSTU-BLaIR paper: 511,835
ours: 511,836
```

This one-interaction difference is probably harmless, and users/items match exactly. But with a thin result margin, exact protocol wording matters. The docs currently both admit and deny the mismatch.

Required fix:

- Correct `SOTA_CONFIRM_PREREG_V2.md` or add an erratum saying the interaction total differs by one.
- Explain exactly why the off-by-one occurs and why it cannot affect leave-one-out evaluation materially.
- Do not use "matches the comparator total" wording.

### R5. Clean rebuild is not yet demonstrated

`_bestrec_run/run_sota_confirm_v2.sh` is useful, but it is idempotent and skips existing outputs:

```bash
if [ -f "$O" ]; then echo "skip k${ARM} seed ${S} (exists)"; continue; fi
```

That is not a clean rebuild proof unless someone first deletes or moves the outputs and records the rerun. Also, `data_5core/` and `cache_5core/` are ignored, so a fresh clone alone cannot run the script.

Required fix:

- Add a `--force` or clean-output mode.
- Add a clean rebuild log from a separate output directory.
- Document exactly how to obtain the ignored data/cache artifacts or provide an external archive with hashes.

### R6. Manuscript is stale

If `PAPER_DRAFT.md` is the manuscript being resubmitted, it is not aligned with the V2 claim. It still has a 2026-06-22 status, centers the Video_Games/tail-law paper, and still lists the older Musical_Instruments result as `0.0413 +/- 0.0005` rather than the V2 dual-kernel result.

The response says the related-work update will be folded into the draft after V2 resolves. That has not happened in the file I audited.

Required fix:

- Update the manuscript itself with the exact V2 frozen claim.
- Include the comparator limitation, one-category scope, single-seed point-estimate limitation, ReSID/ChronoSID positioning, and protocol-parity caveat.
- Remove or clearly quarantine stale MI numbers.

## Non-Blocking Findings

### N1. The narrow claim wording is now mostly acceptable

The resubmission no longer claims "statistically significantly better than HSTU-BLaIR." It says the seed-level mean and confidence interval exceed the published point estimate. That is the right ceiling given the comparator is single-seed.

### N2. The V2 numerical result is stronger than V1

The dual-kernel gate is a meaningful improvement. K=8 and K=16 both clear the point estimate with fresh seeds.

### N3. EXEC1 void handling was honest

The resubmission preserved the dirty EXEC1 artifacts and reran all 10 runs under clean EXEC2 rather than silently replacing only the bad seed. That is good scientific hygiene.

## What I Would Allow The Paper To Claim After Fixes

The maximum defensible claim is:

> On our reproduced Amazon Reviews 2023 Musical_Instruments 5-core leave-last-out full-catalog protocol, fresh five-seed runs for both K=8 and K=16 exceed the published HSTU-BLaIR NDCG@10 point estimate of 0.0406. Because the comparator is a published single-seed number and could not be rerun on our hardware, this is a per-category point-estimate comparison, not a paired or distributional superiority claim.

I would not allow:

- "statistically significantly better than HSTU-BLaIR"
- "general SOTA"
- "state of the art on Amazon Reviews 2023"
- "SOTA recommender"
- "audit-proof" unless the sidecars and manifest issues are fixed

## Required Fixes Before Approval

1. Track or externally archive all 10 V2 sidecars.
2. Add sidecar SHA256s, sizes, and row counts to a manifest.
3. Correct the sidecar-hash claim in `SOTA_CONFIRM_PREREG_V2.md`.
4. Correct the 511,835 vs 511,836 interaction-count wording.
5. Reframe the EXEC2 commit mismatch as a documented doc-only deviation, or rerun from the exact prereg commit.
6. Update `PAPER_DRAFT.md` to match the V2 result and caveats.
7. Add a real clean-rebuild proof or stop claiming a clean rebuild has been demonstrated.

## Final Verdict

**Numerical gate: pass for the narrow V2 point-estimate comparison.**

**Publication package: reject until artifact packaging and manuscript wording are fixed.**

This is no longer a "the result is probably not real" situation. The V2 result looks real and fair enough for a narrowly worded comparison. The remaining failure is that the resubmission still overclaims its audit completeness. A strict reviewer can still reject on missing committed sidecars, absent sidecar hashes, the literal prereg commit mismatch, and a stale manuscript.
