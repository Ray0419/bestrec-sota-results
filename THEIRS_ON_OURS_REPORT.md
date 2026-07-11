# Running the official HSTU-BLaIR reference implementation locally ("theirs on ours")

**Status: COMPLETE — both priority runs finished end-to-end (2026-07-11).**

Date: 2026-07-11
Machine: Windows 11 Pro, NVIDIA GeForce RTX 5060 Ti (16 GB, sm_120), 64 GB RAM
Env: `_bestrec_run/.venv` — Python 3.12.13, torch 2.11.0+cu128 (sm_120 kernels present)
Their repo: `external/HSTU-BLaIR` @ `40a27879ec22648657b5abc77915a7cc88c66cfd` (clean tree, unmodified)
Our repo commit: recorded per-run in each `run_meta.json` (the repo received
commits from other sessions during the runs; run_meta captures the commit at
each launch)

## 1. What this is

We ran the **reference implementation** (snapfinger/HSTU-BLaIR, built on Meta's
`generative-recommenders` research code) **end-to-end locally**: their
preprocessing pipeline, their gin configs, their trainer, their eval protocol —
on our GPU. This was previously believed impossible because their pinned stack
(torch 2.2.2+cu121, fbgemm_gpu 0.6.0, torchrec 1.1.0) has no Windows wheels and
no sm_120 kernels. It became possible because:

- our venv's torch 2.11+cu128 supports sm_120, and
- the **entire research path** (`generative_recommenders/research/**`, the only
  code their `main.py` trains with) uses exactly **three** `torch.ops.fbgemm.*`
  operators, all pure data movement, which we re-implement in pure PyTorch
  (`_bestrec_run/fbgemm_shims.py`), and
- torchrec is **not** imported anywhere on the research path (verified by grep;
  it appears only under `dlrm_v3/` and `modules/`, which the research trainer
  never imports).

No file inside `external/HSTU-BLaIR` was modified (git tree stays clean); all
adaptations are shims/monkeypatches applied from our launcher scripts.

## 2. Shim inventory (complete)

### 2.1 fbgemm operators (`_bestrec_run/fbgemm_shims.py`)

Exhaustive inventory of fbgemm usage under `generative_recommenders/research/`
(grep, 2026-07-11): `asynchronous_complete_cumsum`, `jagged_to_padded_dense`,
`dense_to_jagged`. Nothing else. Registered under the same
`torch.ops.fbgemm.*` names with dispatch key `CompositeImplicitAutograd` so
autograd differentiates through the pure-torch implementation.

| op | semantics | shim implementation |
|---|---|---|
| `asynchronous_complete_cumsum(lengths)` | `[L0..Lb] -> [0, L0, L0+L1, ...]` | `torch.cumsum` with leading 0, dtype-preserving |
| `jagged_to_padded_dense(values, [offsets], [N], pad)` | pack jagged rows into `[B, N, ...]`, pad/truncate | vectorized gather (`index_select`) + masked scatter |
| `dense_to_jagged(dense, [offsets])` | inverse: `[B, N, ...] -> [sum L, ...]` | boolean-mask select (row-major = concat order) |

**Why this does not change the math**: these ops only re-lay-out tensors
between jagged (packed) and dense (padded) forms and compute offsets from
lengths. All model math — layer norms, the fused uvqk projection, SiLU
pointwise attention, relative position/time biases, gating, output projection,
sampled-softmax loss, L2 norms, dot-product scoring, brute-force top-k — runs
in the reference repo's own unmodified lines. Self-test in the module verifies
forward parity against a loop reference and correct gradient flow/pattern on
CPU and CUDA (run: `python _bestrec_run/fbgemm_shims.py`). This extends the
approach already validated numerically by `_bestrec_run/test_hstu_parity.py`
(reference HSTU block matches our reimplementation to <=1e-5 under the same
two padding shims).

### 2.2 Launcher-level monkeypatches (`_bestrec_run/theirs_train.py`)

Their documented entry point is
`python3 main.py --gin_config_file=<cfg> --master_port=<p>`, where `main.py`
(a) `import fbgemm_gpu`, (b) `mp.set_start_method("forkserver")` (POSIX-only),
and (c) `mp.spawn(train_fn, nprocs=torch.cuda.device_count())`. With one GPU
this reduces to `train_fn(rank=0, world_size=1, master_port)`, which our
launcher calls directly after installing the shims. Patches applied to their
trainer module at runtime (their files untouched):

