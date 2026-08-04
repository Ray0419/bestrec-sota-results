# Pinned-environment parity: torch 2.2.2 + fbgemm_gpu 0.6.0 (the comparator's pins) vs torch 2.11 + our shims

Date: 2026-07-11
Test: `_bestrec_run/test_pinned_env_parity.py` (one file, two modes; three legs below)
Reference tree: `external/HSTU-BLaIR` @ `40a27879ec22648657b5abc77915a7cc88c66cfd`, **unmodified**
Hardware: one physical machine, Intel Core Ultra 7 265K; **CPU only** (GPU never touched:
`CUDA_VISIBLE_DEVICES=-1` set before torch import in every process; `torch.cuda.is_available()`
asserted False; single-threaded: OMP/MKL/torch threads = 1 in every leg)

## 1. The objection this addresses, and the verdict

`THEIRS_ON_OURS_REPORT.md` documents running the HSTU-BLaIR reference stack locally under
torch 2.11.0+cu128 with three pure-PyTorch re-implementations of the fbgemm operators used by
its research path (`_bestrec_run/fbgemm_shims.py`). Remaining objection: **"your shims and your
torch 2.11 are not the pinned binaries (torch 2.2.2 + fbgemm_gpu 0.6.0)."**

We installed the pinned versions in their CPU flavor (they publish no Windows and no sm_120
builds, but they do publish CPU builds of the exact pinned versions) in WSL and compared against
them directly. Verdict, on CPU:

- **Shim-vs-pinned-binary is closed.** On identical inputs, under the pinned torch 2.2.2 itself,
  our three shims are **bit-exact (max abs diff exactly 0.0)** against the real
  `fbgemm-gpu(-cpu)==0.6.0` operators — forward outputs **and** gradients — on every case the
  pinned binary accepts (23/26 forward cases, 5/5 gradient cases), including every
  shape/dtype/layout the research path actually produces. The reference HSTU block run
  end-to-end under {torch 2.2.2 + real fbgemm 0.6.0} vs {torch 2.2.2 + shims} is **bit-exact at
  every stage**.
- **torch-2.2.2-vs-2.11 numerics drift is bounded, small, and quantified.** The reference repo's
  own research HSTU block (unmodified code), identical weights and inputs, pinned stack (WSL,
  torch 2.2.2+cpu + real fbgemm 0.6.0) vs paper stack (Windows, torch 2.11 + shims):
  **max abs diff 4.77e-07 per stage, 2.38e-07 end-to-end** (fp32; gate 1e-5). The op replay
  across the same pair is exactly 0.0, so all of that drift is torch/platform kernel rounding
  (layer norm, matmul, einsum), none of it is the shims.
- **What remains open** (Section 7): the pinned stack's **GPU (cu121) kernel numerics** — no
  sm_80/sm_89 GPU here, and the resident sm_120 GPU is excluded by constraint and unsupported by
  the pinned binaries anyway. That residual is exactly what renting a compatible GPU would close.
  **Single-run training-level equivalence is NOT claimed** here or anywhere.

## 2. Environments (exact)

### 2.1 Pinned environment (WSL2 Ubuntu 20.04, glibc 2.31, fresh venv `~/pinned_parity_env`)

Python `3.11.15` (uv-managed CPython; torch 2.2.2 supports 3.8-3.11). Full `uv pip freeze`
(also at `_bestrec_run/theirs_runs/tmp/pinned_parity/pinned_pip_freeze.txt`):

```
fbgemm-gpu-cpu==0.6.0        <- pinned fbgemm version, official CPU build (PyPI)
filelock==3.29.0
fsspec==2026.4.0
jinja2==3.1.6
markupsafe==3.0.3
mpmath==1.3.0
networkx==3.6.1
numpy==1.26.4                <- their pinned numpy
sympy==1.14.0
torch==2.2.2+cpu             <- pinned torch, CPU build (download.pytorch.org/whl/cpu)
typing-extensions==4.15.0
```

