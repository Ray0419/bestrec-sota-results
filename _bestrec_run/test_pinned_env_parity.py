#!/usr/bin/env python
"""Pinned-environment parity test: pinned torch 2.2.2 + fbgemm_gpu 0.6.0 (CPU)
vs our torch 2.11 + pure-PyTorch fbgemm shims.

WHY THIS EXISTS
  The paper's comparator stack (external/HSTU-BLaIR @ 40a27879) pins
  torch==2.2.2 + fbgemm_gpu==0.6.0, which have no sm_120 GPU kernels, so the
  local comparator runs used torch 2.11 + three pure-PyTorch shims
  (_bestrec_run/fbgemm_shims.py) for the only fbgemm ops on the research path.
  Objection to kill: "your shims and your torch 2.11 are not the pinned
  binaries." This test runs the PINNED binaries (CPU flavor: torch 2.2.2+cpu,
  fbgemm-gpu-cpu 0.6.0, numpy 1.26.4, python 3.11 -- installed in WSL) and
  compares, on identical saved inputs:

    (1) OP LEVEL   : real torch.ops.fbgemm.{asynchronous_complete_cumsum,
                     jagged_to_padded_dense, dense_to_jagged} vs our shims,
                     forward outputs AND gradients. Expected: exactly 0.0
                     (these are data-movement ops).
    (2) BLOCK LEVEL: the reference repo's own research HSTU block
                     (SequentialTransductionUnitJagged + RelativePositionalBias
                     + _hstu_attention_maybe_from_cache, all unmodified),
                     fixed weights + fixed jagged inputs, staged + end-to-end.
                     Cross-environment diffs bound torch-2.2.2-vs-2.11 fp32
                     CPU numerics drift for the exact block.

THREE LEGS (same file, two modes)
  leg 1  --mode pinned   in the WSL pinned env (torch 2.2.2+cpu, REAL
                         fbgemm-gpu-cpu 0.6.0). Generates the deterministic
                         test cases, runs the REAL ops (+ grads) and the
                         reference block, saves everything to .pt files.
                         Additionally compares, IN-PROCESS in the pinned env,
                         the real ops against the shim *functions* on the same
                         inputs (same torch, same platform => isolates
                         shim-vs-real-binary exactly).
  leg 2  --mode shimmed  in the SAME WSL pinned env (torch 2.2.2+cpu) but
                         without importing fbgemm_gpu, so the shims register.
                         Replays the saved inputs through the shims: isolates
                         shim-vs-real with torch/platform held fixed,
                         including the torch.library dispatch path.
  leg 3  --mode shimmed  in the paper's Windows env
                         (_bestrec_run/.venv, torch 2.11.0+cu128, CPU only).
                         Replays the same inputs: total drift = shims + torch
                         version + platform/BLAS.

RUN
  # leg 1 (WSL pinned env; must run first -- writes pinned_ops.pt/pinned_block.pt)
  wsl.exe -e /home/ray/pinned_parity_env/bin/python \
      /mnt/c/Users/rayxc/Documents/R/_bestrec_run/test_pinned_env_parity.py --mode pinned
  # leg 2 (same WSL env, shims replay)
  wsl.exe -e /home/ray/pinned_parity_env/bin/python \
      /mnt/c/Users/rayxc/Documents/R/_bestrec_run/test_pinned_env_parity.py --mode shimmed
  # leg 3 (Windows venv, torch 2.11 + shims)
  _bestrec_run/.venv/Scripts/python _bestrec_run/test_pinned_env_parity.py --mode shimmed

CPU ONLY: CUDA_VISIBLE_DEVICES is forced to "" before torch is imported; no
tensor ever leaves the CPU. Single-threaded (OMP/MKL/torch threads = 1) so
reduction order is deterministic within each environment.

CASE COVERAGE (op level; seeds fixed, generated once in leg 1, replayed
byte-identically in legs 2/3): batch sizes 1/7/64; max lengths 1/50/260;
rows of length 0; truncation (row longer than N) and padding; values fp32,
fp64 and int64; lengths/offsets int32 and int64; 2-D and 3-D value tensors
(= 3-D and 4-D dense tensors); explicit total_L; nonzero padding values.
Cases marked contract=True have shapes/dtypes the research path actually
produces (see the call-site inventory in PINNED_ENV_PARITY_REPORT.md);
contract=False cases go beyond it (fp64, extra inner dims, nonzero padding,
int64 dense_to_jagged, truncation). An op ERROR on a beyond-contract case is
recorded as a finding, not a failure; any nonzero DIFF on a case both sides
support is a failure.

GATES
  op forward + grad parity: max abs diff must be exactly 0.0.
  block level, same-stack replay (leg 2): exactly 0.0.
  block level, cross-stack replay (leg 3): <= 1e-5 (fp32; actual value reported).
"""
from __future__ import annotations

import os