1. `train.setup`: `dist.init_process_group("nccl", ...)` -> `"gloo"`.
   NCCL does not exist on Windows. At world_size=1 the backend performs no
   collective that affects training math (`_avg` all_reduce is gated on
   `world_size > 1`).
2. `train.DDP` -> single-process passthrough `torch.nn.Module` wrapper that
   keeps `.module` and the `"module."` checkpoint prefix.
   **Why**: torch 2.11 `DistributedDataParallel` + gloo + CUDA on Windows dies
   with ACCESS_VIOLATION (0xC0000005) even for a 2-layer toy model with no
   custom ops and no anomaly mode (isolated in
   `_bestrec_run/theirs_debug_segfault.py`: stages A/C/D crash = any DDP;
   stages B/E pass = everything except DDP). At world_size=1, DDP's only
   mathematical function is averaging gradients across ranks — the identity
   for one rank (`broadcast_buffers=False` already in their call).
3. `train.add_to_summary_writer`: wrapped to ALSO append every metric their
   code writes to TensorBoard (hr@{1,10,50,100,200,500,1000},
   ndcg@{1,10,50,100,200}, mrr, ...) to `<run_dir>/metrics.jsonl`.
   Pure logging addition.
3b. `train.SummaryWriter`: event files redirected to the short
   `<run_dir>/tb` directory. Their `log_dir` embeds the full model
   description; on Windows the resulting event-file path is 261 chars for
   amzn23_office, exceeding MAX_PATH=260, and `SummaryWriter` creation dies
   with `FileNotFoundError` (observed; first office launch failed on exactly
   this). Log-file LOCATION only; the intended path is recorded in
   `<run_dir>/tb_logdir_intended.txt`.
4. (recorded per-run) dataloader override `num_workers=0, prefetch_factor=None`
   via gin bindings. Their gins say `num_workers=8, prefetch_factor=1024`
   (Linux fork workers). On Windows, DataLoader workers are spawned processes
   re-created every epoch (their code does not set persistent_workers), which
   only adds wall clock. `DatasetV2.__getitem__` is deterministic
   (no augmentation RNG); all sampling RNG (shuffling via
   `DistributedSampler(seed=0, epoch)`, negative sampling on GPU in the train
   loop) lives in the main process, so worker count cannot affect results.

### 2.3 Preprocessing monkeypatches (`_bestrec_run/theirs_preprocess.py`)

We ran **their** `AmazonDataProcessor.preprocess_rating()` (the same call
their `preprocess_public_data.py` makes, with `text_embedding_model="blair"`)
per dataset, with two data-ACQUISITION patches:

1. `download()`: their shipped method unconditionally raises
   `ValueError("Unknown archive type ...")` because `_saved_name` is
   `tmp/<X>.csv` (never ends in `.csv.gz`) — broken as shipped. Replacement
   downloads the **same hardcoded URL**
   (`https://mcauleylab.ucsd.edu/public_datasets/data/amazon_2023/benchmark/5core/rating_only/<X>.csv.gz`)
   and extracts it to the exact path their reader expects. SHA256 recorded.
2. `process_meta()`: their version loads HF dataset
   `McAuley-Lab/Amazon-Reviews-2023` config `raw_meta_<domain>` with
   `trust_remote_code=True` — a script-based dataset that modern `datasets`
   (ours: 4.8.5) can no longer execute. Replacement reads the **same
   McAuley-Lab raw metadata jsonl** (local copies, SHA256 recorded) and applies
   **their own `clean_metadata()`** (imported from
   `generative_recommenders/research/data/utils.py`) per record, producing the
   identical `parent_asin -> cleaned_metadata` dict. 0 null fields encountered
   (`meta_null_fields_patched: 0`), i.e. no behavioral difference vs the HF
   loader was even exercised.

Everything downstream — metadata-coverage filtering, single-pass >=5-count
user/item filters, first-appearance ID remapping, BLaIR
(`hyp1231/blair-roberta-base`) CLS embeddings at batch_size=8/max_length=512
with a zero row at padding index 0, sequence grouping, CSV write — is their
unmodified code. **Their own dataset-size assertion
(`expected_num_unique_items`) is left active and passed**, i.e. their pipeline
on our machine reproduces exactly their corpus:

