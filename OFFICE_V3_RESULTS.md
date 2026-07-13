# Office_Products V3 campaign results (PREREG_OFFICE_V3.md)

Mechanical adjudication blocks appended by `_bestrec_run/adjudicate_office_v3.py`.
Gate (frozen before any run): per kernel arm over 5 fresh seeds, final-epoch
FULL-catalog NDCG@10 (history[-1].test, n_eval == 223,308) 95% t-CI lower bound
must exceed 0.0279 (environment-matched local regeneration of the comparator)
with >=4/5 seeds individually above it; both arms must pass; comparability
conditions 1-3 must hold. One-sided failures, nulls and voids are published
with identical prominence.

---

## Adjudication 2026-07-13 14:31:39 (block-id 196799e7c46d)
Arms k16/k8; seeds [20260728, 20260729, 20260730, 20260731, 20260732]; gate frozen in PREREG_OFFICE_V3.md.

- cond3 OK (E1) k8 seed 20260728: dirty tree consists only of exempt audit-log files per PREREG_OFFICE_V3.md E1 (treestate sidecar verified)
- cond3 OK (E1) k8 seed 20260729: dirty tree consists only of exempt audit-log files per PREREG_OFFICE_V3.md E1 (treestate sidecar verified)
- cond3 OK (E1) k8 seed 20260730: dirty tree consists only of exempt audit-log files per PREREG_OFFICE_V3.md E1 (treestate sidecar verified)
- cond3 OK (E1) k8 seed 20260731: dirty tree consists only of exempt audit-log files per PREREG_OFFICE_V3.md E1 (treestate sidecar verified)
- cond3 OK (E1) k8 seed 20260732: dirty tree consists only of exempt audit-log files per PREREG_OFFICE_V3.md E1 (treestate sidecar verified)
- cond3 OK (E1) k16 seed 20260728: dirty tree consists only of exempt audit-log files per PREREG_OFFICE_V3.md E1 (treestate sidecar verified)
- cond3 OK (E1) k16 seed 20260729: dirty tree consists only of exempt audit-log files per PREREG_OFFICE_V3.md E1 (treestate sidecar verified)
- cond3 OK (E1) k16 seed 20260730: dirty tree consists only of exempt audit-log files per PREREG_OFFICE_V3.md E1 (treestate sidecar verified)
- cond3 OK (E1) k16 seed 20260731: dirty tree consists only of exempt audit-log files per PREREG_OFFICE_V3.md E1 (treestate sidecar verified)
- cond3 OK (E1) k16 seed 20260732: dirty tree consists only of exempt audit-log files per PREREG_OFFICE_V3.md E1 (treestate sidecar verified)
- git commits across runs: ['acbe282f3644']
- cond1 OK: all 10 manifests record 223,308 users / 77,551 items / 1,800,878 interactions (comparator 1,800,877, delta 1 <= 1)
- cond3 OK: clean tracked tree, identical embedded code hashes and data SHA256s across all 10 runs
- cond2: re-derived reference best full-eval NDCG@10 = 0.02786 (-> 0.0279) / final = 0.02752 (-> 0.0275)
- cond2 OK: all 5 reference artifacts hash-match RELEASE_MANIFEST; references re-derived as 0.0279 (best) / 0.0275 (final)
- k16 seed 20260728: final-epoch full-catalog NDCG@10 = 0.03060 (> 0.0279; > 0.0271)
- k16 seed 20260729: final-epoch full-catalog NDCG@10 = 0.03053 (> 0.0279; > 0.0271)
- k16 seed 20260730: final-epoch full-catalog NDCG@10 = 0.03046 (> 0.0279; > 0.0271)
- k16 seed 20260731: final-epoch full-catalog NDCG@10 = 0.03033 (> 0.0279; > 0.0271)
- k16 seed 20260732: final-epoch full-catalog NDCG@10 = 0.03041 (> 0.0279; > 0.0271)
- **ARM k16**: mean 0.03047  sd 0.00011  95% CI-LB 0.03033  vs 0.0279: LB > ref, 5/5 seeds above; vs 0.0271: LB > ref, 5/5 seeds above -> **PASS**
- k8 seed 20260728: final-epoch full-catalog NDCG@10 = 0.03025 (> 0.0279; > 0.0271)
- k8 seed 20260729: final-epoch full-catalog NDCG@10 = 0.03037 (> 0.0279; > 0.0271)
- k8 seed 20260730: final-epoch full-catalog NDCG@10 = 0.03030 (> 0.0279; > 0.0271)
- k8 seed 20260731: final-epoch full-catalog NDCG@10 = 0.03030 (> 0.0279; > 0.0271)
- k8 seed 20260732: final-epoch full-catalog NDCG@10 = 0.03026 (> 0.0279; > 0.0271)
- **ARM k8**: mean 0.03029  sd 0.00005  95% CI-LB 0.03024  vs 0.0279: LB > ref, 5/5 seeds above; vs 0.0271: LB > ref, 5/5 seeds above -> **PASS**

