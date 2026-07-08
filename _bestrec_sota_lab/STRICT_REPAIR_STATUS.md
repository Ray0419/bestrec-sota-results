# Strict Repair Status

Generated: 2026-06-03

Updated: 2026-06-10

## Decision

Approve the repaired full-catalog cold-item claim only.

Latest strict re-audit on 2026-06-10 reviewed
`full_clean_rebuild_confirmatory_masked_candidate_20260701_20260705` and
exited cleanly. The audit found no blocking artifact, fairness, or
reproducibility findings. The approved scope is narrow: cold-item full-catalog
ranking on Beauty, Fashion, Instruments, and Books under protocol
`cold_sota_strict_v2`.

The claim is not a broad warm-start or general recommender SOTA claim. Warm
baselines `ials`, `lightgcn`, and `multivae` are outside this lab gate. The
candidate also uses DropoutNet-derived evidence as a feature/rerank anchor, so
the paper must compare against fixed and tuned official DropoutNet and must not
claim DropoutNet independence.

The repaired approval run uses fresh post-repair seeds
`20260701,20260702,20260703,20260704,20260705`, `mask_seen_in_topm=true`,
required modern cold comparators, `2000` clustered bootstrap replicates, and
run-local full clean-rebuild evidence with `max_metric_abs_diff=0.0` and
`record_multisets_match=true`.

## Repaired

- Added frozen protocol: `protocols/cold_sota_strict_v2.json`.
- Added shared DropoutNet component config:
  `dropoutnet_feature_config_v2.json`.
- Candidate runs now record the protocol and frozen DropoutNet feature config.
- Added `run_official_dropoutnet_fixed.py`, which evaluates the exact
  DropoutNet component used by the candidate as a standalone comparator.
- Finalization now fails for:
  - non-strict-protocol runs,
  - stale confirmatory seeds,
  - missing fixed DropoutNet comparator,
  - missing tuned/official baselines required by the protocol,
  - fixed-HP CLCRec in place of swept CLCRec,
  - missing faithful MELT or TIGER/LIGER-style evidence,
  - bootstrap replicate count below 2000.
- Manifest inputs now include lab code, protocol/config files, imported
  `_bestrec_run` code, cache inputs, canonical records, audits, and imported
  source records where recorded.

## Verified

- Python compile passed for the repaired lab scripts.
- Fixed DropoutNet one-fold Beauty smoke produced canonical full-catalog rows.
- Candidate one-fold Beauty smoke produced canonical full-catalog rows under the
  repaired protocol metadata.
- Full Beauty development run on seeds `101,102,103` produced
  `lc2c_retrieval_ltr` NDCG@10 `0.1428` versus fixed DropoutNet component
  `0.1151`; this is development evidence only, not publication evidence.
- Full all-dataset development run
  `research_strict_v2_all_official_dn_rankblend05_101_103` selected the
  candidate for confirmatory under strict-v2:
  - Beauty: `0.1428` vs fixed DropoutNet `0.1151`
  - Fashion: `0.1365` vs fixed DropoutNet `0.0981`
  - Instruments: `0.0480` vs fixed DropoutNet `0.0239`
  - Books: `0.0407` vs fixed DropoutNet `0.0207`
  This is still development evidence only.
- The old full confirmatory run now fails the strict gate.
- Full confirmatory refuses the old frozen candidate config before compute.
- Fresh strict confirmatory run
  `confirmatory_strict_v2_candidate_20260611_20260615` completed on seeds
  `20260611,20260612,20260613,20260614,20260615`.
  This run is now retired from publication approval after the masked-candidate
  repair and can be used only as internal/exploratory evidence.
- Added complete same-split evidence for fixed DropoutNet, tuned faithful
  DropoutNet, official-checkpoint BLaIR, and HP-swept faithful CLCRec.
- Finalized the current confirmatory run with 2000 clustered bootstrap
  replicates. Beauty remains positive against tuned DropoutNet, but narrowly:
  cluster delta `0.0120`, 95% CI `[0.0014, 0.0227]`.
- Added `run_melt_same_split_audit.py` and ran it on all strict folds. It
  confirms official MELT's item branch has zero train item-contexts for every
  held-out cold item under this protocol, so proxy MELT evidence must remain
  excluded and official MELT should be treated as non-applicable unless the
  claim scope changes.
- Updated the strict gate so official MELT is accepted only as a documented
  non-applicable method with exact status
  `not_applicable_to_zero_interaction_item_cold` and the required
  `official_melt_audit.json` evidence file.
- Added `run_liger_same_split_export.py` and ran it on all strict folds. The
  export produced LIGER-compatible processed sequences, item text, embeddings,
  and target maps for all strict datasets/seeds/folds; LIGER's own
  `process_data_split` parser passed all 100 folds.
