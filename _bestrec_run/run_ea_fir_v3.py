# -*- coding: utf-8 -*-
"""E-A driver (PREREG_FIR_V3): 3 arms x 8 seeds, strictly sequential.

Commands are constructed MECHANICALLY from the frozen reference config
(results_MI_V2_ls02_filter16_seed20260608.json), excluding only the component
under test (causal_filter/filter_kernel) and per-run fields (seed/out).
Never overwrites an existing results file (resume = skip). One GPU job at a
time by construction. --preflight validates every flag against the trainer's
--help text and prints the first full command without launching anything.
"""
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
TRAINER = os.path.join(HERE, "run_sasrec_sbert.py")
REF = os.path.join(HERE, "results_MI_V2_ls02_filter16_seed20260608.json")
EXCLUDE = {"causal_filter", "filter_kernel", "seed", "out",
           "fir_v3", "fir_v3_kernel", "fir_v3_wd",
           "category"}  # positional, prepended in cmd_for()
ARMS = (("a0ident", "frozen", "backbone"),
        ("a1learned", "learned", "backbone"),
        ("a2learnedwd0", "learned", "zero"))
SEEDS = (20260713, 20260714, 20260715, 20260716,
         20260717, 20260718, 20260719, 20260720)
STATUS = os.path.join(HERE, "ea_fir_v3_status.json")


def base_args():
    cfg = json.load(open(REF, encoding="utf-8"))["config"]
    argv = []
    for k in sorted(cfg):
        if k in EXCLUDE:
            continue
        v = cfg[k]
        if v is None or v is False:
            continue
        flag = "--" + k.replace("_", "-")
        if v is True:
            argv.append(flag)
        else:
            argv += [flag, str(v)]
    return argv


def cmd_for(arm, fir, wd, seed):
    cat = json.load(open(REF, encoding="utf-8"))["config"]["category"]
    out = os.path.join(HERE, f"results_MI_FIRV3_{arm}_seed{seed}.json")
    return out, [PY, TRAINER, cat] + base_args() + [
        "--fir-v3", fir, "--fir-v3-wd", wd, "--fir-v3-kernel", "16",
        "--seed", str(seed), "--out", out]


def preflight():
    helptxt = subprocess.run([PY, TRAINER, "--help"], capture_output=True,
                             text=True).stdout
    _, cmd = cmd_for(*ARMS[0], SEEDS[0])
    flags = [a for a in cmd if a.startswith("--")]
    bad = [f for f in flags if f not in helptxt]
    if bad:
        print("PREFLIGHT FAIL: unknown flags:", bad)
        return 1
    print("PREFLIGHT OK:", len(flags), "flags validated against --help")
    print("first command:\n ", " ".join(cmd))
    return 0


def main():
    if "--preflight" in sys.argv:
        return preflight()
    if preflight() != 0:
        return 1
    t0 = time.time()
    done = skipped = failed = 0
    total = len(ARMS) * len(SEEDS)
    for seed in SEEDS:          # seed-major: init-hash triplets complete early
        for arm, fir, wd in ARMS:
            out, cmd = cmd_for(arm, fir, wd, seed)
            tag = os.path.basename(out)
            if os.path.exists(out):
                skipped += 1
                print(f"[skip existing] {tag}", flush=True)
                continue
            print(f"[{done + skipped + failed + 1}/{total}] {tag}", flush=True)
            r = subprocess.run(cmd, cwd=os.path.dirname(HERE))
            if r.returncode != 0:
                failed += 1
                print(f"RUN FAILED (exit {r.returncode}): {tag}", flush=True)
                if failed >= 2:
                    print("aborting after 2 failures", flush=True)
                    _status(done, skipped, failed, total, t0, "aborted")
                    return 1
            else:
                done += 1
            _status(done, skipped, failed, total, t0, "running")
    _status(done, skipped, failed, total, t0, "complete")
    print(f"E-A DRIVER COMPLETE: {done} ran, {skipped} skipped, "
          f"{failed} failed, {(time.time() - t0) / 60:.1f} min", flush=True)
    return 0 if failed == 0 else 1


def _status(done, skipped, failed, total, t0, state):
    with open(STATUS, "w", encoding="utf-8") as f:
        json.dump({"state": state, "ran": done, "skipped": skipped,
                   "failed": failed, "total": total,
                   "elapsed_min": round((time.time() - t0) / 60, 1)}, f)


if __name__ == "__main__":
    sys.exit(main())
