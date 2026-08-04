# -*- coding: utf-8 -*-
"""Canonical-FIR breadth transfer campaign driver (PREREG_FIR_CANONICAL_BREADTH).

Purpose: extend the CANONICAL (nonsingular, gradient-active, identity-initialized)
causal FIR residual -- the E-A `--fir-v3` parameterization, already isolated on
Musical_Instruments (PREREG_FIR_V3, verdict W-POS) -- to two categories NOT used
in the filter's development (Industrial_and_Scientific, CDs_and_Vinyl), under the
SAME frozen primary configuration with ZERO per-category tuning.

Two matched-initialization arms per seed, per category:
  a0ident   : --fir-v3 frozen   (delta kernel held at 0 -> exact identity control)
  a1learned : --fir-v3 learned   (canonical gradient-active FIR)
Both arms share one backbone initial state per (category, seed); the committed
adjudicator enforces per-(category,seed) init_state_sha256 equality.

Config is constructed MECHANICALLY from the frozen MI primary reference
(results_MI_V2_ls02_filter16_seed20260608.json), excluding only the legacy filter
component, the fir-v3 flags (set here), the positional category, and per-run fields
(seed/out). Nothing category-specific is tuned. Strictly sequential (one GPU job at
a time); resume=skip; never overwrites an existing results_*.json.

  python _bestrec_run/run_fir_canonical_breadth.py --preflight   # validate, no launch
  python _bestrec_run/run_fir_canonical_breadth.py               # run the queue
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
           "fir_v3", "fir_v3_kernel", "fir_v3_wd", "category"}
CATEGORIES = ("Industrial_and_Scientific", "CDs_and_Vinyl")
ARMS = (("a0ident", "frozen"), ("a1learned", "learned"))
SEEDS = (20260810, 20260811, 20260812, 20260813,
         20260814, 20260815, 20260816, 20260817)
KERNEL = "16"
STATUS = os.path.join(HERE, "fir_canonical_breadth_status.json")


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


def cmd_for(cat, arm, fir, seed):
    out = os.path.join(HERE, f"results_{cat}_FIRCANON_{arm}_seed{seed}.json")
    return out, [PY, TRAINER, cat] + base_args() + [
        "--fir-v3", fir, "--fir-v3-wd", "backbone", "--fir-v3-kernel", KERNEL,
        "--seed", str(seed), "--out", out]


def preflight():
    # --help text contains a Unicode char; force utf-8 so it doesn't die on the
    # Windows cp1252 console (trainer runs are unaffected -- this is help output only).
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    helptxt = subprocess.run([PY, TRAINER, "--help"], capture_output=True,
                             text=True, env=env, encoding="utf-8").stdout or ""
    _, cmd = cmd_for(CATEGORIES[0], *ARMS[0], SEEDS[0])
    flags = [a for a in cmd if a.startswith("--")]
    bad = [f for f in flags if f not in helptxt]
    if bad:
        print("PREFLIGHT FAIL: unknown flags:", bad)
        return 1
    print("PREFLIGHT OK:", len(flags), "flags validated against --help")
    print("categories:", CATEGORIES, "| arms:", [a[0] for a in ARMS],
          "| seeds:", SEEDS)
    print("first command:\n ", " ".join(cmd))
    return 0


def main():
    if "--preflight" in sys.argv:
        return preflight()
    if preflight() != 0:
        return 1
    t0 = time.time()
    done = skipped = failed = 0
    total = len(CATEGORIES) * len(ARMS) * len(SEEDS)
    for cat in CATEGORIES:
        for seed in SEEDS:                 # seed-major: init-pairs complete early
            for arm, fir in ARMS:
                out, cmd = cmd_for(cat, arm, fir, seed)
                tag = os.path.basename(out)
                if os.path.exists(out):
                    skipped += 1
                    print(f"[skip existing] {tag}", flush=True)
                    continue
                print(f"[{done + skipped + failed + 1}/{total}] {tag}",
                      flush=True)
                r = subprocess.run(cmd, cwd=os.path.dirname(HERE))
                if r.returncode != 0:
                    failed += 1
                    print(f"RUN FAILED (exit {r.returncode}): {tag}",
                          flush=True)
                    if failed >= 2:
                        print("aborting after 2 failures", flush=True)
                        _status(done, skipped, failed, total, t0, "aborted")
                        return 1
                else:
                    done += 1
                _status(done, skipped, failed, total, t0, "running")
    _status(done, skipped, failed, total, t0, "complete")
    print(f"CANONICAL-BREADTH DRIVER COMPLETE: {done} ran, {skipped} skipped, "
          f"{failed} failed, {(time.time() - t0) / 60:.1f} min", flush=True)
    return 0 if failed == 0 else 1


def _status(done, skipped, failed, total, t0, state):
    with open(STATUS, "w", encoding="utf-8") as f:
        json.dump({"state": state, "ran": done, "skipped": skipped,
                   "failed": failed, "total": total,
                   "elapsed_min": round((time.time() - t0) / 60, 1)}, f)


if __name__ == "__main__":
    sys.exit(main())