Install provenance: `pinned_parity/setup_pinned_env.{sh,log}` (same scratch dir). First-attempt
installs succeeded: `torch==2.2.2 --index-url https://download.pytorch.org/whl/cpu`,
`fbgemm-gpu-cpu==0.6.0` from PyPI (`--no-deps`, torch already pinned), `numpy==1.26.4`.
Import smoke test: all three `torch.ops.fbgemm.*` ops present and functional.

### 2.2 Paper environment (Windows 11, `_bestrec_run/.venv` — the env that produced the comparator runs)

```
Python 3.12.13 [MSC v.1944 64 bit (AMD64)]
torch==2.11.0+cu128   numpy==2.4.4   (fbgemm-gpu: not installed -> shims)
```

## 3. Methodology

Same file, `--mode pinned` / `--mode shimmed`; inputs are generated once (fixed seeds) in the
pinned environment, saved to `.pt`, and **replayed byte-identically** everywhere else — no
cross-version RNG assumption (Section 6.2 shows that assumption would actually be wrong).

| leg | env | fbgemm impl | role |
|---|---|---|---|
| 1 | WSL, torch 2.2.2+cpu | **REAL fbgemm-gpu-cpu 0.6.0** | generate cases; run real ops (+grads) and the reference block; save inputs+outputs. Also compares real ops vs shim *functions* in the same process (same torch, same platform -> isolates shim-vs-binary exactly) |
| 2 | WSL, torch 2.2.2+cpu | shims (via `torch.library`) | replay: shim-vs-real with torch AND platform held fixed, through the same dispatch path the training runs used |
| 3 | Windows, torch 2.11.0+cu128 (CPU-only) | shims | replay: total drift of the paper stack = shims + torch version + platform/BLAS |

**Op-level cases (26 forward + 5 gradient)** — coverage axes: batch sizes 1/7/64; max lengths
1/50/260; rows of length 0; truncation (row longer than N) and padding; values fp32/fp64/int64;
offsets int32/int64; 2-D and 3-D jagged values (3-D/4-D dense); explicit `total_L`; nonzero,
fractional and negative padding values. Gradients: sum-of-squares loss through
`jagged_to_padded_dense` and `dense_to_jagged`, input grads compared (plus loss scalars,
informational). Cases are tagged **in-contract** when their shape/dtype/layout can actually be
produced by the research path, per this call-site inventory (grep of
`generative_recommenders/research/**`, 2026-07-11 — the complete list):
`hstu.py` 198/201/218/393/396/408/535 (j2pd, fp32 2-D values, pad 0.0), 214/405/524 (d2j, fp32
3-D dense), 703 (cumsum); `candidate_index.py` 87-95 (cumsum; j2pd on int64 ids `[total,1]` and
fp32 embeddings, pad 0); `sampled_softmax.py` 123-187 and `autoregressive_losses.py` 433-452,
529-552 (cumsum; d2j on fp32 3-D dense — ids/weights are `.unsqueeze(-1)`d and ids are cast
`.float()` before d2j); `utils.py` 100-128 (cumsum; j2pd/d2j fp32). So: j2pd sees fp32 2-D and
int64 `[total,1]` values with pad 0; d2j sees fp32 3-D dense with lengths <= N; cumsum sees 1-D
int lengths. Everything else we test is a superset.