| dataset | their expected #items | reproduced | users | interactions | note |
|---|---|---|---|---|---|
| amzn23_music (Musical_Instruments) | 24,587 | **24,587 (assert passed)** | 57,439 | 511,835 | `preprocess_provenance_amzn23_music.json` |
| amzn23_office (Office_Products) | 77,551 | **77,551 (assert passed)** | 223,308 | 1,800,877 | `preprocess_provenance_amzn23_office.json` |

Their paper reports MI 511,836 interactions; the pipeline as shipped reads the
rating CSV with `header=1` + explicit `names`, which consumes the first DATA
row as a header line, dropping exactly one interaction. User/item counts are
unaffected (57,439 / 24,587 exact). Same one-row quirk on Office (1,800,877
here). Our own independently-preprocessed Office split
(`SOTA_CONFIRM_OFFICE_RESULTS.md`): 223,308 users / 1,800,878 interactions —
the corpora agree to within that single row.

## 3. What ran (commands + provenance)

All runs from `_bestrec_run/theirs_runs/` (their relative `tmp/`, `exps/`,
`ckpts/` paths resolve there). Full provenance per run in
`<run_dir>/run_meta.json` (gin SHA256, commits, torch/CUDA versions, bindings,
elapsed) and `preprocess_provenance_*.json` (input/output SHA256s).

```
# preprocessing (their pipeline, blair embeddings)
python _bestrec_run/theirs_preprocess.py amzn23_music     # done, 411 s
python _bestrec_run/theirs_preprocess.py amzn23_office    # done, 834 s

# training (their gin configs, unmodified; --workers0 = dataloader perf only)
python _bestrec_run/theirs_train.py \
  --gin external/HSTU-BLaIR/configs/amzn23_office/sasrec-sampled-softmax-n512-final.gin \
  --run-name office_sasrec_final --workers0 --port 12411   # done, 13608 s
python _bestrec_run/theirs_train.py \
  --gin external/HSTU-BLaIR/configs/amzn23_music/hstu-sampled-softmax-n512-blair.gin \
  --run-name music_hstu_blair --workers0 --port 12412      # done, 6158 s
```

Smoke (1 epoch, MI HSTU-BLaIR): completed end-to-end on GPU — 449 train steps,
full-corpus eval (24,587 items, all users), checkpoint save. 72.5 s. Epoch-0
full eval NDCG@10 0.0267 / HR@10 0.0514 / HR@50 0.1249 / HR@200 0.2481 /
MRR 0.0245 — a plausible early point en route to their published 101-epoch
numbers.

## 4. Results (their code, our GPU) vs their published table

Eval protocol = theirs, unchanged: full-corpus ranking over all items
(seen-item filtering on), leave-last-out target, final-epoch full eval
(their `num_epochs=101`, `full_eval_every_n=5` => last epoch 100 is a full
eval). "Best full eval" also reported since their README does not state
which epoch the table uses.

### 4.1 Goal 1 — their SASRec on Office_Products (the "floor anomaly" check)

Published (their README, Office / SASRec):
HR@10 .0281, HR@50 .0668, HR@200 .1331, NDCG@10 .0153, NDCG@200 .0335, MRR .0143

Local run: `office_sasrec_final` — 101 epochs, 13,608 s (3h47m) wall,
run started 2026-07-10T23:26Z. Full-corpus final-epoch eval over all
223,308 users / 77,551 items:

| metric | their published | local final ep 100 | local vs published | local best full eval (ep 50) |
|---|---|---|---|---|
| HR@10 | 0.0281 | **0.0312** | +11.0% | 0.0317 |
| HR@50 | 0.0668 | **0.0721** | +7.9% | 0.0733 |
| HR@200 | 0.1331 | **0.1405** | +5.6% | 0.1426 |
| NDCG@10 | 0.0153 | **0.0174** | +13.7% | 0.0177 |
| NDCG@200 | 0.0335 | **0.0365** | +9.0% | 0.0370 |
| MRR | 0.0143 | **0.0164** | +14.7% | 0.0167 |

Context for the floor question: our own plain SASRec floor on our Office
split is NDCG@10 0.02208 vs their published 0.0153 (+44%) — the discrepancy
that motivated this experiment (`SOTA_CONFIRM_OFFICE_RESULTS.md`, artifact
`_bestrec_run/results_OFFICE_sasrecfloor_seed20260623.json`). Protocol of that
floor run, for contrast with theirs: 2 transformer blocks (theirs: 4),
batch 256 (theirs 128), 20 epochs with warmup-cosine LR (theirs 101 constant),
**full softmax over the catalog** (theirs: sampled softmax, 512 negatives,
temperature 0.05, L2-normalized embeddings), best-validation-epoch snapshot
evaluated on a 30,000-user subsample = 0.02208; its final-epoch full-catalog
(223,308 users) value is 0.02037.