# HARD CONSTRAINT: CPU only. Must happen before `import torch`.
# "-1" (not ""): on this Windows torch 2.11 build an empty string still leaves
# torch.cuda.is_available() True (device_count 0); "-1" hides the GPU fully.
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import argparse  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import platform  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

import torch  # noqa: E402
import torch.nn.functional as F  # noqa: E402

torch.set_num_threads(1)

HERE = os.path.dirname(os.path.abspath(__file__))            # _bestrec_run
ROOT = os.path.dirname(HERE)                                 # repo root
SCRATCH = os.path.join(HERE, "theirs_runs", "tmp", "pinned_parity")
OPS_PT = os.path.join(SCRATCH, "pinned_ops.pt")
BLOCK_PT = os.path.join(SCRATCH, "pinned_block.pt")

BLOCK_TOL_CROSS = 1e-5   # fp32 gate for cross-version block drift
SEED_CASES = 20260711

sys.path.insert(0, HERE)                                     # fbgemm_shims
sys.path.insert(0, os.path.join(ROOT, "external", "HSTU-BLaIR"))


# ---------------------------------------------------------------------------
# Environment metadata
# ---------------------------------------------------------------------------

def _git_head(path: str) -> str:
    try:
        git = os.path.join(path, ".git")
        if os.path.isfile(git):  # worktree / submodule pointer
            with open(git) as f:
                git = f.read().split("gitdir:")[1].strip()
            if not os.path.isabs(git):
                git = os.path.join(path, git)
        with open(os.path.join(git, "HEAD")) as f:
            head = f.read().strip()
        if head.startswith("ref:"):
            ref = head.split(None, 1)[1]
            with open(os.path.join(git, ref)) as f:
                return f.read().strip()
        return head
    except Exception:
        return "unknown"


def build_meta(mode: str, fbgemm_impl: str) -> dict:
    return {
        "mode": mode,
        "torch": str(torch.__version__),  # plain str: TorchVersion is not weights_only-safe
        "python": sys.version.replace("\n", " "),
        "platform": platform.platform(),
        "system": platform.system(),
        "fbgemm_impl": fbgemm_impl,
        "num_threads": torch.get_num_threads(),
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES", None),
        "cuda_available": torch.cuda.is_available(),  # must be False
        "repo_commit": _git_head(ROOT),
        "ref_commit": _git_head(os.path.join(ROOT, "external", "HSTU-BLaIR")),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }


# ---------------------------------------------------------------------------
# Tensor comparison
# ---------------------------------------------------------------------------

def tensor_diff(a: torch.Tensor, b: torch.Tensor):
    """-> (max_abs_diff: float, bit_exact: bool, note: str)."""
    notes = []
    if a.dtype != b.dtype:
        notes.append(f"dtype {a.dtype} vs {b.dtype}")
    if tuple(a.shape) != tuple(b.shape):
        notes.append(f"shape {tuple(a.shape)} vs {tuple(b.shape)}")
        return math.inf, False, "; ".join(notes)
    if a.dtype == b.dtype and torch.equal(a, b):
        return 0.0, True, "; ".join(notes)
    if a.numel() == 0:
        return 0.0, True, "; ".join(notes)  # same-shape empty tensors
    d = (a.double() - b.double()).abs().max().item()
    return d, False, "; ".join(notes)


def fmt_diff(d) -> str:
    if d is None:
        return "-"
    if d == 0.0:
        return "0.0"
    if math.isinf(d):
        return "inf"
    return f"{d:.3e}"


# ---------------------------------------------------------------------------
# Op-level test cases (generated in leg 1 only; replayed from disk elsewhere)
# ---------------------------------------------------------------------------

L_MIX_TRUNC_50 = [0, 50, 73, 12, 1, 49, 50]   # N=50: zero, full, TRUNCATED, short
L_MIX_LE_50 = [0, 50, 12, 1, 49, 50, 25]      # N=50: all <= N (d2j contract)


def _rand_lengths(gen, b, hi, force):
    t = torch.randint(0, hi + 1, (b,), generator=gen)
    for i, v in force.items():
        t[i] = v
    return t


