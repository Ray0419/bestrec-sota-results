#!/usr/bin/env python
"""FIR-encoder probe — EXPLORATORY, not pre-registered.

Question (screen wjslq4lbw, open question #4): does a strictly causal FIR-only
encoder hold accuracy against an honestly optimized attention baseline when it
REPLACES attention (not rides on it) — and what does it cost at long histories?

Clean minimal reimplementation (deliberately independent of the canonical
_bestrec_run FIR code). Two encoders sharing one skeleton, differing ONLY in
the token mixer:

  SASREC  : pre-LN transformer block, causal SDPA attention
            (F.scaled_dot_product_attention -> flash / mem-efficient kernels
            on CUDA automatically; the "honest optimized baseline")
  FIR     : pre-LN block, strictly causal depthwise FIR convolution
            (K taps, left-padded; linear in sequence length)

Protocol:
  Accuracy : MovieLens-1M, all interactions, chronological per user,
             leave-one-out (last = test, second-last = valid), FULL-catalog
             ranking with history masking (no sampled negatives), NDCG@10 /
             HR@10, max length 200, 3 seeds each arm.
  Cost     : forward-pass latency (median of 30 after 10 warmup) and peak
             memory at lengths {200,400,600,800,1000}, batch 256, both models,
             eval mode. CUDA events for timing on CUDA; perf_counter+sync
             elsewhere.

Usage:
  python fir_encoder_probe.py --data ./ml-1m --out ./results           # full
  python fir_encoder_probe.py --data ./ml-1m --out ./results --smoke   # ~2 min
"""

import argparse
import json
import math
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

MAX_LEN = 200
D_MODEL = 64
N_BLOCKS = 2
N_HEADS = 2
FIR_TAPS = 64
DROPOUT = 0.2
LR = 1e-3
EPOCHS = 200
PATIENCE = 20          # early stop on valid NDCG@10
BATCH = 128
SEEDS = (13, 42, 2026)
BENCH_LENGTHS = (200, 400, 600, 800, 1000)
BENCH_BATCH = 256


# ---------------------------------------------------------------- data

def load_ml1m(data_dir: Path):
    """ratings.dat -> per-user chronological item sequences (1-indexed items)."""
    users = {}
    for line in (data_dir / "ratings.dat").read_text().splitlines():
        u, i, _r, t = line.strip().split("::")
        users.setdefault(int(u), []).append((int(t), int(i)))
    remap, seqs = {}, []
    for u in sorted(users):
        seq = [i for _, i in sorted(users[u])]
        if len(seq) < 5:
            continue
        seqs.append([remap.setdefault(i, len(remap) + 1) for i in seq])
    return seqs, len(remap) + 1  # n_items incl. pad id 0


class SeqData(torch.utils.data.Dataset):
    def __init__(self, seqs):
        self.seqs = seqs

    def __len__(self):
        return len(self.seqs)

    def __getitem__(self, k):
        s = self.seqs[k][:-2][-(MAX_LEN + 1):]  # train region (excl. valid/test)
        inp = np.zeros(MAX_LEN, dtype=np.int64)
        tgt = np.zeros(MAX_LEN, dtype=np.int64)
        x, y = s[:-1], s[1:]
        inp[MAX_LEN - len(x):] = x
        tgt[MAX_LEN - len(y):] = y
        return inp, tgt


# ---------------------------------------------------------------- models

class AttnMixer(nn.Module):
    def __init__(self):
        super().__init__()
        self.qkv = nn.Linear(D_MODEL, 3 * D_MODEL)
        self.proj = nn.Linear(D_MODEL, D_MODEL)

    def forward(self, x):  # (B,L,D)
        B, L, _ = x.shape
        q, k, v = self.qkv(x).chunk(3, dim=-1)
        q, k, v = (t.view(B, L, N_HEADS, -1).transpose(1, 2) for t in (q, k, v))
        o = F.scaled_dot_product_attention(q, k, v, is_causal=True)
        return self.proj(o.transpose(1, 2).reshape(B, L, D_MODEL))


class FIRMixer(nn.Module):
    """Strictly causal depthwise FIR: left-pad K-1, groups=D conv."""

    def __init__(self):
        super().__init__()
        self.taps = nn.Parameter(torch.zeros(D_MODEL, 1, FIR_TAPS))
        with torch.no_grad():
            self.taps[:, 0, -1] = 1.0  # identity init (current position)
        self.proj = nn.Linear(D_MODEL, D_MODEL)

    def forward(self, x):  # (B,L,D)
        h = F.pad(x.transpose(1, 2), (FIR_TAPS - 1, 0))
        h = F.conv1d(h, self.taps, groups=D_MODEL).transpose(1, 2)
        return self.proj(F.gelu(h))


