# VOID (audit 2026-07-24): E-B / PREREG_TEXTPERM_V1 is TOMBSTONED.

**Do NOT run any command in this file.** The E-B design is void (pseudoreplication, un-normalized random control, arm/pod aliasing); its execution scripts (`bootstrap_pod.sh`, `make_shards_eb.py`, `run_shard.py`, `eval_final_model.py`, `run_all_pod.sh`) hard-refuse. The shard files under `cloud/shards/` and any `controls/` references are stale (the generator now targets `controls_v2/`). A corrected PREREG_TEXTPERM_V2 in a new code namespace is required before any run. The text below is retained only as the voided original.

---

# Cloud fleet (RunPod) — operator guide

Everything here is launch-ready; the prereg (PREREG_TEXTPERM_V1.md) is
frozen and committed BEFORE any pod runs. Environment heterogeneity is
declared; per-run env is captured in shard ledgers.

## Maintainer steps (account side — never handled by the automation)

1. Create/fund the RunPod account.
2. Provision **8 pods** (4 also works, ~2.2 h): any of RTX 3090 / 4090 /
   A5000, ≥16 GB VRAM, ≥40 GB disk, a PyTorch CUDA template (or plain CUDA
   — bootstrap installs torch if absent). Community/spot is fine: every
   step is skip-if-exists resumable.
3. Hand the automation SSH endpoints (host/port/key) — or a RunPod API key
   via environment variable for programmatic provisioning.

## Per-pod sequence (one command each once SSH works)

```bash
git clone --depth 50 --branch codex/bestrec-sota-results \
  https://github.com/Ray0419/bestrec-sota-results.git /workspace/R
cd /workspace/R && bash cloud/bootstrap_pod.sh          # assets + deps + caches, hash-verified
python cloud/run_shard.py cloud/shards/eb_shard<N>.json # N = 0..7, one per pod
```

Each pod ends by writing `cloud/returns/eb_shard<N>_<host>.tar.gz`
(+SHA256SUMS). The operator pulls those 8 files back (scp), verifies sums,
unpacks into the repo, and runs
`_bestrec_run/adjudicate_textperm_v1.py` — the FIRST reader of any test
value (training used --no-test-eval; the final eval prints no metrics).

## Scope

Shards currently cover PREREG_TEXTPERM_V1 (E-B, 30 pipelines, ≈8.2
GPU-hours; ≈65 min wall on 8 pods). E-G2 stays on the local GPU by design
(mid-campaign; clean single-environment provenance). Later campaigns
(E-C2 etc.) reuse this harness with their own frozen preregs and shard
generators.
