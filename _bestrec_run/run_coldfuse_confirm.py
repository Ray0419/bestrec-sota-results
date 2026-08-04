# -*- coding: utf-8 -*-
"""PREREG_COLDFUSE_V1 driver (E-G stage 2): 5 categories x 5 fresh seeds.

Per seed: train base (--save-ckpt, mechanical config from the frozen
reference) -> MI/IS/VG: frozen PREREG_HYBRID_V1 fusion (fuse_ease_eval)
-> streaming confirm (fuse_cold_confirm). Refuses to start while any
earlier campaign status reports running; skip-if-exists; sequential."""
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
TRAINER = os.path.join(HERE, "run_sasrec_sbert.py")
FUSER = os.path.join(HERE, "fuse_ease_eval.py")
CONFIRM = os.path.join(HERE, "fuse_cold_confirm.py")
SEEDS = (20260736, 20260737, 20260738, 20260739, 20260740)
L2_GRID = "50,100,200,500"
W_GRID = "0.01,0.02,0.03,0.04,0.05,0.06,0.075,0.1"
CATS = (  # (tag, reference results JSON, use_ease)
    ("MI", "results_MI_V2_ls02_filter16_seed20260608.json", True),
    ("IS", "results_FIRB_Industrial_and_Scientific_filter_seed20260713.json",
     True),
    ("VG", "results_V2_ls02_filter8_seed20260610_VG.json", True),
    ("OFFICE", "results_OFFICEV3_k16_seed20260728.json", False),
    ("CDS", "results_FIRB_CDs_and_Vinyl_filter_seed20260713.json", False),
)
EXCLUDE = {"seed", "out", "category", "save_ckpt",
           "fir_v3", "fir_v3_kernel", "fir_v3_wd"}
STATUS = os.path.join(HERE, "coldfuse_confirm_status.json")
PRIOR = ("ea_fir_v3_status.json", "ef_hybrid_v1_status.json",
         "eg_coldfuse_status.json")


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
    out = os.path.join(HERE, f"results_{tag}_COLDFUSE_base_seed{seed}.json")
    return out, [PY, TRAINER] + base_args(ref) + [
        "--save-ckpt", "--seed", str(seed), "--out", out]


def preflight():
    helptxt = subprocess.run([PY, TRAINER, "--help"], capture_output=True,
                             text=True).stdout
    ok = True
    for tag, ref, _ in CATS:
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
    return 0 if ok else 1


def wait_for_gpu():
    while True:
        busy = []
        for f in PRIOR:
            p = os.path.join(HERE, f)
            if os.path.exists(p):
                try:
                    if json.load(open(p, encoding="utf-8")).get("state") == \
                            "running":
                        busy.append(f)
                except Exception:
                    pass
        if not busy:
            print("no prior campaign running -> starting", flush=True)
            return
        print(f"waiting on {busy}; 300 s", flush=True)
        time.sleep(300)


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

    def step(exists_path, cmd, tag):
        nonlocal done, skipped, failed
        if os.path.exists(exists_path):
            skipped += 1
            print(f"[skip existing] {os.path.basename(exists_path)}",
                  flush=True)
            return True
        rc = run(cmd, tag)
        if rc != 0:
            failed += 1
            return False
        done += 1
        return True

    for tag, ref, use_ease in CATS:
        cfgcat = json.load(open(os.path.join(HERE, ref),
                                encoding="utf-8"))["config"]["category"]
        for seed in SEEDS:
            base, cmd = train_cmd(tag, ref, seed)
            if not step(base, cmd, os.path.basename(base)):
                if failed >= 2:
                    _status("aborted", done, skipped, failed, t0)
                    return 1
                continue
            if use_ease:
                fj = base[:-5] + ".fusion.json"
                if not step(fj, [PY, FUSER, base, "--ease-l2", L2_GRID,
                                 "--fusion-weights", W_GRID, "--out", fj],
                            os.path.basename(fj)):
                    if failed >= 2:
                        _status("aborted", done, skipped, failed, t0)
                        return 1
                    continue
            cj = os.path.join(
                HERE, f"results_{cfgcat}_COLDFUSE_confirm_seed{seed}.json")
            ccmd = [PY, CONFIRM, base, "--out", cj]
            if not use_ease:
                ccmd.insert(3, "--no-ease")
            if not step(cj, ccmd, os.path.basename(cj)):
                if failed >= 2:
                    _status("aborted", done, skipped, failed, t0)
                    return 1
            _status("running", done, skipped, failed, t0)
    _status("complete" if failed == 0 else "complete_with_failures",
            done, skipped, failed, t0)
    print(f"COLDFUSE CONFIRM DONE: {done} ran, {skipped} skipped, "
          f"{failed} failed, {(time.time() - t0) / 60:.1f} min", flush=True)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