class Encoder(nn.Module):
    def __init__(self, n_items, mixer_cls):
        super().__init__()
        self.item = nn.Embedding(n_items, D_MODEL, padding_idx=0)
        self.pos = nn.Embedding(MAX_LEN + 1024, D_MODEL)  # headroom for bench lengths
        self.drop = nn.Dropout(DROPOUT)
        self.blocks = nn.ModuleList()
        for _ in range(N_BLOCKS):
            self.blocks.append(nn.ModuleDict({
                "ln1": nn.LayerNorm(D_MODEL),
                "mix": mixer_cls(),
                "ln2": nn.LayerNorm(D_MODEL),
                "ffn": nn.Sequential(
                    nn.Linear(D_MODEL, 4 * D_MODEL), nn.GELU(),
                    nn.Dropout(DROPOUT), nn.Linear(4 * D_MODEL, D_MODEL)),
            }))
        self.ln_f = nn.LayerNorm(D_MODEL)

    def forward(self, seq):  # (B,L) -> (B,L,D)
        L = seq.shape[1]
        pos = torch.arange(L, device=seq.device)
        h = self.drop(self.item(seq) + self.pos(pos)[None])
        pad = (seq == 0).unsqueeze(-1)
        for b in self.blocks:
            h = h + b["mix"](b["ln1"](h))
            h = h + b["ffn"](b["ln2"](h))
            h = h.masked_fill(pad, 0.0)
        return self.ln_f(h)

    def logits(self, h):  # tied weights
        return h @ self.item.weight.T


# ---------------------------------------------------------------- train / eval

def evaluate(model, seqs, device, split):
    """Full-catalog leave-one-out. split: 'valid' (-2) or 'test' (-1)."""
    model.eval()
    ndcg = hr = n = 0
    off = -1 if split == "valid" else 0
    with torch.no_grad():
        for k in range(0, len(seqs), 512):
            batch = seqs[k: k + 512]
            inp = np.zeros((len(batch), MAX_LEN), dtype=np.int64)
            tgts, hists = [], []
            for j, s in enumerate(batch):
                ctx = s[: len(s) - 1 + off][-MAX_LEN:]
                inp[j, MAX_LEN - len(ctx):] = ctx
                tgts.append(s[len(s) - 1 + off])
                hists.append(set(ctx))
            h = model(torch.as_tensor(inp, device=device))[:, -1]
            sc = model.logits(h)
            sc[:, 0] = -1e9
            for j, (t, hist) in enumerate(zip(tgts, hists)):
                s_j = sc[j].clone()
                s_j[list(hist)] = -1e9
                rank = int((s_j > s_j[t]).sum().item())
                if rank < 10:
                    ndcg += 1.0 / math.log2(rank + 2)
                    hr += 1
                n += 1
    return ndcg / n, hr / n


def train_arm(arch, seed, seqs, n_items, device, epochs, log):
    torch.manual_seed(seed)
    np.random.seed(seed)
    model = Encoder(n_items, AttnMixer if arch == "sasrec" else FIRMixer).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=LR, betas=(0.9, 0.98))
    dl = torch.utils.data.DataLoader(SeqData(seqs), batch_size=BATCH, shuffle=True,
                                     drop_last=True, num_workers=0)
    best = (-1, None, 0)  # (valid ndcg, state, epoch)
    for ep in range(1, epochs + 1):
        model.train()
        tot = cnt = 0
        for inp, tgt in dl:
            inp, tgt = inp.to(device), tgt.to(device)
            logits = model.logits(model(inp))
            loss = F.cross_entropy(logits.view(-1, n_items), tgt.view(-1),
                                   ignore_index=0)
            opt.zero_grad()
            loss.backward()
            opt.step()
            tot += loss.item(); cnt += 1
        v_ndcg, _ = evaluate(model, seqs, device, "valid")
        if v_ndcg > best[0]:
            best = (v_ndcg, {k: v.detach().clone() for k, v in model.state_dict().items()}, ep)
        log(f"    {arch} s{seed} ep{ep:3d} loss {tot/cnt:.4f} vNDCG {v_ndcg:.4f} (best {best[0]:.4f}@{best[2]})")
        if ep - best[2] >= PATIENCE:
            break
    model.load_state_dict(best[1])
    t_ndcg, t_hr = evaluate(model, seqs, device, "test")
    return model, {"seed": seed, "test_ndcg10": t_ndcg, "test_hr10": t_hr,
                   "valid_ndcg10": best[0], "best_epoch": best[2]}