**CAMPAIGN VERDICT: PASS** (arms: k16: PASS, k8: PASS; comparability conditions OK)

Frozen claim wording applies (PREREG_OFFICE_V3.md): a per-category point-estimate comparison against the published 0.0271 and the environment-matched single-run local regeneration 0.0279; no paired or distributional superiority claimed; not SOTA on Office_Products, not SOTA on Amazon Reviews 2023, and not a general-SOTA claim of any kind.

## Per-user sidecar inventory (2026-07-13; PREREG_OFFICE_V3.md ERRATUM E2)

All ten runs' FINAL-EPOCH per-user records exist locally and are hash-embedded in the
tracked result JSONs (sidecar files themselves are local-only per the paper's
availability statement):

- k16 seed 20260728: final-epoch sidecar (separate file); n=223308; sha256=a194bc87a3c4a7a3...; path=results_OFFICEV3_k16_seed20260728.final.users.jsonl.gz
- k16 seed 20260729: regular sidecar == final-epoch record (best epoch == final; E2); n=223308; sha256=6692084ee88c1ac0...; path=results_OFFICEV3_k16_seed20260729.users.jsonl.gz
- k16 seed 20260730: final-epoch sidecar (separate file); n=223308; sha256=fb869656c1397058...; path=results_OFFICEV3_k16_seed20260730.final.users.jsonl.gz
- k16 seed 20260731: regular sidecar == final-epoch record (best epoch == final; E2); n=223308; sha256=d75d4f9de971fe1d...; path=results_OFFICEV3_k16_seed20260731.users.jsonl.gz
- k16 seed 20260732: final-epoch sidecar (separate file); n=223308; sha256=48c7c36718ccf13a...; path=results_OFFICEV3_k16_seed20260732.final.users.jsonl.gz
- k8 seed 20260728: final-epoch sidecar (separate file); n=223308; sha256=908663d91907ed59...; path=results_OFFICEV3_k8_seed20260728.final.users.jsonl.gz
- k8 seed 20260729: final-epoch sidecar (separate file); n=223308; sha256=4544875485f2b59b...; path=results_OFFICEV3_k8_seed20260729.final.users.jsonl.gz
- k8 seed 20260730: final-epoch sidecar (separate file); n=223308; sha256=722a3c82ab846986...; path=results_OFFICEV3_k8_seed20260730.final.users.jsonl.gz
- k8 seed 20260731: regular sidecar == final-epoch record (best epoch == final; E2); n=223308; sha256=993136c39d22de48...; path=results_OFFICEV3_k8_seed20260731.users.jsonl.gz
- k8 seed 20260732: final-epoch sidecar (separate file); n=223308; sha256=7a67563d67692806...; path=results_OFFICEV3_k8_seed20260732.final.users.jsonl.gz
