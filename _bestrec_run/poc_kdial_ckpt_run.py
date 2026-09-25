# -*- coding: utf-8 -*-
"""k-dial runs WITH --save-ckpt: the exchange-rate scaling test.

Usage: poc_kdial_ckpt_run.py [cap_frac]
  cap_frac 0.25 -> 3,090 manufactured cold items (~20% of eval targets)
  cap_frac 0.0  -> ANCHOR: only MI's 31 natural cold items

Running both gives the SAME dataset / architecture / seed at two cold-catalog
sizes, isolating how the warm externality scales with the number of imputed
rows (the VG-vs-MI comparison confounds dataset with prevalence).
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MAIN_RUN = r"C:\Users\rayxc\Documents\R\_bestrec_run"
OUT_DIR = os.path.join(HERE, "poc_out")
TRAINER = os.path.join(HERE, "run_sasrec_sbert_kdial.py")
REF = os.path.join(MAIN_RUN, "results_MI_COLDFUSE_base_seed20260736.json")
SEED = 20260736
EXCLUDE = {"seed", "out", "category", "save_ckpt", "eval_every",
           "fir_v3", "fir_v3_kernel", "fir_v3_wd", "zfusion_sweep"}

cap_frac = float(sys.argv[1]) if len(sys.argv) > 1 else 0.25
# 0.25 keeps the historical "k0" tag so the two runs already on disk are reused
tag = ("anchor" if cap_frac == 0.0 else
       "k0" if cap_frac == 0.25 else f"k0f{cap_frac:g}")

cfg = json.load(open(REF, encoding="utf-8"))["config"]
argv = [cfg["category"]]
for k in sorted(cfg):
    if k in EXCLUDE or cfg[k] is None or cfg[k] is False:
        continue
    flag = "--" + k.replace("_", "-")
    if cfg[k] is True:
        argv.append(flag)
    else:
        argv += [flag, str(cfg[k])]

out = os.path.join(OUT_DIR, f"results_KDIALCK_text_{tag}_MI_seed{SEED}.json")
if os.path.exists(out):
    print("SKIP (exists)", os.path.basename(out))
    sys.exit(0)
cap_args = ([] if cap_frac == 0.0 else
            ["--item-cap-k", "0", "--item-cap-frac", str(cap_frac),
             "--item-cap-seed", "7"])
cmd = [sys.executable, "-u", TRAINER] + argv + cap_args + [
    "--eval-every", "5", "--save-ckpt", "--seed", str(SEED), "--out", out]
log = out.replace(".json", ".log")
print("LAUNCH", os.path.basename(out), flush=True)
with open(log, "w", encoding="utf-8") as lf:
    rc = subprocess.run(cmd, stdout=lf, stderr=subprocess.STDOUT).returncode
print("DONE rc=", rc, flush=True)
sys.exit(rc)