- Added `run_liger_same_split_eval.py`, which uses official LIGER RQ-VAE,
  TIGER model construction, `model_forward`, and dense target-scoring modules
  to emit canonical full-catalog JSONL. A Beauty seed `20260611` fold `0`
  200-step smoke produced 525 records with NDCG@10 `0.0152`; on the same fold
  LC2C retrieval LTR is `0.1323` and tuned DropoutNet is `0.1189`.
- Ran the LIGER dense partial across all Beauty strict seeds/folds with 200
  training steps and 5 RQ-VAE epochs. It produced 12,660 schema-valid records
  with NDCG@10 `0.0124`, well below LC2C retrieval LTR `0.1441` and tuned
  DropoutNet `0.1321` on the same Beauty records. This is still not
  publication-grade evidence.
- Added `make_ablation_configs.py`, generating frozen diagnostic configs for:
  `mask_seen_topm_true`, `no_dropoutnet_feature_or_anchor`,
  `dropoutnet_feature_content_anchor`, and
  `dropoutnet_anchor_only_control`.
- Ran a Beauty seed `20260611` fold `0` smoke for
  `mask_seen_topm_true`. The `lc2c_retrieval_ltr` rows were identical to the
  original confirmatory rows on that fold:
  NDCG@10 `0.13227602999197421`, HR@10 `0.26095238095238094`, MRR
  `0.11813527789274467`. This is a single-fold diagnostic only, not a full
  fairness proof.
- Ran the full Beauty strict-seed/fold diagnostic for `mask_seen_topm_true`
  (`ablation_mask_seen_beauty_20260611_20260615_full`). All 12,660 paired
  candidate records are identical to the original confirmatory candidate:
  NDCG@10 `0.144102822835`, delta `0.000000000000`, max absolute delta
  `0.000000000000`. This closes the rerank-pool masking concern for Beauty.
- Ran a Beauty seed `20260611` fold `0` smoke for
  `no_dropoutnet_feature_or_anchor`. Candidate NDCG@10 dropped from
  `0.13227602999197421` to `0.12536743673874576` (`-0.006908593253228457`)
  while remaining above content-direct `0.036048481119653725`, LC2C V2
  `0.011191473494320054`, and local faithful DropoutNet
  `0.05012592924546842` on that fold. This suggests DropoutNet contributes
  measurable lift, but does not by itself explain the fold result; full
  all-seed/all-dataset ablation is still required.
- Ran the full Beauty strict-seed/fold diagnostic for
  `no_dropoutnet_feature_or_anchor`
  (`ablation_no_dn_beauty_20260611_20260615_full`). Candidate NDCG@10 dropped
  from `0.144102822835` to `0.132223455258` (`-0.011879367577`). The ablated
  model remains far above official BLaIR, official CLCRec, fixed DropoutNet,
  and content-direct on Beauty, but it is only slightly above tuned
  `official_dropoutnet` (`0.132223455258` vs `0.132100380468`; paired
  per-user one-sided Wilcoxon raw `p=0.017874`, 136 positive users, 112
  negative users). This makes any claim of DropoutNet-independent Beauty SOTA
  fragile and requires full cross-dataset ablation plus corrected multiple
  testing before publication.
- Ran the full Fashion strict-seed/fold diagnostic for `mask_seen_topm_true`
  (`ablation_mask_seen_fashion_20260611_20260615_full`). Candidate NDCG@10
  dropped from `0.133770656690` to `0.131123862314`
  (`-0.002646794375`). The masked candidate still beats tuned
  `official_dropoutnet` decisively on Fashion by paired per-user raw Wilcoxon
  (`p=1.85556e-66`, 415 positive users, 36 negative users), but the original
  unmasked Fashion result was inflated. The repaired publication candidate
  should use `mask_seen_in_topm=true`, not the original unmasked config.
- Ran the full Fashion strict-seed/fold diagnostic for
  `no_dropoutnet_feature_or_anchor`
  (`ablation_no_dn_fashion_20260611_20260615_full`). Candidate NDCG@10 dropped
  from `0.133770656690` to `0.122716255128`
  (`-0.011054401562`). The ablated model still beats tuned
  `official_dropoutnet` on Fashion (`p=1.11245e-26`, 315 positive users, 118
  negative users), so DropoutNet contributes lift but does not explain the
  whole Fashion result.
- Ran the full Instruments strict-seed/fold diagnostic for
  `mask_seen_topm_true`
  (`ablation_mask_seen_instruments_20260611_20260615_full`). Candidate
  NDCG@10 changed from `0.049103153377` to `0.049060875139`
  (`-0.000042278239`) across 295,130 paired records. The masked candidate
  remains far above tuned `official_dropoutnet` by paired per-user raw
  Wilcoxon (`p=0`, 3,395 positive users, 136 negative users), so the rerank
  masking issue is not material for Instruments.
