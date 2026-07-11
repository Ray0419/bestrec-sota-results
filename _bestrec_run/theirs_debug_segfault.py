#!/usr/bin/env python
"""Isolate the Windows segfault: DDP+gloo+CUDA vs detect_anomaly vs custom ops.

Run each stage in a SEPARATE process:
  python theirs_debug_segfault.py A   # gloo init + DDP(cuda) + backward + step
  python theirs_debug_segfault.py B   # detect_anomaly + custom fbgemm shim op in graph (no DDP)
  python theirs_debug_segfault.py C   # both combined
  python theirs_debug_segfault.py D   # DDP without detect_anomaly, WITH custom op
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import torch
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP

import fbgemm_shims

stage = sys.argv[1]
fbgemm_shims.install()
dev = "cuda"


def make_model():
    m = torch.nn.Sequential(torch.nn.Linear(16, 32), torch.nn.SiLU(),
                            torch.nn.Linear(32, 16)).to(dev)
    return m


def loss_with_custom_op(model, x, lengths):
    off = torch.ops.fbgemm.asynchronous_complete_cumsum(lengths)
    h = model(x)                                     # [B, N, 16]
    jag = torch.ops.fbgemm.dense_to_jagged(h, [off])[0]
    back = torch.ops.fbgemm.jagged_to_padded_dense(jag, [off], [x.size(1)], 0.0)
    return (back ** 2).mean()


def run(use_ddp: bool, use_anomaly: bool):
    if use_ddp:
        os.environ["MASTER_ADDR"] = "localhost"
        os.environ["MASTER_PORT"] = "12499"
        dist.init_process_group("gloo", rank=0, world_size=1)
    if use_anomaly:
        torch.autograd.set_detect_anomaly(True)
    model = make_model()
    if use_ddp:
        model = DDP(model, device_ids=[0], broadcast_buffers=False)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3)
    B, N = 8, 12
    lengths = torch.randint(1, N + 1, (B,), dtype=torch.int64, device=dev)
    for step in range(5):
        x = torch.randn(B, N, 16, device=dev)
        opt.zero_grad()
        loss = loss_with_custom_op(model, x, lengths)
        loss.backward()
        opt.step()
        print(f"  step {step} loss {loss.item():.5f}", flush=True)
    if use_ddp:
        dist.destroy_process_group()
    print(f"STAGE OK (ddp={use_ddp}, anomaly={use_anomaly})", flush=True)


if stage == "A":
    # DDP without custom op in graph
    if True:
        os.environ["MASTER_ADDR"] = "localhost"
        os.environ["MASTER_PORT"] = "12499"
        dist.init_process_group("gloo", rank=0, world_size=1)
        model = DDP(make_model(), device_ids=[0], broadcast_buffers=False)
        opt = torch.optim.AdamW(model.parameters(), lr=1e-3)
        for step in range(5):
            x = torch.randn(64, 16, device=dev)
            opt.zero_grad()
            loss = (model(x) ** 2).mean()
            loss.backward()
            opt.step()
            print(f"  step {step} loss {loss.item():.5f}", flush=True)
        dist.destroy_process_group()
        print("STAGE A OK (pure DDP+gloo+cuda)", flush=True)
elif stage == "B":
    run(use_ddp=False, use_anomaly=True)
elif stage == "C":
    run(use_ddp=True, use_anomaly=True)
elif stage == "D":
    run(use_ddp=True, use_anomaly=False)
elif stage == "E":
    # init+destroy gloo, custom-op training WITHOUT DDP wrapper
    os.environ["MASTER_ADDR"] = "localhost"
    os.environ["MASTER_PORT"] = "12499"
    dist.init_process_group("gloo", rank=0, world_size=1)
    model = make_model()
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3)
    B, N = 8, 12
    lengths = torch.randint(1, N + 1, (B,), dtype=torch.int64, device=dev)
    torch.autograd.set_detect_anomaly(True)
    for step in range(5):
        x = torch.randn(B, N, 16, device=dev)
        opt.zero_grad()
        loss = loss_with_custom_op(model, x, lengths)
        loss.backward()
        opt.step()
        print(f"  step {step} loss {loss.item():.5f}", flush=True)
    dist.destroy_process_group()
    print("STAGE E OK (gloo init/destroy + anomaly + custom op, no DDP)", flush=True)
else:
    raise SystemExit("stage must be A/B/C/D/E")