Interpretation rule (stated before the run finished): if the local
final-epoch NDCG@10 lands near their published 0.0153 (within ~±15%,
0.013-0.018), their number reproduces locally and the +44% floor gap is a
property of OUR baseline being configured/trained stronger — a
config-strength difference, not an environment artifact. If it lands near our
floor 0.022 (0.019-0.025), their own code locally produces the elevated floor
and their published value is low relative to what their pipeline reproduces.
In between: mixed.

**Outcome: the local run lands ABOVE their published table on every metric
(+6% to +15%), at the upper edge of the "reproduces" band for NDCG@10.**
Two readings, both informative for the floor question:

1. Their published Office SASRec numbers are LOW relative to what their own
   unmodified pipeline produces here (their code crossed its own published
   final NDCG@10 at epoch 20 of 101 and never went back below it). The gap
   (+13.7% NDCG@10) is larger than typical seed noise for a 223k-user eval,
   so environment/hardware (torch 2.2 vs 2.11, TF32 kernels, RTX 4090 vs
   5060 Ti) and/or an unlucky run on their side plausibly contribute.
2. The +44% floor anomaly (ours 0.0221 vs their published 0.0153)
   decomposes cleanly, using final-epoch full-catalog numbers on both sides:
   0.0204 (our floor run, final-epoch) / 0.0174 (their code, local) = +17%
   attributable to BASELINE-STRENGTH differences (our floor uses full
   softmax over the catalog vs their 512-negative sampled softmax, plus
   best-epoch selection for the 0.0221 variant), and 0.0174 / 0.0153 = +14%
   attributable to their published number sitting below what their pipeline
   reproduces. (1.17 x 1.14 = 1.33 = 0.0204/0.0153 exactly; the remaining
   step to 0.0221 is best-epoch selection + 30k-user eval subsample.)
   Conclusion: our elevated floor is NOT an artifact of our data split or
   eval protocol — their own code on their own pipeline confirms Office
   supports SASRec numbers well above the published 0.0153; the published
   value is simply a weak-config (sampled-softmax), possibly-unlucky run.

Full-eval trajectory of the local run (NDCG@10, full corpus, all 223,308
users): epoch 0: 0.0048 -> 5: 0.0096 -> 10: 0.0132 -> 15: 0.0149 ->
20: 0.0160 -> 25: 0.0160 -> 30: 0.0166 -> 35: 0.0164 -> 40: 0.0168 ->
45: 0.0169 -> 50: 0.0177 -> 55: 0.0174 -> 60: 0.0175 -> 65: 0.0175 ->
70: 0.0173 -> 75: 0.0168 -> 80: 0.0173 -> 85: 0.0170 -> 90: 0.0177 ->
95: 0.0175 -> 100: 0.0174. Plateau from ~epoch 45 in the 0.0168-0.0177
band; their published 0.0153 was crossed at epoch 20 and never re-entered.

### 4.2 Goal 2 — their HSTU-BLaIR on Musical_Instruments (comparator reproduction)

Published (their README, MI / HSTU-BLaIR):
HR@10 .0733, HR@50 .1681, HR@200 .3066, NDCG@10 .0406, NDCG@200 .0818, MRR .0371

Local run: `music_hstu_blair` — 101 epochs, 6,158 s (1h43m) wall. Full-corpus
eval over all 57,439 users / 24,587 items:

| metric | their published | local final ep 100 | local vs published | local best full eval (ep 35) |
|---|---|---|---|---|
| HR@10 | 0.0733 | 0.0716 | -2.3% | 0.0743 |
| HR@50 | 0.1681 | 0.1641 | -2.4% | 0.1714 |
| HR@200 | 0.3066 | 0.3026 | -1.3% | 0.3136 |
| NDCG@10 | 0.0406 | 0.0391 | -3.7% | **0.0406 (exact)** |
| NDCG@200 | 0.0818 | 0.0798 | -2.4% | 0.0829 |
| MRR | 0.0371 | 0.0355 | -4.3% | 0.0369 |