def build_op_cases() -> list:
    gen = torch.Generator().manual_seed(SEED_CASES)
    f32, f64, i32, i64 = torch.float32, torch.float64, torch.int32, torch.int64
    cases = []

    # ---- asynchronous_complete_cumsum: 1-D lengths -> offsets --------------
    acc_rand64 = _rand_lengths(gen, 64, 520, {3: 0, 17: 0, 40: 520})
    acc_sets = [
        ("B1_zero", torch.tensor([0])),
        ("B1_one", torch.tensor([7])),
        ("B7_mixed", torch.tensor([3, 0, 260, 5, 1, 0, 50])),
        ("B64_rand", acc_rand64),
    ]
    for nm, lengths in acc_sets:
        for dt, dtn in ((i32, "i32"), (i64, "i64")):
            cases.append(dict(
                name=f"acc_{nm}_{dtn}", op="acc", contract=True,
                lengths=lengths.to(dt).clone(),
            ))

    # ---- jagged_to_padded_dense ---------------------------------------------
    j2pd_rand390 = _rand_lengths(gen, 64, 390, {3: 0, 17: 0, 5: 260, 9: 390})

    def vals_for(lengths, inner, dtype):
        total = int(lengths.sum())
        shape = (total,) + inner
        if dtype in (f32, f64):
            return torch.randn(shape, generator=gen, dtype=dtype)
        return torch.randint(1, 100000, shape, generator=gen, dtype=dtype)

    j2pd_specs = [
        # (name, N, lengths, inner_shape, vdtype, odtype, pad, contract)
        ("B1_N1_trunc_fp32_i32", 1, torch.tensor([3]), (5,), f32, i32, 0.0, True),
        ("B1_N1_empty_fp32_i64_pad", 1, torch.tensor([0]), (5,), f32, i64, -1.5, False),
        ("B7_N50_mix_fp32_i32", 50, torch.tensor(L_MIX_TRUNC_50), (8,), f32, i32, 0.0, True),
        ("B7_N50_mix_fp32_i64_pad", 50, torch.tensor(L_MIX_TRUNC_50), (8,), f32, i64, -2.25, False),
        ("B7_N50_mix_fp64_i32_pad", 50, torch.tensor(L_MIX_TRUNC_50), (8,), f64, i32, -2.25, False),
        ("B7_N50_mix_3dvals_fp32_i32", 50, torch.tensor(L_MIX_TRUNC_50), (4, 3), f32, i32, 0.0, False),
        ("B7_N50_mix_3dvals_fp64_i64_pad", 50, torch.tensor(L_MIX_TRUNC_50), (4, 3), f64, i64, 1.5, False),
        ("B64_N260_rand_fp32_i32", 260, j2pd_rand390, (16,), f32, i32, 0.0, True),
        ("B64_N260_rand_fp64_i64", 260, j2pd_rand390, (16,), f64, i64, 0.0, False),
        ("B7_N50_ids_i64vals_i32", 50, torch.tensor(L_MIX_LE_50), (1,), i64, i32, 0.0, True),
    ]
    for nm, n, lengths, inner, vdt, odt, pad, contract in j2pd_specs:
        off = torch.zeros(lengths.numel() + 1, dtype=torch.int64)
        torch.cumsum(lengths, 0, out=off[1:])
        cases.append(dict(
            name=f"j2pd_{nm}", op="j2pd", contract=contract,
            values=vals_for(lengths, inner, vdt),
            offsets=off.to(odt), max_length=int(n), padding_value=float(pad),
        ))

    # ---- dense_to_jagged (lengths <= N: the research-path contract) --------
    d2j_rand260 = _rand_lengths(gen, 64, 260, {3: 0, 17: 0, 5: 260})

    def dense_for(b, n, inner, dtype):
        shape = (b, n) + inner
        if dtype in (f32, f64):
            return torch.randn(shape, generator=gen, dtype=dtype)
        return torch.randint(1, 100000, shape, generator=gen, dtype=dtype)

    d2j_specs = [
        # (name, N, lengths, inner_shape, vdtype, odtype, pass_total_L, contract)
        ("B1_N1_full_fp32_i32", 1, torch.tensor([1]), (5,), f32, i32, False, True),
        ("B1_N1_empty_fp64_i64", 1, torch.tensor([0]), (5,), f64, i64, False, False),
        ("B7_N50_mix_fp32_i32", 50, torch.tensor(L_MIX_LE_50), (8,), f32, i32, False, True),
        ("B7_N50_mix_fp64_i64_totL", 50, torch.tensor(L_MIX_LE_50), (8,), f64, i64, True, False),
        ("B7_N50_mix_4ddense_fp32_i64", 50, torch.tensor(L_MIX_LE_50), (4, 3), f32, i64, False, False),
        ("B64_N260_rand_fp32_i32", 260, d2j_rand260, (16,), f32, i32, False, True),
        ("B64_N260_rand_fp64_i64", 260, d2j_rand260, (16,), f64, i64, False, False),
        ("B7_N50_i64dense_i32", 50, torch.tensor(L_MIX_LE_50), (1,), i64, i32, False, False),
    ]
    for nm, n, lengths, inner, vdt, odt, tl, contract in d2j_specs:
        off = torch.zeros(lengths.numel() + 1, dtype=torch.int64)
        torch.cumsum(lengths, 0, out=off[1:])
        cases.append(dict(
            name=f"d2j_{nm}", op="d2j", contract=contract,
            dense=dense_for(lengths.numel(), int(n), inner, vdt),
            offsets=off.to(odt),
            total_L=int(lengths.sum()) if tl else None,
        ))
    return cases