- Ran the full Instruments strict-seed/fold diagnostic for
  `no_dropoutnet_feature_or_anchor`
  (`ablation_no_dn_instruments_20260611_20260615_full`). Candidate NDCG@10
  dropped from `0.049103153377` to `0.038788602097`
  (`-0.010314551280`) across 295,130 paired records. The ablated model still
  beats tuned `official_dropoutnet` on Instruments by paired per-user raw
  Wilcoxon (`p=1.57226e-163`, 2,432 positive users, 1,034 negative users).
  This confirms DropoutNet contributes real lift but does not fully explain the
  Instruments result.
- Added a candidate-only diagnostic path to `run_confirmatory.py` and
  `sota_common.py` so large ablations can write only `lc2c_retrieval_ltr`
  records while still building the candidate's required feature stack.
- Ran the full Books strict-seed/fold diagnostic for `mask_seen_topm_true`
  (`ablation_mask_seen_books_20260611_20260615_full`). Candidate NDCG@10
  changed from `0.040656206936` to `0.040993031185`
  (`+0.000336824249`) across 3,009,960 paired records. The masked candidate
  remains far above tuned `official_dropoutnet` by paired per-user raw
  Wilcoxon (`p=0`, 12,188 positive users, 1,230 negative users). The Books
  run contains complete candidate rows but only partial non-candidate baseline
  rows, so it must be used through the paired ablation report, not as a
  standalone baseline table.
- Ran the full Books strict-seed/fold diagnostic for
  `no_dropoutnet_feature_or_anchor`
  (`ablation_no_dn_books_20260611_20260615_full`). Candidate NDCG@10 dropped
  from `0.040656206936` to `0.036918209844`
  (`-0.003737997092`) across 3,009,960 paired records. The ablated model still
  beats tuned `official_dropoutnet` by paired per-user raw Wilcoxon (`p=0`,
  9,140 positive users, 3,919 negative users). This closes the full
  DropoutNet-dependence ablation set: DropoutNet helps on every dataset, but
  removing it does not erase the gains on Fashion, Instruments, or Books;
  Beauty remains the fragile case.
- At this point in the repair log, the strict gate still failed because
  TIGER/LIGER full-catalog score records were absent. This blocker is now
  closed in the 2026-06-10 approved run
  `full_clean_rebuild_confirmatory_masked_candidate_20260701_20260705`.

## Newly Fixed Harness Issue

- `run_official_dropoutnet_fixed.py` previously overwrote `run_config.json`
  when adding the fixed comparator to an existing candidate run. This was
  repaired so future baseline additions write
  `baseline_run_config_official_dropoutnet_fixed.json` instead.
- Initial LIGER smoke-export verification incorrectly expected every fold cold
  item even when a smoke target cap was supplied. This was repaired so capped
  smoke runs verify the exported target set, while full runs verify every
  exported cold target.
- Official LIGER `load_data` assumes a non-empty unseen-validation item set.
  The strict BEST-Rec export has no cold validation targets, so the evaluation
  runner now records a seen-item validation placeholder used only to keep LIGER's
  validation bookkeeping shape-safe. Training targets and test records are not
  changed by this placeholder.
- `run_liger_same_split_eval.py` could previously mark a high-step Beauty-only
  run as publication-grade. This is repaired: publication-grade status now
  requires all four datasets, the frozen strict seed list, no fold/target caps,
  and minimum training/RQ-VAE thresholds.
- Diagnostic ablation configs could have been run at full scale and accidentally
  passed the same publication gate as the candidate. This is repaired:
  `run_confirmatory.py` preserves ablation metadata in `run_config.json`, and
  `finalize.py` rejects any frozen config whose `publication_role` is not
  `publication_candidate`.
- `run_liger_same_split_eval.py` now supports `--resume` and `--fold-ids`.
  Resume skips only folds whose existing canonical record count exactly matches
  the exported target count, and refuses partial/mismatched existing fold rows.
  A tiny Beauty fold-0 five-target smoke was run and rerun with `--resume`; the
  second invocation skipped the complete fold and preserved
  `publication_grade_records=false`.
- `import_liger_records.py` now checks exact per-fold record coverage from the
  source LIGER audit before copying records. A dry-run import of the five-record
  smoke source into the confirmatory run was correctly rejected as
  non-publication-grade.
- Added `clean_rebuild_audit.py`. The current-artifact consistency audit passes
  required-artifact, manifest-output-hash, table/significance, and proxy-table
  checks for `confirmatory_strict_v2_candidate_20260611_20260615`, but it
  intentionally records `strict_clean_rebuild_passed=false` because no
  destructive clean rebuild has been run yet.