**Block-level**: the reference repo's own `SequentialTransductionUnitJagged` +
`RelativePositionalBias` + `_hstu_attention_maybe_from_cache` (imported from the unmodified
tree), the published pointwise path (`linear_config="uvqk"`, `linear_activation="silu"`,
`normalization="rel_bias"`, `concat_ua=False`, dropout 0, eval), same construction as the
pre-existing `_bestrec_run/test_hstu_parity.py` but on **variable-length jagged batches** so the
fbgemm ops do real padding/unpadding work. Two configs: D=32/H=2/B=4/N=8, lengths `[8,3,6,1]`;
D=64/H=4/B=7/N=50, lengths `[50,3,0,27,50,1,13]` (includes a zero-length row and full-length
rows). Weights are seeded in leg 1 and the exact `state_dict` tensors are saved and reloaded in
legs 2/3; inputs likewise. Compared per stage (input layer norm; fused uvqk+silu split u/v/q/k;
pointwise silu attention incl. j2pd/d2j round trip; attn norm x u gate; output proj + residual)
and end-to-end via the reference's own `forward()`, without and with the relative-position-bias
branch. In-env sanity (staged pipeline == `forward()` bitwise) held in every leg.

## 4. Results

### 4.1 Op level, forward (26 cases): every comparable case exactly 0.0

Identical numbers in all three comparisons — leg-1 in-process real-vs-shim-fn, leg-2 same-torch
replay, leg-3 cross-torch replay:

| group | cases | result |
|---|---|---|
| `asynchronous_complete_cumsum` (B=1/7/64; int32/int64; zeros; large) | 8 | **all 0.0** (dtype preserved) |
| `jagged_to_padded_dense` (incl. truncation row 73>N=50 and 390>260, empty rows, pads -1.5/-2.25/+1.5, fp32/fp64, int64 ids `[total,1]`, int32/int64 offsets, B/N up to 64/260) | 8 of 10 comparable | **all comparable 0.0**; 2 rejected by the pinned binary (below) |
| `dense_to_jagged` (fp32/fp64/int64 dense, empty rows, explicit `total_L`, B/N up to 64/260) | 7 of 8 comparable | **all comparable 0.0**; 1 rejected by the pinned binary (below) |

All 15 in-contract cases ran on both sides and are exactly 0.0 (bit-exact, dtypes equal).
The pinned CPU binary **rejected 3 beyond-contract layouts** (recorded, not failures):
3-D jagged values `[total,4,3]` for j2pd (`RuntimeError: inner_dense_size, 3 !=
x_values.size(-1), 12`) and 4-D dense for d2j with a single offsets tensor
(`RuntimeError: x_offsets.size(), 1 != NUM_JAGGED_DIM, 2`). fbgemm 0.6.0 requires the inner
dims flattened; the research path always passes flattened 2-D values / 3-D dense (inventory
above), so these layouts are unreachable in their code. The shims accept them (strict superset);
no comparison output exists for them.

### 4.2 Op level, gradients (5 cases): exactly 0.0, including under truncation

| case | grad max abs diff | loss abs diff |
|---|---|---|
| j2pd fp32 (mixed lengths, padding) | **0.0** | 0.0 |
| j2pd fp64 | **0.0** | 0.0 |
| j2pd fp32 with truncated row (73 > N=50) | **0.0** | 0.0 |
| d2j fp32 | **0.0** | 0.0 |
| d2j fp64 | **0.0** | 0.0 |

Identical in legs 1, 2 and 3. The pinned binary's autograd zeroes gradients of truncated
elements exactly as the shims' autograd does. (Loss scalars matching to the bit also means the
single-threaded sum reduction order matched across torch 2.2.2/2.11 here — informational.)

### 4.3 Block level, same torch (leg 2 vs leg 1): shims are bit-exact in situ

{torch 2.2.2 + real fbgemm 0.6.0} vs {torch 2.2.2 + shims}, identical weights+inputs:
**every stage and both end-to-end outputs of both configs: max abs diff exactly 0.0** (20/20
comparisons, plus offsets via the cumsum op: 0.0). Under the pinned torch itself, replacing the
pinned fbgemm binary by our shims changes **no bit** of the reference block's output.

### 4.4 Block level, cross stack (leg 3 vs leg 1): torch 2.2.2 -> 2.11 drift bound

{WSL torch 2.2.2+cpu + real fbgemm 0.6.0} vs {Windows torch 2.11.0 + shims}, identical
weights+inputs, fp32, single thread (gate 1e-5):