def build_grad_cases() -> list:
    gen = torch.Generator().manual_seed(SEED_CASES + 1)
    f32, f64, i32 = torch.float32, torch.float64, torch.int32
    cases = []
    for nm, lengths, dt, contract in [
        ("gr_j2pd_fp32", L_MIX_LE_50, f32, True),
        ("gr_j2pd_fp64", L_MIX_LE_50, f64, False),
        ("gr_j2pd_fp32_trunc", L_MIX_TRUNC_50, f32, False),
    ]:
        lt = torch.tensor(lengths)
        off = torch.zeros(lt.numel() + 1, dtype=torch.int64)
        torch.cumsum(lt, 0, out=off[1:])
        cases.append(dict(
            name=nm, op="j2pd", contract=contract,
            values=torch.randn(int(lt.sum()), 8, generator=gen, dtype=dt),
            offsets=off.to(i32), max_length=50, padding_value=0.0,
        ))
    for nm, dt, contract in [("gr_d2j_fp32", f32, True), ("gr_d2j_fp64", f64, False)]:
        lt = torch.tensor(L_MIX_LE_50)
        off = torch.zeros(lt.numel() + 1, dtype=torch.int64)
        torch.cumsum(lt, 0, out=off[1:])
        cases.append(dict(
            name=nm, op="d2j", contract=contract,
            dense=torch.randn(lt.numel(), 50, 8, generator=gen, dtype=dt),
            offsets=off.to(i32), total_L=None,
        ))
    return cases


# ---------------------------------------------------------------------------
# Op runners. `fns` is either the torch.ops.fbgemm namespace (real ops or
# registered shims) or the shim module's plain python functions.
# ---------------------------------------------------------------------------

class TorchOpsFns:
    """Adapter: run through torch.ops.fbgemm (real fbgemm or registered shims)."""
    name = "torch.ops.fbgemm"

    @staticmethod
    def acc(lengths):
        return torch.ops.fbgemm.asynchronous_complete_cumsum(lengths)

    @staticmethod
    def j2pd(values, offsets, max_length, padding_value):
        return torch.ops.fbgemm.jagged_to_padded_dense(
            values, [offsets], [max_length], padding_value)

    @staticmethod
    def d2j(dense, offsets, total_L=None):
        if total_L is not None:
            return torch.ops.fbgemm.dense_to_jagged(dense, [offsets], total_L)[0]
        return torch.ops.fbgemm.dense_to_jagged(dense, [offsets])[0]


class ShimFns:
    """Adapter: call the shim implementations directly (no op registration),
    usable even when the real fbgemm ops own the torch.ops.fbgemm names."""
    name = "fbgemm_shims functions"

    def __init__(self, shims_module):
        self._m = shims_module

    def acc(self, lengths):
        return self._m._asynchronous_complete_cumsum(lengths)

    def j2pd(self, values, offsets, max_length, padding_value):
        return self._m._jagged_to_padded_dense(
            values, [offsets], [max_length], padding_value)

    def d2j(self, dense, offsets, total_L=None):
        return self._m._dense_to_jagged(dense, [offsets], total_L)[0]


def run_op_case(fns, c):
    """-> (output_tensor | None, error_str | None)"""
    try:
        if c["op"] == "acc":
            return fns.acc(c["lengths"]), None
        if c["op"] == "j2pd":
            return fns.j2pd(c["values"], c["offsets"], c["max_length"],
                            c["padding_value"]), None
        if c["op"] == "d2j":
            return fns.d2j(c["dense"], c["offsets"], c["total_L"]), None
        raise ValueError(c["op"])
    except Exception as e:  # noqa: BLE001 -- record faithfully, keep going
        return None, f"{type(e).__name__}: {e}"


def run_grad_case(fns, c):
    """Sum-of-squares loss through the op; -> (loss, grad, error)."""
    try:
        if c["op"] == "j2pd":
            leaf = c["values"].clone().requires_grad_(True)
            out = fns.j2pd(leaf, c["offsets"], c["max_length"], c["padding_value"])
        else:
            leaf = c["dense"].clone().requires_grad_(True)
            out = fns.d2j(leaf, c["offsets"], c["total_L"])
        loss = (out * out).sum()
        loss.backward()
        if leaf.grad is None:
            return None, None, "no gradient reached the input"
        return loss.detach().clone(), leaf.grad.detach().clone(), None
    except Exception as e:  # noqa: BLE001
        return None, None, f"{type(e).__name__}: {e}"


# ---------------------------------------------------------------------------
# Block level: the reference repo's research HSTU block, unmodified.
# Same construction as _bestrec_run/test_hstu_parity.py (tied point
# linear_hidden_dim = attention_dim = D/H; published pointwise path:
# linear_config="uvqk", linear_activation="silu", normalization="rel_bias",
# concat_ua=False, dropout 0, eval mode), extended to variable-length jagged
# batches (incl. a zero-length row) so the fbgemm ops do real padding work.
# ---------------------------------------------------------------------------

