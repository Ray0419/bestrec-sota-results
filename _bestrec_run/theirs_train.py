#!/usr/bin/env python
"""Launch HSTU-BLaIR's OWN research trainer locally (their repo, our env, our GPU).

Equivalent to their documented entry point
    CUDA_VISIBLE_DEVICES=0 python3 main.py --gin_config_file=<cfg> --master_port=<p>
for the single-GPU case, but WITHOUT main.py, because main.py
  (a) does `import fbgemm_gpu` (no Windows wheels; replaced by pure-PyTorch
      shims in _bestrec_run/fbgemm_shims.py -- data movement only), and
  (b) uses mp.set_start_method("forkserver") (POSIX-only). Their _main spawns
      nprocs = torch.cuda.device_count() = 1 process running
      train_fn(rank=0, world_size=1, master_port); we call that directly.

MONKEYPATCHES applied to their trainer module from our side (repo untouched):
  1. train.setup: init_process_group backend "nccl" -> "gloo"
     (NCCL does not exist on Windows; world_size=1, so the collective backend
     only affects DDP bookkeeping, not math).
  2. train.add_to_summary_writer: wrapped to ALSO append every metric that
     their code sends to TensorBoard (hr@10/50/100/200, ndcg@10/50/100/200,
     mrr, ...) to <run_dir>/metrics.jsonl. Pure logging addition.
  3. train.DDP -> single-process passthrough wrapper. Reason: on Windows,
     torch 2.11 DistributedDataParallel with gloo + CUDA modules dies with
     ACCESS_VIOLATION (0xC0000005) even for a 2-layer toy model with no
     custom ops (see theirs_debug_segfault.py stages A/C/D; stage E shows
     everything EXCEPT the DDP wrapper works). At world_size=1 DDP is
     mathematically the identity: its only job is averaging gradients over
     ranks (a no-op for 1 rank; broadcast_buffers is already False in their
     call). The wrapper keeps the `.module` attribute and the "module."
     state_dict prefix so their checkpoint format is unchanged.
  ( 4. optional, off by default: dataloader worker override for Windows --
     recorded in run_meta.json when used. num_workers only affects wall clock;
     DatasetV2.__getitem__ is deterministic and all sampling RNG lives in the
     training process, so results are unaffected. )

Usage:
  .../python theirs_train.py --gin external/HSTU-BLaIR/configs/amzn23_office/sasrec-sampled-softmax-n512-final.gin \
       --run-name office_sasrec_seed42 [--binding "train_fn.num_epochs = 2"]... [--workers0] [--port 12356]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))            # _bestrec_run
ROOT = os.path.dirname(HERE)                                  # repo root
THEIRS = os.path.join(ROOT, "external", "HSTU-BLaIR")
RUNROOT = os.path.join(HERE, "theirs_runs")

sys.path.insert(0, THEIRS)
sys.path.insert(0, HERE)


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_head(repo: str) -> str:
    import subprocess
    try:
        return subprocess.check_output(
            ["git", "-C", repo, "rev-parse", "HEAD"], text=True
        ).strip()
    except Exception:
        return "unknown"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gin", required=True, help="path to their gin config")
    ap.add_argument("--run-name", required=True)
    ap.add_argument("--binding", action="append", default=[],
                    help="extra gin binding (smoke tests only; recorded)")
    ap.add_argument("--workers0", action="store_true",
                    help="override dataloader to num_workers=0 (Windows perf; "
                         "no effect on results; recorded)")
    ap.add_argument("--port", type=int, default=12355)
    args = ap.parse_args()

    gin_path = os.path.abspath(args.gin)
    os.makedirs(RUNROOT, exist_ok=True)
    os.chdir(RUNROOT)   # their code reads tmp/... and writes exps/, ckpts/ here

    run_dir = os.path.join(RUNROOT, args.run_name)
    os.makedirs(run_dir, exist_ok=True)

    # --- fbgemm shims BEFORE importing their modules -----------------------
    import fbgemm_shims
    shim_status = fbgemm_shims.install()

    import gin
    import torch
    import torch.distributed as dist

    import generative_recommenders.research.trainer.train as train_mod
    from generative_recommenders.research.data.eval import _avg

    # --- patch 1: gloo instead of nccl (Windows) ---------------------------
    def setup_gloo(rank: int, world_size: int, master_port: int) -> None:
        os.environ["MASTER_ADDR"] = "localhost"
        os.environ["MASTER_PORT"] = str(master_port)
        dist.init_process_group("gloo", rank=rank, world_size=world_size)

    train_mod.setup = setup_gloo

    # --- patch 2: tee all tensorboard metrics to metrics.jsonl -------------
    metrics_path = os.path.join(run_dir, "metrics.jsonl")
    orig_writer_fn = train_mod.add_to_summary_writer

    def tee_add_to_summary_writer(writer, batch_id, metrics, prefix, world_size):
        rec = {"prefix": prefix, "batch_id": int(batch_id),
               "t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        for key, values in metrics.items():
            try:
                rec[key] = float(_avg(values, world_size))
            except Exception:
                pass
        with open(metrics_path, "a") as f:
            f.write(json.dumps(rec) + "\n")
        return orig_writer_fn(writer, batch_id, metrics, prefix, world_size)

    train_mod.add_to_summary_writer = tee_add_to_summary_writer

    # --- patch 2b: redirect TensorBoard event files to a SHORT directory.
    # Their log_dir embeds the full model_desc; on Windows the resulting
    # event-file path exceeds MAX_PATH (260) for amzn23_office (261 chars)
    # and SummaryWriter creation dies with FileNotFoundError. Event-file
    # LOCATION only; the intended log_dir is recorded in run_meta/log, and
    # all scalar content is also tee'd to metrics.jsonl by patch 2.
    _RealSummaryWriter = train_mod.SummaryWriter

    def short_dir_summary_writer(log_dir=None, *a, **k):
        tb_dir = os.path.join(run_dir, "tb")
        os.makedirs(tb_dir, exist_ok=True)
        with open(os.path.join(run_dir, "tb_logdir_intended.txt"), "w") as f:
            f.write(str(log_dir) + "\n")
        return _RealSummaryWriter(log_dir=tb_dir, *a, **k)

    train_mod.SummaryWriter = short_dir_summary_writer

    # --- patch 3: single-process DDP passthrough (Windows gloo+CUDA DDP
    #     segfaults; world_size=1 DDP is identity) ---------------------------
    class SingleProcessDDP(torch.nn.Module):
        def __init__(self, module, device_ids=None, broadcast_buffers=False,
                     **kwargs):
            super().__init__()
            self.module = module            # keeps "module." state_dict prefix

        def forward(self, *args, **kwargs):
            return self.module(*args, **kwargs)

        @property
        def device(self):                   # train.py uses model.device
            return next(self.module.parameters()).device

    train_mod.DDP = SingleProcessDDP

    # --- gin config ---------------------------------------------------------
    bindings = list(args.binding)
    if args.workers0:
        bindings += ["create_data_loader.num_workers = 0",
                     "create_data_loader.prefetch_factor = None"]
    gin.parse_config_files_and_bindings([gin_path], bindings)

    # --- provenance ---------------------------------------------------------
    meta = {
        "run_name": args.run_name,
        "gin_file": gin_path,
        "gin_sha256": sha256_file(gin_path),
        "extra_bindings": bindings,
        "master_port": args.port,
        "shims": shim_status,
        "their_commit": git_head(THEIRS),
        "our_commit": git_head(ROOT),
        "torch": torch.__version__,
        "cuda": torch.version.cuda,
        "device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu",
        "python": sys.version,
        "monkeypatches": ["train.setup: nccl->gloo",
                          "train.add_to_summary_writer: tee to metrics.jsonl",
                          "train.SummaryWriter: events to <run_dir>/tb "
                          "(Windows MAX_PATH; location only)",
                          "train.DDP: single-process passthrough (Windows "
                          "gloo+CUDA DDP segfaults; identity at world_size=1)"],
        "argv": sys.argv,
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    with open(os.path.join(run_dir, "run_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)
    shutil.copy(gin_path, os.path.join(run_dir, os.path.basename(gin_path)))

    print(f"[theirs_train] shims: {shim_status}", flush=True)
    print(f"[theirs_train] gin: {gin_path}", flush=True)
    print(f"[theirs_train] bindings: {bindings}", flush=True)

    t0 = time.time()
    try:
        train_mod.train_fn(rank=0, world_size=1, master_port=args.port)
    finally:
        meta["elapsed_sec"] = round(time.time() - t0, 1)
        meta["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with open(os.path.join(run_dir, "run_meta.json"), "w") as f:
            json.dump(meta, f, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
