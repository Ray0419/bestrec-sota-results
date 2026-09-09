# -*- coding: utf-8 -*-
"""S6.6.1 attribution control: sampled-CE (256 negatives, CE form).

Isolates NEGATIVE COUNT from LOSS FORM in the gBCE-vs-full-CE comparison:
  full-CE   : all negatives,  CE form
  sampled-CE: 256 negatives,  CE form   <- this arm
  gBCE      : 256 negatives,  gBCE form (beta calibration)
If sampled-CE tracks gBCE on the tail, the damage is negative sampling.
If it tracks full-CE, the damage is the gBCE form/beta. Fair to gSASRec either way.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "poc_out")
TRAINER = os.path.join(HERE, "run_sasrec_sbert_temporal.py")
EVAL = os.path.join(HERE, "poc_temporal_eval.py")
SEEDS = (20260736, 20260737, 20260738)
BASE = ["Musical_Instruments", "--epochs", "20", "--batch-size", "256",
        "--d-model", "64", "--n-layers", "4", "--n-heads", "2",
        "--dropout", "0.5", "--encoder", "hstu", "--time-bias", "--pos-rab",
        "--causal-filter", "--filter-kernel", "16", "--text-sim-bias",
        "--text-prototypes", "512", "--lr-schedule", "warmup_cosine",
        "--temporal-split", "--sampled-negs", "256", "--eval-every", "20"]


def gpu_busy():
    try:
        o = subprocess.run(["nvidia-smi", "--query-gpu=memory.used",
                            "--format=csv,noheader,nounits"],
                           capture_output=True, text=True, timeout=30)
        return int(o.stdout.strip().splitlines()[0]) >= 6000
    except Exception:
        return False


def main():
    mx = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    done = todo = 0
    for seed in SEEDS:
        out = os.path.join(OUT, f"results_LOSS_sce_MI_seed{seed}.json")
        dst = out.replace(".json", ".degree_eval.json")
        if os.path.exists(dst):
            continue
        todo += 1
        if done >= mx:
            continue
        if gpu_busy():
            print("GPU BUSY — stopping.", flush=True)
            return
        if not os.path.exists(out.replace(".json", ".best.pt")):
            cmd = ([sys.executable, "-u", TRAINER] + BASE
                   + ["--save-ckpt", "--seed", str(seed), "--out", out])
            print(f"TRAIN {os.path.basename(out)}", flush=True)
            with open(out.replace(".json", ".log"), "w", encoding="utf-8") as lf:
                rc = subprocess.run(cmd, stdout=lf,
                                    stderr=subprocess.STDOUT).returncode
            if not os.path.exists(out.replace(".json", ".best.pt")):
                print(f"  FAILED rc={rc}", flush=True)
                sys.exit(1)
        print(f"EVAL  {os.path.basename(dst)}", flush=True)
        with open(dst.replace(".json", ".log"), "w", encoding="utf-8") as lf:
            rc = subprocess.run([sys.executable, "-u", EVAL, out, "--out", dst,
                                 "--event-stride", "2"],
                                stdout=lf, stderr=subprocess.STDOUT).returncode
        print(f"  rc={rc}", flush=True)
        if rc != 0:
            sys.exit(rc)
        done += 1
    print(f"[{done} this invocation; {todo-done} remaining]", flush=True)
    if todo - done == 0:
        print("ALL DONE", flush=True)


if __name__ == "__main__":
    main()
