# -*- coding: utf-8 -*-
"""PREREG_SCALE_LOSS_V1: scale ladder x loss family, degree-sliced.

Crosses the two axes that the scaling-law and the negative-sampling literatures
each hold fixed:
  scale  : --d-model in {32, 64, 128, 256}   (n_layers=4, n_heads=2 fixed)
  loss   : fce  = --chunked-full-softmax     (all negatives, CE form)
           sce  = --sampled-negs 256         (256 negatives, CE form)
           gbce = --gbce-t 0.75 --gbce-negs 256   (beta = 0.2578, fixed: alpha
                                                   depends only on the catalogue)
Endpoint is the degree-sliced NDCG@10 in *.degree_eval.json (by_degree), bands
TAIL = k1-50, HEAD = k>200, AGG = warm.  k=0 is degenerate and excluded.

Protocol change vs poc_loss_driver.py, declared in PREREG S4.3 and applied to
EVERY cell: --eval-every 5, so best-checkpoint-on-validation selection is
meaningful and larger rungs are not measured while overfitted.  The ladder is
therefore run fresh at d=64 too; the 9 existing --eval-every 20 runs are kept
only as a protocol-consistency check.

Foreground execution with a per-invocation cap and skip-if-exists resume:
detached/background launches get reaped in this environment.  Logs go to files;
never pipe a run through `Select-Object -First N` (it kills the upstream proc).

Usage:  python poc_scale_loss_driver.py [max_cells_this_invocation]
        python poc_scale_loss_driver.py --plan     # print cells, run nothing
        python poc_scale_loss_driver.py --timing   # PREREG S9 calibration only
                                                   # (d=32 and d=256, fce, seed 1)
"""
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "poc_out")
TRAINER = os.path.join(HERE, "run_sasrec_sbert_temporal.py")
EVAL = os.path.join(HERE, "poc_temporal_eval.py")

# Stage 1 seeds (PREREG S4.1).  Stage 2 appends 20260739, 20260740 -- only
# after the 3/3 sign-consistency gate in PREREG S6 fires.
#
# GATE FIRED 2026-08-18: stage-1 H2 contrast was negative in 3/3 seeds
# (-0.000943, -0.000953, -0.000890).  Pass --stage2 to add the two seeds.
SEEDS = (20260736, 20260737, 20260738)
STAGE2_SEEDS = (20260739, 20260740)
RUNGS = (32, 64, 128, 256)          # cheapest first within a seed
LOSSES = {
    "fce":  ["--chunked-full-softmax", "--item-chunk", "32768"],
    "sce":  ["--sampled-negs", "256"],
    "gbce": ["--gbce-t", "0.75", "--gbce-negs", "256"],
}

# Copied verbatim from poc_loss_driver.py BASE except: the loss flags (per arm),
# --d-model (the ladder), and --eval-every (PREREG S4.3).
BASE = ["Musical_Instruments", "--epochs", "20", "--batch-size", "256",
        "--n-layers", "4", "--n-heads", "2",
        "--dropout", "0.5", "--encoder", "hstu",
        "--time-bias", "--pos-rab", "--causal-filter", "--filter-kernel", "16",
        "--text-sim-bias", "--text-prototypes", "512",
        "--lr-schedule", "warmup_cosine", "--temporal-split",
        "--eval-every", "5"]

TIMING_LOG = os.path.join(OUT, "SXL_timing.json")

# R1 (PREREG S4.2 robustness, fires only after the stage-2 gate passes -- it did,
# 2026-08-18).  Answers "the big rung was mistuned / undertrained", which became
# load-bearing when the HEAD slope came out negative for all three losses.
# LR grid was frozen in the prereg at {1e-3, 5e-4}; 1e-3 is the main ladder, so
# R1 only needs the 5e-4 cells.  Never a selection -- a sensitivity report.
R1_LR = "5e-4"
R1_LOSSES = ("fce", "gbce")
R1_RUNG = 256