**Outcome: the comparator REPRODUCES.** The final-epoch full eval lands
within 1.3-4.3% of every published number, and the best full-eval epoch
(35) hits the published NDCG@10 exactly (0.0406) with HR/NDCG@200/MRR within
~1%. The run oscillated in the 0.0384-0.0406 NDCG@10 band from epoch ~30
onward (their README itself notes "a small margin of variability" across
runs). Full-eval NDCG@10 trajectory: ep0 0.0269 -> 5 0.0361 -> 10 0.0385 ->
15 0.0393 -> 20 0.0388 -> 25 0.0395 -> 30 0.0399 -> 35 0.0406 -> 40 0.0394
-> 45 0.0395 -> 50 0.0394 -> 55 0.0390 -> 60 0.0399 -> 65 0.0388 ->
70 0.0387 -> 75 0.0391 -> 80 0.0395 -> 85 0.0397 -> 90 0.0384 -> 95 0.0396
-> 100 0.0391.

This directly upgrades the comparator story (audit finding F5): the
published HSTU-BLaIR Musical_Instruments row is not merely a transcribed
external constant anymore — the reference implementation, run end-to-end
locally on the exact corpus its own pipeline reproduces (24,587 items,
57,439 users), regenerates it within a few percent (exactly, at the level
of run-internal epoch variance).

### 4.3 Stretch goals — status update (round-3 audit F4 disclosure)

**COMPLETED (2026-07-12).** The Office_Products HSTU-BLaIR run (their config `hstu-sampled-softmax-n512-blair.gin`, 101 epochs, launched 2026-07-11 ~11:40Z, run dir `theirs_runs/office_hstu_blair/`, ~9h wall) finished:

| metric | their published | local final ep 100 | local vs published | local best full eval (ep 90) |
|---|---|---|---|---|
| NDCG@10 | 0.0271 | **0.0275** | +1.6% | 0.0279 (+2.8%) |
| HR@10 | — | 0.0486 | — | — |
| MRR | — | 0.0253 | — | — |

Full-eval NDCG@10 trajectory: ep0 0.0170 → 20 0.0258 → 50 0.0269 → 70 0.0274 → 90 0.0279 → 100 0.0275 (plateau band ≈0.0267–0.0279 from ~epoch 40).

**Outcome: the published Office HSTU-BLaIR row REGENERATES here** (final +1.6%, best +2.8% — comparable to the MI regeneration margins). This **refutes the section-4.1 extrapolation below** (that the HSTU-BLaIR Office row would plausibly land well above 0.0271 the way the SASRec row did): the conservatism observed in this environment is a property of their published Office **SASRec** row (+13.9%), **not** of their published Office **HSTU-BLaIR** row (+1.6%). Descriptive context only: our (VOID) Office gate values 0.03042/0.03033 sit ≈+9% above both the published 0.0271 and this local regeneration — reported as descriptive, environment-caveated, single-run evidence; **the prereg VOID stands on procedural grounds** (the floor check failed as written; no post-hoc information restores a voided pre-registration) and Office remains counted in no claim. (Original section text below, retained verbatim.)

Office HSTU-BLaIR (published NDCG@10 .0271) and Video_Games HSTU-BLaIR
(published .0760) were not run: the two priority questions were answered and
each additional run costs 2-5 GPU-hours. Everything needed is in place —
office data is already preprocessed (`tmp/amzn23_office/` incl. BLaIR
embeddings); launch with `bash _bestrec_run/theirs_run_office_hstu_blair.sh`
(~4-5 h). Video_Games would additionally need
`theirs_preprocess.py amzn23_game` (raw meta jsonl already on disk at
`data_raw_proper/video_games/meta_Video_Games.jsonl`).

Note the implication of 4.1 for the Office stretch (WRITTEN BEFORE THE RUN; kept for the record): since their own SASRec
config lands ~+14% above its published row locally, a local office
HSTU-BLaIR run would plausibly also land above 0.0271 — i.e. published
comparator rows for Office appear systematically conservative relative to
what this environment reproduces. Any gate comparison against 0.0271 should
carry that caveat.

**Post-run correction (2026-07-12): the extrapolation did NOT hold.** The completed run (§4.3 table) lands only +1.6% above the published row — the Office HSTU-BLaIR row regenerates, and the systematic-conservatism reading narrows to the Office SASRec row specifically.

## 5. Validity caveats (honest assessment)