| stage | blkA D32 H2 B4 N8 | blkB D64 H4 B7 N50 |
|---|---|---|
| s1 input layer norm | 2.384e-07 | 4.768e-07 |
| s2 uvqk+silu split u / v / q / k | 7.5e-09 / 1.1e-08 / 1.5e-08 / 3.0e-08 | 7.5e-08 / 6.0e-08 / 6.0e-08 / 4.5e-08 |
| s3 pointwise silu attention (j2pd/d2j inside) | 5.457e-11 | 1.746e-10 |
| s4 attn norm x u gate | 4.191e-09 | 2.980e-08 |
| s5 out proj + residual | 2.384e-07 | 2.384e-07 |
| end-to-end forward (no rab) | **2.384e-07** | **2.384e-07** |
| end-to-end forward (with rel. pos. bias) | 1.490e-08 | **2.384e-07** |

Max over everything: **4.768e-07** (a layer-norm stage), i.e. ~2-4 float32 ulps at these
magnitudes — ordinary kernel-rounding drift across torch versions/platforms/BLAS backends, and
orders of magnitude below the 1e-5 gate. Since 4.1-4.3 pin the ops at exactly 0.0, all of this
is torch-version/platform numerics, none of it the shims.

### 4.5 Negative control: the harness detects what it must

`pinned_parity/negative_control.py`: replaying one saved case unmodified reproduces the pinned
output bit-exactly; perturbing the padding value (0.0 -> -1.0) reports 1.0; shortening the last
row by one element reports 2.14; bumping **one input element by one ulp** reports 1.19e-07.
PASS — the exact-0.0 gate resolves single-ulp discrepancies; the zeros above are not vacuous.

## 5. Reproduction

```
# leg 1 (writes pinned_ops.pt / pinned_block.pt; must run first)
wsl.exe -e /home/ray/pinned_parity_env/bin/python \
    /mnt/c/Users/rayxc/Documents/R/_bestrec_run/test_pinned_env_parity.py --mode pinned
# leg 2
wsl.exe -e /home/ray/pinned_parity_env/bin/python \
    /mnt/c/Users/rayxc/Documents/R/_bestrec_run/test_pinned_env_parity.py --mode shimmed
# leg 3
_bestrec_run/.venv/Scripts/python _bestrec_run/test_pinned_env_parity.py --mode shimmed
```

All three exit 0 (gates: ops/grads exactly 0.0; block exactly 0.0 same-stack, <=1e-5
cross-stack). Artifacts (gitignored scratch,
`_bestrec_run/theirs_runs/tmp/pinned_parity/`): `setup_pinned_env.{sh,log}`,
`pinned_pip_freeze.txt`, `pinned_python_version.txt`, `pinned_ops.pt`, `pinned_block.pt`,
`leg1_pinned.log`, `leg2_wsl_shims.log`, `leg3_win_t211_shims.log`,
`replay_results_Linux-torch2.2.2pcpu-shims.json`,
`replay_results_Windows-torch2.11.0pcu128-shims.json`, `negative_control.{py,log}`.
WSL env is reproducible from scratch via `setup_pinned_env.sh` (uv; ~2 minutes).

**Artifact status (round-3 audit F3):** the scratch files above are **reproducible intermediates** — the source of truth is `_bestrec_run/test_pinned_env_parity.py` plus the three-leg commands in section 3. They are additionally archived as the release asset `pinned_env_parity_artifacts.zip` on `v0.9-audit-evidence` (SHA256 `f469d3d849fe2049c8cf059b880eebfd6032d9c6c58d99b03a13c052159fec4b`), and the key outputs are hash-manifested in `RELEASE_MANIFEST.json` under `pinned_parity_artifacts` (verified by `update_release_manifest.py --verify`, which the strict rebuild wrapper runs).