# Steam external replication (PREREG S4.2): 3 losses x d{64,256} x 3 seeds.
# Config copied verbatim from poc_temporal_driver.py STEAM_ARGV, minus the loss
# flags (per arm), --d-model (the ladder) and --eval-every (A2/S4.3: 5).
# CAVEAT to report: beta is NOT matched to MI.  alpha = K/(n_items-1) depends on
# the catalogue, and Steam has ~12k items vs MI's 24,587, so beta ~= 0.266 here
# vs 0.2578 on MI.  Constant WITHIN the Steam ladder, but not across datasets.
STEAM_BASE = ["Steam", "--epochs", "20", "--batch-size", "256",
              "--n-layers", "4", "--n-heads", "2", "--dropout", "0.5",
              "--encoder", "hstu", "--time-bias", "--pos-rab",
              "--label-smoothing", "0.2", "--causal-filter",
              "--filter-kernel", "16", "--text-sim-bias",
              "--text-prototypes", "512", "--lr-schedule", "warmup_cosine",
              "--temporal-split", "--temporal-inner-q", "0.60",
              "--temporal-outer-q", "0.75", "--eval-every", "5"]
STEAM_RUNGS = (64, 256)


def tag(loss, d, seed, lr=None, ds="MI"):
    suf = f"_lr{lr}" if lr else ""
    return f"results_SXL_{loss}_d{d}{suf}_{ds}_seed{seed}"


def cells(seeds=SEEDS):
    """Seed-major, then cheapest rung, then loss: a partial campaign always
    leaves a COMPLETE ladder for every loss at the seeds finished so far."""
    for seed in seeds:
        for d in RUNGS:
            for loss in LOSSES:
                yield loss, d, seed


def gpu_busy():
    try:
        o = subprocess.run(["nvidia-smi", "--query-gpu=memory.used",
                            "--format=csv,noheader,nounits"],
                           capture_output=True, text=True, timeout=30)
        return int(o.stdout.strip().splitlines()[0]) >= 6000
    except Exception:
        return False