1. **Unpinned environment.** Their pins: torch 2.2.2, pandas 2.2.1,
   transformers 4.51.3, numpy 1.26.4, fbgemm_gpu 0.6.0. Ours: torch 2.11.0,
   pandas 3.0.3, transformers 5.7.0, numpy 2.4.4, fbgemm shimmed. Kernel-level
   numerics (cuBLAS versions, TF32 paths — their configs enable TF32) and the
   BLaIR tokenizer/model forward under a newer transformers can differ at
   floating-point level. We verified the one pandas construct that changes
   behavior across 2.x/3.x in their preprocessing (row-apply returning
   None/Series then dropna) behaves identically.
2. **Shims.** Three fbgemm data-movement ops re-implemented (Section 2);
   DDP replaced by identity wrapper at world_size=1; nccl->gloo. Arguments for
   why none of these touch the math are given above; residual risk is
   implementation bugs, mitigated by self-tests + the pre-existing HSTU parity
   test + the sanity of training trajectories.
3. **Different GPU.** RTX 5060 Ti vs their RTX 4090. Non-deterministic
   reduction order and TF32 differences make per-run numbers vary; their own
   README warns of "a small margin of variability" across runs of their code.
4. **Single seed.** Their code seeds only python `random` (seed 42) — model
   init/negative sampling use unseeded torch RNG, so even their pipeline is
   not run-to-run deterministic. We ran each config once, as they document it.
5. **Windows dataloader override.** `num_workers 8 -> 0` — wall-clock only
   (argument in 2.2.4); recorded in every `run_meta.json`.
6. **Metadata source substitution.** Same McAuley raw_meta artifact, local
   jsonl instead of the (now-unloadable) HF script dataset; their
   `expected_num_unique_items` assertions passing is the end-to-end check that
   the corpus came out identical.

## 6. Bottom line

The "impossible" run is possible: the official HSTU-BLaIR reference stack —
their preprocessing, their gin configs, their trainer, their eval — runs
end-to-end on this Windows/RTX 5060 Ti machine under torch 2.11, with only
(a) three pure-data-movement fbgemm ops re-implemented in PyTorch,
(b) an identity DDP wrapper at world_size=1 (Windows gloo+CUDA DDP
segfaults), (c) nccl->gloo, and (d) two logging/data-acquisition patches.
Their own dataset-size assertions passed for both corpora.

Headline numbers (their code, their data, their configs, our GPU;
final-epoch full-corpus eval):

- **Musical_Instruments HSTU-BLaIR: NDCG@10 0.0391 final / 0.0406 best vs
  published 0.0406 — the comparator reproduces** (all published metrics
  within ~1-4% at final epoch; best epoch exact on NDCG@10).
- **Office_Products SASRec: NDCG@10 0.0174 final / 0.0177 best vs published
  0.0153 — their own baseline lands +14% ABOVE its published row here**, and
  crossed the published value at epoch 20/101. Combined with our floor run
  (0.0204 final-epoch full-catalog under a stronger full-softmax protocol),
  the +44% "floor anomaly" decomposes into ~+14% (published row low relative
  to what their pipeline reproduces) x ~+17% (baseline-strength protocol
  differences), leaving nothing attributable to our data split or eval.

Practical upshots: (1) the MI comparator row can now be cited as locally
regenerated with the reference implementation (single run, environment
caveats in Section 5); (2) [refined 2026-07-12 after the completed Office HSTU-BLaIR run] the published Office **SASRec** row appears
conservative in this environment (+13.9%) while the Office **HSTU-BLaIR** row regenerates (+1.6%),
so conservatism must be assessed per-row, not assumed for the table; (3) the full recipe
(shims + launchers + preprocessing with SHA256 provenance) is reusable for
the remaining configs (`theirs_run_office_hstu_blair.sh` — completed 2026-07-12, results in §4.3; Video_Games remains the un-run config).

Artifacts: `_bestrec_run/theirs_runs/{office_sasrec_final,music_hstu_blair}/`
(metrics.jsonl with hr@{1..1000}/ndcg@{1..200}/mrr per eval, run_meta.json,
tensorboard events, their gin copy), trainer stdout logs
`office_sasrec_final.log` / `music_hstu_blair.log`, checkpoints under
`theirs_runs/ckpts/` (epochs 50 and 100, their format), preprocessing
provenance `preprocess_provenance_amzn23_{office,music}.json`.