BLOCK_CFGS = [
    dict(name="blkA_D32_H2_B4_N8", D=32, H=2, N=8,
         lengths=[8, 3, 6, 1], seed_w=1234, seed_x=4321),
    dict(name="blkB_D64_H4_B7_N50", D=64, H=4, N=50,
         lengths=[50, 3, 0, 27, 50, 1, 13], seed_w=777, seed_x=888),
]

BLOCK_STAGES = ["s1_norm_in", "s2_u", "s2_v", "s2_q", "s2_k",
                "s3_attn", "s4_gated", "s5_final", "e2e_fwdA", "e2e_fwdB_rab"]


def run_block_case(cfg, state=None, x_in=None):
    """Build + run the reference block. state/x_in None => generate (leg 1);
    given => replay identical weights/inputs (legs 2/3)."""
    from generative_recommenders.research.modeling.sequential.hstu import (
        RelativePositionalBias,
        SequentialTransductionUnitJagged,
        _hstu_attention_maybe_from_cache,
    )

    D, H, N = cfg["D"], cfg["H"], cfg["N"]
    DH = D // H
    lengths = torch.tensor(cfg["lengths"], dtype=torch.int32)
    total = int(lengths.sum())

    torch.manual_seed(cfg["seed_w"])
    rel = RelativePositionalBias(max_seq_len=N)
    ref = SequentialTransductionUnitJagged(
        embedding_dim=D, linear_hidden_dim=DH, attention_dim=DH,
        dropout_ratio=0.0, attn_dropout_ratio=0.0, num_heads=H,
        linear_activation="silu", relative_attention_bias_module=rel,
        normalization="rel_bias", linear_config="uvqk", concat_ua=False,
    )
    ref.eval()
    # as-initialized weights under THIS torch's RNG (informational RNG check)
    rng_state = {k: v.detach().clone() for k, v in ref.state_dict().items()}
    if state is not None:
        ref.load_state_dict(state)

    if x_in is None:
        torch.manual_seed(cfg["seed_x"])
        x_in = torch.randn(total, D, dtype=torch.float32)
    rng_x = None
    if state is not None:  # informational: what this torch's RNG would give
        torch.manual_seed(cfg["seed_x"])
        rng_x = torch.randn(total, D, dtype=torch.float32)

    # offsets through the fbgemm op itself (real in leg 1, shim in legs 2/3)
    offsets = torch.ops.fbgemm.asynchronous_complete_cumsum(lengths)
    keep = 1.0 - torch.triu(torch.ones(N, N, dtype=torch.float32), diagonal=1)
    ts = torch.zeros(lengths.numel(), N, dtype=torch.int64)

    stages = {}
    with torch.no_grad():
        normed = ref._norm_input(x_in)                       # hstu.py 277-278
        g = F.silu(torch.mm(normed, ref._uvqk))              # hstu.py 322-324
        u, v, q, k = torch.split(g, [DH * H] * 4, dim=1)     # hstu.py 327-336
        attn, _, _ = _hstu_attention_maybe_from_cache(       # hstu.py 151-224
            num_heads=H, attention_dim=DH, linear_dim=DH,
            q=q, k=k, v=v, cached_q=None, cached_k=None,
            delta_x_offsets=None, x_offsets=offsets, all_timestamps=None,
            invalid_attn_mask=keep, rel_attn_bias=rel,
        )
        gated = u * ref._norm_attn_output(attn)              # hstu.py 424
        fin = ref._o(gated) + x_in                           # hstu.py 426-435
        fwd_a = ref(x=x_in, x_offsets=offsets, all_timestamps=None,
                    invalid_attn_mask=keep)[0]
        fwd_b = ref(x=x_in, x_offsets=offsets, all_timestamps=ts,
                    invalid_attn_mask=keep)[0]

    for nm, t in zip(BLOCK_STAGES,
                     [normed, u, v, q, k, attn, gated, fin, fwd_a, fwd_b]):
        stages[nm] = t.detach().contiguous().clone()

    return dict(
        state={k: v.detach().clone() for k, v in ref.state_dict().items()},
        rng_state=rng_state, x=x_in.detach().clone(), rng_x=rng_x,
        offsets=offsets.detach().clone(), keep=keep, stages=stages,
        sanity_staged_eq_fwdA=bool(torch.equal(fin, fwd_a)),
    )


# ---------------------------------------------------------------------------
# Mode: pinned (leg 1)
# ---------------------------------------------------------------------------