def record_timing(name, secs):
    rec = {}
    if os.path.exists(TIMING_LOG):
        try:
            rec = json.load(open(TIMING_LOG, encoding="utf-8"))
        except Exception:
            rec = {}
    rec[name] = round(secs, 1)
    with open(TIMING_LOG, "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=1, sort_keys=True)


def run_cell(loss, d, seed, lr=None, ds="MI"):
    out = os.path.join(OUT, tag(loss, d, seed, lr, ds) + ".json")
    dst = out.replace(".json", ".degree_eval.json")
    ckpt = out.replace(".json", ".best.pt")
    if not os.path.exists(ckpt):
        base = STEAM_BASE if ds == "STEAM" else BASE
        cmd = ([sys.executable, "-u", TRAINER] + base + LOSSES[loss]
               + ["--d-model", str(d), "--save-ckpt",
                  "--seed", str(seed), "--out", out]
               + (["--lr", lr] if lr else []))
        print(f"TRAIN {tag(loss, d, seed, lr, ds)}", flush=True)
        t0 = time.time()
        with open(out.replace(".json", ".log"), "w", encoding="utf-8") as lf:
            rc = subprocess.run(cmd, stdout=lf,
                                stderr=subprocess.STDOUT).returncode
        secs = time.time() - t0
        if not os.path.exists(ckpt):
            print(f"  FAILED rc={rc} after {secs:.0f}s "
                  f"-- see {os.path.basename(out)}.log", flush=True)
            return False
        record_timing(tag(loss, d, seed, lr, ds), secs)
        print(f"  trained in {secs:.0f}s", flush=True)
    print(f"EVAL  {os.path.basename(dst)}", flush=True)
    with open(dst.replace(".json", ".log"), "w", encoding="utf-8") as lf:
        rc = subprocess.run([sys.executable, "-u", EVAL, out, "--out", dst,
                             "--event-stride", "2"],
                            stdout=lf, stderr=subprocess.STDOUT).returncode
    if rc != 0:
        print(f"  EVAL FAILED rc={rc}", flush=True)
        return False
    return True


def main():
    argv = sys.argv[1:]
    plan = "--plan" in argv
    timing = "--timing" in argv
    stage2 = "--stage2" in argv
    mx = next((int(a) for a in argv if a.isdigit()), 3)

    if "--steam" in argv:
        sseeds = (SEEDS + STAGE2_SEEDS) if stage2 else SEEDS
        todo = [(loss, d, s, None, "STEAM")
                for s in sseeds for d in STEAM_RUNGS for loss in LOSSES]
        todo = [c for c in todo
                if not os.path.exists(os.path.join(OUT, tag(*c) + ".degree_eval.json"))]
        if plan:
            print(f"Steam ({len(todo)} cell(s) remaining of "
                  f"{len(SEEDS)*len(STEAM_RUNGS)*len(LOSSES)}):")
            for c in todo:
                print(f"  {tag(*c)}")
            return
        done = 0
        for c in todo:
            if done >= mx:
                break
            if gpu_busy():
                print("GPU BUSY -- stopping.", flush=True)
                break
            if not run_cell(*c):
                sys.exit(1)
            done += 1
        print(f"[{done} Steam cell(s); {len(todo)-done} remaining]", flush=True)
        if len(todo) - done == 0:
            print("ALL DONE", flush=True)
        return

    if "--lrladder" in argv:
        # AMENDMENT A2 (post-hoc in origin, prediction+rule frozen first): the
        # full ladder re-run at lr=5e-4, n=5.  The 6 R1 cells already on disk
        # are the d=256/seed736-38 corner and are reused via skip-if-exists.
        todo = [(loss, d, s, R1_LR)
                for s in SEEDS + STAGE2_SEEDS for d in RUNGS for loss in LOSSES]
        todo = [c for c in todo
                if not os.path.exists(os.path.join(OUT, tag(*c) + ".degree_eval.json"))]
        if plan:
            print(f"A2 LR ladder ({len(todo)} cell(s) remaining of "
                  f"{len(SEEDS + STAGE2_SEEDS)*len(RUNGS)*len(LOSSES)}):")
            for c in todo[:6]:
                print(f"  {tag(*c)}")
            if len(todo) > 6:
                print(f"  ... and {len(todo)-6} more")
            return
        done = 0
        for c in todo:
            if done >= mx:
                break
            if gpu_busy():
                print("GPU BUSY -- stopping.", flush=True)
                break
            if not run_cell(*c):
                sys.exit(1)
            done += 1
        print(f"[{done} A2 cell(s); {len(todo)-done} remaining]", flush=True)
        if len(todo) - done == 0:
            print("ALL DONE", flush=True)
        return

    if "--r1" in argv:
        todo = [(loss, R1_RUNG, s, R1_LR) for s in SEEDS for loss in R1_LOSSES]
        todo = [c for c in todo
                if not os.path.exists(os.path.join(OUT, tag(*c) + ".degree_eval.json"))]
        if plan:
            print(f"R1 ({len(todo)} cell(s) remaining):")
            for c in todo:
                print(f"  {tag(*c)}")
            return
        done = 0
        for c in todo:
            if done >= mx:
                break
            if gpu_busy():
                print("GPU BUSY -- stopping.", flush=True)
                break
            if not run_cell(*c):
                sys.exit(1)
            done += 1
        print(f"[{done} R1 cell(s); {len(todo)-done} remaining]", flush=True)
        if len(todo) - done == 0:
            print("ALL DONE", flush=True)
        return

    seeds = (SEEDS + STAGE2_SEEDS) if stage2 else SEEDS
    todo = [c for c in cells(seeds)
            if not os.path.exists(os.path.join(OUT, tag(*c) + ".degree_eval.json"))]
    if plan:
        print(f"{len(todo)} cell(s) remaining of {len(seeds)*len(RUNGS)*len(LOSSES)}:")
        for loss, d, seed in todo:
            print(f"  {tag(loss, d, seed)}")
        return
    if timing:
        todo = [c for c in (("fce", 32, SEEDS[0]), ("fce", 256, SEEDS[0]))
                if c in todo]
        mx = len(todo)
        print("TIMING CALIBRATION only (PREREG S9): "
              + ", ".join(tag(*c) for c in todo), flush=True)

    done = 0
    for loss, d, seed in todo:
        if done >= mx:
            break
        if gpu_busy():
            print("GPU BUSY -- stopping.", flush=True)
            break
        if not run_cell(loss, d, seed):
            sys.exit(1)
        done += 1
    left = len(todo) - done
    print(f"[{done} cell(s) this invocation; {left} remaining]", flush=True)
    if left == 0:
        print("ALL DONE", flush=True)


if __name__ == "__main__":
    main()
