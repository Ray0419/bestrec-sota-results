# -*- coding: utf-8 -*-
"""Launch one ID-only VG run with --save-ckpt for the POC (Next-2).

Rebuilds the exact TFV2 idonly config (run_coldfuse_confirm.base_args logic),
writes results + checkpoint to the worktree's poc_out. New files only.
"""
import json
import os
import subprocess
import sys

MAIN_RUN = r"C:\Users\rayxc\Documents\R\_bestrec_run"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "poc_out")
os.makedirs(OUT_DIR, exist_ok=True)

REF = os.path.join(MAIN_RUN, "results_TFV2_VG_idonly_seed20260851.json")
EXCLUDE = {"seed", "out", "category", "save_ckpt",
           "fir_v3", "fir_v3_kernel", "fir_v3_wd"}
SEED = 20260851

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

out = os.path.join(OUT_DIR, f"results_POC_VG_idonly_seed{SEED}.json")
cmd = [sys.executable, os.path.join(MAIN_RUN, "run_sasrec_sbert.py")] + argv + [
    "--save-ckpt", "--seed", str(SEED), "--out", out]
print("LAUNCH:", " ".join(cmd), flush=True)
rc = subprocess.run(cmd).returncode
print("DONE rc=", rc, flush=True)
sys.exit(rc)