def mode_pinned() -> int:
    fbgemm_impl = None
    try:
        import fbgemm_gpu  # noqa: F401  -- registers the real ops
        import importlib.metadata as md
        ver = "unknown-version"
        for dist in ("fbgemm-gpu-cpu", "fbgemm_gpu_cpu", "fbgemm-gpu", "fbgemm_gpu"):
            try:
                ver = f"{dist}=={md.version(dist)}"
                break
            except Exception:
                continue
        fbgemm_impl = f"REAL {ver}"
    except Exception as e:  # documented fallback: shims on both sides
        import fbgemm_shims
        fbgemm_shims.install()
        fbgemm_impl = f"SHIM-FALLBACK (fbgemm_gpu import failed: {e})"
    import fbgemm_shims as shims_mod  # plain functions for the in-env check
    shim_fns = ShimFns(shims_mod)
    real_fns = TorchOpsFns()

    meta = build_meta("pinned", fbgemm_impl)
    print(f"[pinned] torch {meta['torch']} | {meta['system']} | "
          f"fbgemm: {fbgemm_impl} | threads={meta['num_threads']} | "
          f"cuda_available={meta['cuda_available']}")
    assert not meta["cuda_available"], "CPU-only run required"

    op_cases = build_op_cases()
    grad_cases = build_grad_cases()

    # ---- run real ops, save outputs; in-env compare vs shim functions ------
    inenv_ops, n_fail = [], 0
    print("\n[pinned] OP LEVEL: real fbgemm ops -> saved; in-env real-vs-shim-fn:")
    print(f"{'case':44s} {'ctr':3s} {'real':6s} {'max|diff|':>12s}  note")
    for c in op_cases:
        out, err = run_op_case(real_fns, c)
        c["out"], c["err"] = out, err
        sout, serr = run_op_case(shim_fns, c)
        row = dict(name=c["name"], op=c["op"], contract=c["contract"],
                   real_error=err, shimfn_error=serr,
                   max_abs_diff=None, bit_exact=None, note="")
        if err is None and serr is None:
            d, exact, note = tensor_diff(out, sout)
            row.update(max_abs_diff=d, bit_exact=exact, note=note)
            if d != 0.0:
                n_fail += 1
        elif err is not None and c["contract"]:
            n_fail += 1
            row["note"] = "REAL OP FAILED ON IN-CONTRACT CASE"
        elif err is not None:
            row["note"] = "real op rejects beyond-contract case (recorded)"
        if serr is not None:
            n_fail += 1
            row["note"] += " SHIM-FN ERROR"
        inenv_ops.append(row)
        st = "ok" if err is None else "ERR"
        print(f"{c['name']:44s} {str(c['contract'])[0]:3s} {st:6s} "
              f"{fmt_diff(row['max_abs_diff']):>12s}  "
              f"{row['note']}{('  real: ' + err) if err else ''}"
              f"{('  shimfn: ' + serr) if serr else ''}")

    # ---- grads --------------------------------------------------------------
    inenv_grads = []
    print("\n[pinned] GRAD LEVEL (sum-of-squares loss; in-env real-vs-shim-fn):")
    print(f"{'case':44s} {'ctr':3s} {'real':6s} {'grad max|d|':>12s} {'loss|d|':>10s}  note")
    for c in grad_cases:
        loss, grad, err = run_grad_case(real_fns, c)
        c["loss"], c["grad"], c["err"] = loss, grad, err
        sloss, sgrad, serr = run_grad_case(shim_fns, c)
        row = dict(name=c["name"], contract=c["contract"], real_error=err,
                   shimfn_error=serr, grad_max_abs_diff=None,
                   loss_abs_diff=None, note="")
        if err is None and serr is None:
            gd, _, note = tensor_diff(grad, sgrad)
            ld = abs(loss.double().item() - sloss.double().item())
            row.update(grad_max_abs_diff=gd, loss_abs_diff=ld, note=note)
            if gd != 0.0:
                n_fail += 1
        elif err is not None and c["contract"]:
            n_fail += 1
            row["note"] = "REAL GRAD FAILED ON IN-CONTRACT CASE"
        elif err is not None:
            row["note"] = "real grad rejects beyond-contract case (recorded)"
        if serr is not None:
            n_fail += 1
            row["note"] += " SHIM-FN ERROR"
        inenv_grads.append(row)
        st = "ok" if err is None else "ERR"
        print(f"{c['name']:44s} {str(c['contract'])[0]:3s} {st:6s} "
              f"{fmt_diff(row['grad_max_abs_diff']):>12s} "
              f"{fmt_diff(row['loss_abs_diff']):>10s}  "
              f"{row['note']}{('  real: ' + err) if err else ''}"
              f"{('  shimfn: ' + serr) if serr else ''}")

    # ---- block level ---------------------------------------------------------
    print("\n[pinned] BLOCK LEVEL: reference HSTU block under the pinned stack:")
    block_results = {}
    for cfg in BLOCK_CFGS:
        res = run_block_case(cfg)
        block_results[cfg["name"]] = res
        if not res["sanity_staged_eq_fwdA"]:
            n_fail += 1
        print(f"  {cfg['name']}: lengths={cfg['lengths']} "
              f"staged==forward: {res['sanity_staged_eq_fwdA']}")

    # ---- persist --------------------------------------------------------------
    os.makedirs(SCRATCH, exist_ok=True)
    torch.save({"meta": meta, "op_cases": op_cases, "grad_cases": grad_cases,
                "inenv_ops": inenv_ops, "inenv_grads": inenv_grads}, OPS_PT)
    torch.save({"meta": meta,
                "cases": [dict(cfg=cfg, **block_results[cfg["name"]])
                          for cfg in BLOCK_CFGS]}, BLOCK_PT)
    with open(os.path.join(SCRATCH, "inenv_results.json"), "w") as f:
        json.dump({"meta": meta, "ops": inenv_ops, "grads": inenv_grads,
                   "block_sanity": {k: v["sanity_staged_eq_fwdA"]
                                    for k, v in block_results.items()}},
                  f, indent=1, default=str)
    print(f"\n[pinned] saved: {OPS_PT}\n[pinned] saved: {BLOCK_PT}")
    print(f"[pinned] GATE (in-env real-vs-shim + contract + sanity): "
          f"{'PASS' if n_fail == 0 else f'FAIL ({n_fail})'}")
    return 0 if n_fail == 0 else 1


