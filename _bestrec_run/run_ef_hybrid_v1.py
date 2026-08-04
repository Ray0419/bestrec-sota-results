# -*- coding: utf-8 -*-
"""E-F driver (PREREG_HYBRID_V1): EASE late-fusion hybrid, 3 categories x
5 fresh seeds, strictly sequential, chained behind E-A.

Per category: train the frozen reference stack with --save-ckpt (commands
constructed MECHANICALLY from the frozen per-category reference results JSON,
excluding only seed/out), then run fuse_ease_eval.py per seed (frozen l2/w
grids, val-only selection), then -- MI only -- ensemble_fuse_eval.py over the
five checkpoints with the modal val-selected l2 (ties toward smaller).

Never overwrites results_*.json / *.fusion.json (resume = skip). Waits for
the E-A driver to release the GPU before the first job (one GPU job at a
time). --preflight validates every flag and prints commands without running.
"""
import json
import os
import subprocess
import sys
import time
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
TRAINER = os.path.join(HERE, "run_sasrec_sbert.py")
FUSER = os.path.join(HERE, "fuse_ease_eval.py")
ENSEMBLER = os.path.join(HERE, "ensemble_fuse_eval.py")
SEEDS = (20260721, 20260722, 20260723, 20260724, 20260725)
L2_GRID = "50,100,200,500"
W_GRID = "0.01,0.02,0.03,0.04,0.05,0.06,0.075,0.1"
CATS = (  # (tag, frozen reference results JSON)
    ("MI", "results_MI_V2_ls02_filter16_seed20260608.json"),
    ("IS", "results_FIRB_Industrial_and_Scientific_filter_seed20260713.json"),
    ("VG", "results_V2_ls02_filter8_seed20260610_VG.json"),
)
EXCLUDE = {"seed", "out", "category", "save_ckpt",
           "fir_v3", "fir_v3_kernel", "fir_v3_wd"}
STATUS = os.path.join(HERE, "ef_hybrid_v1_status.json")
EA_STATUS = os.path.join(HERE, "ea_fir_v3_status.json")


def base_args(ref):
    cfg = json.load(open(os.path.join(HERE, ref), encoding="utf-8"))["config"]
    argv = [cfg["category"]]
    for k in sorted(cfg):
        if k in EXCLUDE or cfg[k] is None or cfg[k] is False:
            continue
        flag = "--" + k.replace("_", "-")
        if cfg[k] is True:
            argv.append(flag)
        else:
            argv += [flag, str(cfg[k])]
    return argv


def train_cmd(tag, ref, seed):
    out = os.path.join(HERE, f"results_{tag}_HYBRIDV1_base_seed{seed}.json")
    return out, [PY, TRAINER] + base_args(ref) + [
        "--save-ckpt", "--seed", str(seed), "--out", out]


def fuse_cmd(base_json):
    out = base_json[:-5] + ".fusion.json"
    return out, [PY, FUSER, base_json, "--ease-l2", L2_GRID,
                 "--fusion-weights", W_GRID, "--out", out]


def preflight():
    helptxt = subprocess.run([PY, TRAINER, "--help"], capture_output=True,
                             text=True).stdout
    ok = True
    for tag, ref in CATS:
        if not os.path.exists(os.path.join(HERE, ref)):
            print(f"PREFLIGHT FAIL: missing reference {ref}")
            ok = False
            continue
        _, cmd = train_cmd(tag, ref, SEEDS[0])
        bad = [a for a in cmd if a.startswith("--") and a not in helptxt]
        if bad:
            print(f"PREFLIGHT FAIL ({tag}): unknown flags {bad}")
            ok = False
        else:
            print(f"PREFLIGHT OK ({tag}): "
                  f"{sum(a.startswith('--') for a in cmd)} flags")
            print("  ", " ".join(cmd))
    return 0 if ok else 1


def wait_for_gpu():
    while True:
        state = None
        if os.path.exists(EA_STATUS):
            try:
                state = json.load(open(EA_STATUS, encoding="utf-8")).get("state")
            except Exception:
                state = None
        if state != "running":
            print(f"E-A state = {state!r} -> GPU free, starting E-F", flush=True)
            return
        print("E-A still running; waiting 120 s", flush=True)
        time.sleep(120)


def run(cmd, tag):
    print(f"[run] {tag}", flush=True)
    r = subprocess.run(cmd, cwd=os.path.dirname(HERE))
    if r.returncode != 0:
        print(f"RUN FAILED (exit {r.returncode}): {tag}", flush=True)
    return r.returncode


def _status(state, done, skipped, failed, t0):
    with open(STATUS, "w", encoding="utf-8") as f:
        json.dump({"state": state, "done": done, "skipped": skipped,
                   "failed": failed,
                   "elapsed_min": round((time.time() - t0) / 60, 1)}, f)


def main():
    if "--preflight" in sys.argv:
        return preflight()
    if preflight() != 0:
        return 1
    wait_for_gpu()
    t0 = time.time()
    done = skipped = failed = 0
    mi_bases = []
    for tag, ref in CATS:
        for seed in SEEDS:
            base, cmd = train_cmd(tag, ref, seed)
            if tag == "MI":
                mi_bases.append(base)
            if os.path.exists(base):
                skipped += 1
                print(f"[skip existing] {os.path.basename(base)}", flush=True)
            else:
                rc = run(cmd, os.path.basename(base))
                if rc != 0:
                    failed += 1
                    if failed >= 2:
                        _status("aborted", done, skipped, failed, t0)
                        return 1
                    continue
                done += 1
            fout, fcmd = fuse_cmd(base)
            if os.path.exists(fout):
                skipped += 1
                print(f"[skip existing] {os.path.basename(fout)}", flush=True)
            else:
                rc = run(fcmd, os.path.basename(fout))
                if rc != 0:
                    failed += 1
                    if failed >= 2:
                        _status("aborted", done, skipped, failed, t0)
                        return 1
                else:
                    done += 1
            _status("running", done, skipped, failed, t0)

    # MI ensemble (secondary endpoint): modal val-selected l2, ties -> smaller
    ens_out = os.path.join(HERE, "results_MI_HYBRIDV1_ensemble5.json")
    if os.path.exists(ens_out):
        print("[skip existing] ensemble5", flush=True)
    else:
        l2s = []
        for b in mi_bases:
            f = b[:-5] + ".fusion.json"
            if os.path.exists(f):
                l2s.append(float(json.load(open(f, encoding="utf-8"))
                                 ["selected"]["l2"]))
        if len(l2s) == len(SEEDS):
            modal = sorted(Counter(l2s).items(),
                           key=lambda kv: (-kv[1], kv[0]))[0][0]
            print(f"ensemble EASE l2 = modal({l2s}) = {modal}", flush=True)
            rc = run([PY, ENSEMBLER] + mi_bases + [
                "--ease-l2", str(modal), "--fusion-weights", W_GRID,
                "--out", ens_out], "ensemble5")
            failed += (rc != 0)
            done += (rc == 0)
        else:
            print("ensemble skipped: missing MI fusion selections", flush=True)
    _status("complete" if failed == 0 else "complete_with_failures",
            done, skipped, failed, t0)
    print(f"E-F DRIVER DONE: {done} ran, {skipped} skipped, {failed} failed, "
          f"{(time.time() - t0) / 60:.1f} min", flush=True)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