# ---------------------------------------------------------------- benchmark

def bench(model, n_items, device, log):
    model.eval()
    out = {}
    for L in BENCH_LENGTHS:
        seq = torch.randint(1, n_items, (BENCH_BATCH, L), device=device)
        try:
            with torch.no_grad():
                for _ in range(10):
                    model(seq)
                if device.type == "cuda":
                    torch.cuda.synchronize()
                    torch.cuda.reset_peak_memory_stats()
                    times = []
                    for _ in range(30):
                        s = torch.cuda.Event(enable_timing=True)
                        e = torch.cuda.Event(enable_timing=True)
                        s.record(); model(seq); e.record()
                        torch.cuda.synchronize()
                        times.append(s.elapsed_time(e))
                    mem = torch.cuda.max_memory_allocated() / 2**20
                else:
                    times = []
                    for _ in range(30):
                        if device.type == "mps":
                            torch.mps.synchronize()
                        t0 = time.perf_counter()
                        model(seq)
                        if device.type == "mps":
                            torch.mps.synchronize()
                        times.append((time.perf_counter() - t0) * 1e3)
                    mem = None
            out[L] = {"latency_ms_median": float(np.median(times)),
                      "latency_ms_p90": float(np.percentile(times, 90)),
                      "peak_mem_mb": mem}
        except torch.cuda.OutOfMemoryError:
            torch.cuda.empty_cache()
            out[L] = {"oom": True}
        log(f"    L={L}: {out[L]}")
    return out


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="./ml-1m")
    ap.add_argument("--out", default="./results")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--device", default="auto")
    args = ap.parse_args()

    if args.device == "auto":
        dev = "cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu")
    else:
        dev = args.device
    device = torch.device(dev)
    out_dir = Path(args.out); out_dir.mkdir(parents=True, exist_ok=True)
    logf = open(out_dir / "probe.log", "a")

    def log(m):
        print(m, flush=True); logf.write(m + "\n"); logf.flush()

    log(f"== FIR-encoder probe {'SMOKE' if args.smoke else 'FULL'} device={dev} "
        f"torch={torch.__version__} {time.strftime('%F %T')}")
    if dev == "cuda":
        log(f"   gpu={torch.cuda.get_device_name(0)} "
            f"sdpa_flash={torch.backends.cuda.flash_sdp_enabled()}")

    seqs, n_items = load_ml1m(Path(args.data))
    log(f"   ML-1M: {len(seqs)} users, {n_items-1} items, "
        f"median len {int(np.median([len(s) for s in seqs]))}")

    epochs = 2 if args.smoke else EPOCHS
    seeds = SEEDS[:1] if args.smoke else SEEDS
    results = {"device": dev, "torch": torch.__version__, "config": {
        "d_model": D_MODEL, "blocks": N_BLOCKS, "heads": N_HEADS,
        "fir_taps": FIR_TAPS, "max_len": MAX_LEN, "smoke": args.smoke},
        "accuracy": {}, "bench": {}}

    bench_done = set()
    for arch in ("sasrec", "fir"):
        results["accuracy"][arch] = []
        for seed in seeds:
            t0 = time.time()
            log(f"  train {arch} seed {seed}")
            model, res = train_arm(arch, seed, seqs, n_items, device, epochs, log)
            res["train_s"] = round(time.time() - t0, 1)
            results["accuracy"][arch].append(res)
            log(f"  {arch} s{seed}: test NDCG@10 {res['test_ndcg10']:.4f} "
                f"HR@10 {res['test_hr10']:.4f} ({res['train_s']}s)")
            if arch not in bench_done:
                log(f"  benchmark {arch} (batch {BENCH_BATCH})")
                results["bench"][arch] = bench(model, n_items, device, log)
                bench_done.add(arch)
            (out_dir / "probe_results.json").write_text(json.dumps(results, indent=2))

    for arch in ("sasrec", "fir"):
        nd = [r["test_ndcg10"] for r in results["accuracy"][arch]]
        log(f"== {arch}: test NDCG@10 mean {np.mean(nd):.4f} "
            f"(seeds: {' '.join(f'{x:.4f}' for x in nd)})")
    log("== probe complete")


if __name__ == "__main__":
    main()