## 6. Findings and notes

1. **Pinned-binary layout restrictions** (Section 4.1): fbgemm 0.6.0 CPU rejects unflattened
   inner dims (3-D jagged values / 4-D dense with one offsets tensor). Unreachable from the
   research path; shims are a strict superset there.
2. **Cross-version RNG is NOT bit-stable** (informational, not gated): regenerating the block's
   seeded init weights and inputs under torch 2.11/Windows instead of 2.2.2/Linux gives values
   differing by up to 2.4e-07 (same distribution, last-bits rounding differences in the normal
   transform). This validates the save/replay design — and means any "same seed => same run"
   argument across these torch versions would be unsound even on CPU; we never make one.
3. **Windows CUDA hygiene**: on torch 2.11.0+cu128/Windows, `CUDA_VISIBLE_DEVICES=""` leaves
   `torch.cuda.is_available()` True (with 0 devices); the test sets `"-1"`, which fully hides
   the GPU, and asserts `is_available()` is False in every leg.
4. Both replay legs also re-derive the block's offsets through the (shimmed) cumsum op and
   match the pinned offsets exactly; in-env staged-vs-`forward()` sanity is bitwise True in all
   legs.

## 7. Honest scope — what this does and does not establish

**Established (CPU, this machine):**
- The three shims are functionally identical — bit-exact, forward and backward — to the pinned
  `fbgemm_gpu==0.6.0` binaries' CPU operators, verified under the pinned `torch==2.2.2` itself,
  across all research-path-reachable input classes plus supersets (edge rows, truncation,
  fp64, int64, both offset dtypes).
- The unmodified reference HSTU block is bit-identical under {pinned torch + pinned fbgemm} vs
  {pinned torch + shims}, and drifts by at most 4.8e-07 (fp32, per application) under
  {torch 2.11 + shims} — the "not the pinned torch" delta for the exact block math, bounded.

**Not established (stated plainly):**
- **GPU kernel numerics of the pinned stack.** The pinned comparator's published numbers came
  from torch 2.2.2+cu121 CUDA kernels on an RTX 4090 (sm_89). This machine's GPU is sm_120
  (unsupported by those binaries — the original reason for this whole exercise) and was
  off-limits during this work. fbgemm-gpu-cpu 0.6.0 is the same pinned release but its CPU
  kernels, not its CUDA kernels. **The residual check a rented sm_80/sm_89 GPU would close is
  exactly this**: rerun leg 1 with `fbgemm-gpu==0.6.0+cu121` on such a GPU (this test file
  would only need its device pinned to cuda).
- **Training-level equivalence.** Nothing here claims a 101-epoch training run under
  {2.11 + shims} equals one under the pinned stack run-for-run. Training amplifies fp32
  rounding chaotically, their own code is not run-to-run deterministic even in place (unseeded
  torch RNG; their README notes cross-run variability), and per-application drift measured here
  (<=4.8e-07) is far below GPU-side nondeterminism within the pinned stack itself. The claim
  that IS supported: op-level substitution is exact, and single-application block numerics drift
  is negligible; remaining differences between environments are of the same nature and scale as
  reordering-induced noise the reference stack already exhibits between its own runs.
- CPU-flavor caveat for the op-parity claim: "bit-exact vs pinned binaries" means the pinned
  version's official CPU build (`fbgemm-gpu-cpu==0.6.0`). The cu121 build compiles different
  (CUDA) kernels for the same ops; for pure data-movement ops the semantics are the same, but we
  did not (cannot, locally) verify its bits.
- One environment axis intentionally differs inside leg comparisons: leg 1/2 run on Linux
  (WSL2)/py3.11 while leg 3 runs on Windows/py3.12 — so the 4.8e-07 bound conflates torch
  version with OS/toolchain/BLAS. That is the conservative direction (it upper-bounds the
  torch-version-only delta at the same order), and leg 2 removes the shim variable from it
  entirely.