# ---------------------------------------------------------------------------
# Mode: shimmed (legs 2 and 3) -- replay saved inputs through the shims
# ---------------------------------------------------------------------------

def mode_shimmed() -> int:
    import fbgemm_shims
    status = fbgemm_shims.install()
    if "NOT installed" in status:
        print("ERROR: real fbgemm ops are registered in this process; "
              "--mode shimmed must exercise the shims. Run in an env where "
              "fbgemm_gpu is not imported.")
        return 2
    fns = TorchOpsFns()  # now dispatches to the registered shims
    meta = build_meta("shimmed", f"shims ({status})")
    print(f"[shimmed] torch {meta['torch']} | {meta['system']} | {status} | "
          f"threads={meta['num_threads']} | cuda_available={meta['cuda_available']}")
    assert not meta["cuda_available"], "CPU-only run required (CVD='' is set)"
    if not (os.path.exists(OPS_PT) and os.path.exists(BLOCK_PT)):
        print(f"ERROR: {OPS_PT} / {BLOCK_PT} missing -- run --mode pinned first.")
        return 2

    ops_data = torch.load(OPS_PT, map_location="cpu", weights_only=True)
    block_data = torch.load(BLOCK_PT, map_location="cpu", weights_only=True)
    pm = ops_data["meta"]
    same_stack = (pm["torch"] == meta["torch"] and pm["system"] == meta["system"])
    block_tol = 0.0 if same_stack else BLOCK_TOL_CROSS
    print(f"[shimmed] pinned side: torch {pm['torch']} | {pm['system']} | "
          f"{pm['fbgemm_impl']}")
    print(f"[shimmed] same_stack_as_pinned={same_stack} -> block gate "
          f"{'exact 0.0' if same_stack else f'<= {BLOCK_TOL_CROSS:.0e}'}")

    n_fail = 0
    results = {"tag": f"{meta['system']}-torch{meta['torch']}-shims",
               "pinned_meta": pm, "replay_meta": meta,
               "same_stack_as_pinned": same_stack,
               "ops": [], "grads": [], "blocks": [], "rng_info": {},
               "block_sanity": {}}

    # ---- op replay -----------------------------------------------------------
    print(f"\n[shimmed] OP LEVEL replay vs pinned real outputs "
          f"(gate: exactly 0.0):")
    print(f"{'case':44s} {'ctr':3s} {'status':10s} {'max|diff|':>12s}  note")
    for c in ops_data["op_cases"]:
        out, err = run_op_case(fns, c)
        row = dict(name=c["name"], op=c["op"], contract=c["contract"],
                   status=None, max_abs_diff=None, bit_exact=None, note="")
        if c["err"] is not None and err is not None:
            row.update(status="BOTH_ERR",
                       note=f"pinned: {c['err']} | replay: {err}")
        elif c["err"] is not None:
            row.update(status="PINNED_ERR",
                       note=f"real op errored ({c['err']}); shim accepts "
                            f"(superset) -- no reference output to compare")
            if c["contract"]:
                n_fail += 1
        elif err is not None:
            row.update(status="REPLAY_ERR", note=err)
            n_fail += 1
        else:
            d, exact, note = tensor_diff(c["out"], out)
            row.update(status="OK", max_abs_diff=d, bit_exact=exact, note=note)
            if d != 0.0:
                n_fail += 1
        results["ops"].append(row)
        print(f"{c['name']:44s} {str(c['contract'])[0]:3s} {row['status']:10s} "
              f"{fmt_diff(row['max_abs_diff']):>12s}  {row['note']}")

    # ---- grad replay -----------------------------------------------------------
    print(f"\n[shimmed] GRAD LEVEL replay (grad gate: exactly 0.0; "
          f"loss diff informational):")
    print(f"{'case':44s} {'ctr':3s} {'status':10s} {'grad max|d|':>12s} "
          f"{'loss|d|':>10s}  note")
    for c in ops_data["grad_cases"]:
        loss, grad, err = run_grad_case(fns, c)
        row = dict(name=c["name"], contract=c["contract"], status=None,
                   grad_max_abs_diff=None, loss_abs_diff=None, note="")
        if c["err"] is not None and err is not None:
            row.update(status="BOTH_ERR",
                       note=f"pinned: {c['err']} | replay: {err}")
        elif c["err"] is not None:
            row.update(status="PINNED_ERR",
                       note=f"real grad errored ({c['err']}); shim accepts")
            if c["contract"]:
                n_fail += 1
        elif err is not None:
            row.update(status="REPLAY_ERR", note=err)
            n_fail += 1
        else:
            gd, _, note = tensor_diff(c["grad"], grad)
            ld = abs(c["loss"].double().item() - loss.double().item())
            row.update(status="OK", grad_max_abs_diff=gd, loss_abs_diff=ld,
                       note=note)
            if gd != 0.0:
                n_fail += 1
        results["grads"].append(row)
        print(f"{c['name']:44s} {str(c['contract'])[0]:3s} {row['status']:10s} "
              f"{fmt_diff(row['grad_max_abs_diff']):>12s} "
              f"{fmt_diff(row['loss_abs_diff']):>10s}  {row['note']}")

    # ---- block replay -----------------------------------------------------------
    print(f"\n[shimmed] BLOCK LEVEL replay: reference HSTU block, identical "
          f"weights+inputs (gate: {'0.0' if same_stack else f'{BLOCK_TOL_CROSS:.0e}'}):")
    print(f"{'cfg / stage':44s} {'max|diff|':>12s}  note")
    for saved in block_data["cases"]:
        cfg = saved["cfg"]
        res = run_block_case(cfg, state=saved["state"], x_in=saved["x"])
        results["block_sanity"][cfg["name"]] = {
            "pinned": bool(saved["sanity_staged_eq_fwdA"]),
            "replay": bool(res["sanity_staged_eq_fwdA"]),
        }
        if not res["sanity_staged_eq_fwdA"]:
            n_fail += 1
        d_off, _, _ = tensor_diff(saved["offsets"], res["offsets"])
        if d_off != 0.0:
            n_fail += 1
            print(f"{cfg['name'] + ' / offsets':44s} {fmt_diff(d_off):>12s}  "
                  f"OFFSETS DIFFER (acc via shim)")
        for st in BLOCK_STAGES:
            d, exact, note = tensor_diff(saved["stages"][st], res["stages"][st])
            results["blocks"].append(dict(cfg=cfg["name"], stage=st,
                                          max_abs_diff=d, bit_exact=exact))
            if d > block_tol:
                n_fail += 1
                note = (note + " EXCEEDS GATE").strip()
            print(f"{cfg['name'] + ' / ' + st:44s} {fmt_diff(d):>12s}  {note}")
        # informational: cross-version RNG reproducibility (not gated)
        rw = max(tensor_diff(saved["state"][k], res["rng_state"][k])[0]
                 for k in saved["state"])
        rx = tensor_diff(saved["x"], res["rng_x"])[0] if res["rng_x"] is not None else None
        results["rng_info"][cfg["name"]] = {
            "init_weights_max_abs_diff_same_seed": rw,
            "input_randn_max_abs_diff_same_seed": rx,
        }
        print(f"{cfg['name'] + ' / [info] RNG same-seed init':44s} "
              f"{fmt_diff(rw):>12s}  (weights; informational)")
        print(f"{cfg['name'] + ' / [info] RNG same-seed randn':44s} "
              f"{fmt_diff(rx):>12s}  (input x; informational)")

    # ---- persist + gate -----------------------------------------------------------
    results["gates"] = {"n_fail": n_fail, "block_tol_used": block_tol,
                        "overall_pass": n_fail == 0}
    tag = results["tag"].replace("+", "p").replace("/", "_")
    out_json = os.path.join(SCRATCH, f"replay_results_{tag}.json")
    with open(out_json, "w") as f:
        json.dump(results, f, indent=1, default=str)
    print(f"\n[shimmed] results written: {out_json}")
    print(f"[shimmed] GATE: {'PASS' if n_fail == 0 else f'FAIL ({n_fail})'}")
    return 0 if n_fail == 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mode", choices=["pinned", "shimmed"], required=True,
                    help="pinned: generate+run under the pinned stack (WSL); "
                         "shimmed: replay through the shims (any env)")
    args = ap.parse_args()
    os.makedirs(SCRATCH, exist_ok=True)
    return mode_pinned() if args.mode == "pinned" else mode_shimmed()


if __name__ == "__main__":
    raise SystemExit(main())