- Updated the strict protocol and finalizer so `mask_seen_in_topm=true` is now
  mandatory for any publication candidate. Re-finalizing the old
  `confirmatory_strict_v2_candidate_20260611_20260615` run now fails explicitly
  with `Candidate LTR config mask_seen_in_topm=False does not match required
  publication value True`.
- Added `_bestrec_sota_lab/publication_candidate_mask_seen_v2.json` as the
  repaired frozen candidate config. A Beauty fold-0 smoke confirms it is not
  treated as a diagnostic ablation and satisfies the new mask requirement.
- Updated the strict protocol, repaired frozen candidate config, and full
  confirmatory precheck to require the fresh post-repair seeds
  `20260701,20260702,20260703,20260704,20260705`. A full confirmatory attempt
  with retired seeds `20260611,20260612,20260613,20260614,20260615` is refused
  before compute.
- Added `run_confirmatory_chunk.py`, a chunk-safe runner for the repaired
  candidate. It keeps a full four-dataset `run_config.json` while allowing
  dataset-by-dataset execution, so partial long Books runs can be resumed
  without corrupting the confirmatory config.
- Ran the repaired `mask_seen_in_topm=true` candidate on fresh post-repair
  seeds `20260701,20260702,20260703,20260704,20260705` for Beauty, Fashion,
  Instruments, and Books. All four datasets have all `25/25` seed/folds:
  - Beauty: NDCG@10 `0.148825868265`, `12,675` records.
  - Fashion: NDCG@10 `0.130137817674`, `18,996` records.
  - Instruments: NDCG@10 `0.049575215957`, `295,130` records.
  - Books: NDCG@10 `0.040225492558`, `3,009,960` records.
- Continued the fresh Books candidate chunk with safe `--max-new-folds`
  resumes until all Books seed/folds completed. The final Books candidate file
  is valid JSONL with `3,009,960` records and covers all `25/25` seed/folds.
  This completes candidate coverage only; it is not publication evidence until
  baselines, bootstrap, and clean rebuild requirements are also satisfied.
- Fixed another strict-gate weakness: `finalize.py` now records method
  seed/fold coverage and fails publication if the candidate or any required
  evidence method lacks all frozen seed/folds. It also checks exact per-fold
  record counts against the evaluator's eligible-user target count, so a
  partially written fold cannot pass as complete. This check no longer fails
  for the fresh candidate run because all candidate seed/folds are complete.
- Ran the required fresh-seed `official_blair` comparator on the repaired
  confirmatory run. It is complete on all four datasets:
  - Beauty: NDCG@10 `0.043254142790`, `12,675` records.
  - Fashion: NDCG@10 `0.037732308978`, `18,996` records.
  - Instruments: NDCG@10 `0.007166005337`, `295,130` records.
  - Books: NDCG@10 `0.007794307885`, `3,009,960` records.
- Ran the required fresh-seed MELT same-split applicability audit and fixed its
  canonical artifact filename to `official_melt_audit.json`. The fresh gate now
  accepts `official_melt` only as
  `not_applicable_to_zero_interaction_item_cold`; this is not a win over MELT.

## Still Required

- The `mask_seen_topm_true` ablation is now complete on all four datasets.
  Beauty is unchanged, Instruments changes only by `-0.000042278239`, Books
  improves by `+0.000336824249`, and Fashion shows a real decrease. The masked
  config should be the repaired default before any new confirmatory claim, but
  it must be rerun on fresh post-repair seeds before it can support publication.
- Do not make a broad DropoutNet-independent claim. The full no-DropoutNet
  ablation set is complete, but Beauty is fragile after removing DropoutNet
  (`0.132223455258` versus tuned `official_dropoutnet` `0.132100380468`, raw
  `p=0.017874`). Fashion, Instruments, and Books remain clearly above tuned
  `official_dropoutnet` without the DropoutNet feature/anchor.
- Scale the LIGER/TIGER same-split evaluation runner from smoke settings to a
  frozen full configuration on all verified exported folds and import canonical
  full-catalog records.
- Rerun the repaired `mask_seen_in_topm=true` candidate and all mandatory
  publication baselines on seeds
  `20260701,20260702,20260703,20260704,20260705`. The repaired candidate is
  now complete for all four datasets, `official_blair` is complete, and
  `official_melt` has documented non-applicability. The next blockers are
  LC2C V2, fixed/tuned DropoutNet, official CLCRec, and TIGER/LIGER evidence.
- Add or justify exclusion of very recent cold-item/content-cold comparators.
- Run a clean rebuild test from documented lab commands.
- Approve only if every strict publication gate passes.
