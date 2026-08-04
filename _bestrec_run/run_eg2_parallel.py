# -*- coding: utf-8 -*-
"""PREREG_COLDFUSE_V2 driver (E-G2): TWO GPU lanes in parallel (maintainer
directive 2026-07-23: use idle capacity), with the audit-15:59 OPS ledger.

Lane A: MI + IS (small-memory categories). Lane B: VG + OFFICE + CDS.
Peak GPU memory ~4 GB + ~9 GB < 16 GB. Each lane runs its per-(cat,seed)
pipeline sequentially: train (--no-test-eval --save-ckpt) -> fusion
(--val-only, MI/IS/VG) -> confirm2 (sequestered test).

OPS: append-only JSONL ledger (_bestrec_run/attempts/eg2_ledger.jsonl) with
launch commit + dirty-diff sha + command + phase events; atomic status
(temp+rename); per-launch dirty patch snapshot; skip-if-exists; a lane
aborts after 3 failures. Progress monitoring is FILE COUNTS ONLY -- no
endpoint value is ever printed by this driver or by the sequestered confirm.
"""
import hashlib
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PY = sys.executable
TRAINER = os.path.join(HERE, "run_sasrec_sbert.py")
FUSER = os.path.join(HERE, "fuse_ease_eval.py")
CONFIRM = os.path.join(HERE, "fuse_cold_confirm2.py")
SEEDS = (20260741, 20260742, 20260743, 20260744,
         20260745, 20260746, 20260747, 20260748)
L2_GRID = "50,100,200,500"
W_GRID = "0.01,0.02,0.03,0.04,0.05,0.06,0.075,0.1"
CATS = {
    "MI": ("results_MI_V2_ls02_filter16_seed20260608.json", True, "A"),
    "IS": ("results_FIRB_Industrial_and_Scientific_filter_seed20260713.json",
           True, "A"),
    "VG": ("results_V2_ls02_filter8_seed20260610_VG.json", True, "B"),
    "OFFICE": ("results_OFFICEV3_k16_seed20260728.json", False, "B"),
    "CDS": ("results_FIRB_CDs_and_Vinyl_filter_seed20260713.json", False, "B"),
}
EXCLUDE = {"seed", "out", "category", "save_ckpt", "no_test_eval",
           "fir_v3", "fir_v3_kernel", "fir_v3_wd"}
ATT = os.path.join(HERE, "attempts")
LEDGER = os.path.join(ATT, "eg2_ledger.jsonl")
STATUS = os.path.join(HERE, "eg2_status.json")
_ledger_lock = threading.Lock()
_status_lock = threading.Lock()
_counts = {"done": 0, "skipped": 0, "failed": 0}


def now():
    return datetime.now(timezone.utc).isoformat()


def emit(event):
    with _ledger_lock:
        with open(LEDGER, "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": now(), **event}) + "\n")


def status(state):
    with _status_lock:
        tmp = STATUS + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"state": state, **_counts,
                       "ts": now()}, f)
        os.replace(tmp, STATUS)


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


def step(lane, tag, seed, phase, exists_path, cmd):
    if os.path.exists(exists_path):
        _counts["skipped"] += 1
        emit({"lane": lane, "cat": tag, "seed": seed, "phase": phase,
              "event": "skip", "artifact": os.path.basename(exists_path)})
        return True
    emit({"lane": lane, "cat": tag, "seed": seed, "phase": phase,
          "event": "launch", "cmd": " ".join(cmd)})
    t0 = time.time()
    r = subprocess.run(cmd, cwd=ROOT)
    ok = r.returncode == 0
    emit({"lane": lane, "cat": tag, "seed": seed, "phase": phase,
          "event": "done" if ok else "fail", "rc": r.returncode,
          "dur_s": round(time.time() - t0, 1)})
    _counts["done" if ok else "failed"] += 1
    status("running")
    return ok


def lane_worker(lane, tags):
    failures = 0
    for seed in SEEDS:
        for tag in tags:
            ref, use_ease, _ = CATS[tag]
            cat = json.load(open(os.path.join(HERE, ref),
                                 encoding="utf-8"))["config"]["category"]
            b = os.path.join(HERE, f"results_{tag}_COLDFUSE2_base_seed{seed}.json")
            if not step(lane, tag, seed, "train", b,
                        [PY, TRAINER] + base_args(ref) +
                        ["--save-ckpt", "--no-test-eval",
                         "--seed", str(seed), "--out", b]):
                failures += 1
                if failures >= 3:
                    emit({"lane": lane, "event": "lane_abort"})
                    return
                continue
            if use_ease:
                fj = b[:-5] + ".fusion.json"
                if not step(lane, tag, seed, "fusion", fj,
                            [PY, FUSER, b, "--ease-l2", L2_GRID,
                             "--fusion-weights", W_GRID, "--val-only",
                             "--out", fj]):
                    failures += 1
                    if failures >= 3:
                        emit({"lane": lane, "event": "lane_abort"})
                        return
                    continue
            cj = os.path.join(HERE,
                              f"results_{cat}_COLDFUSE2_confirm_seed{seed}.json")
            ccmd = [PY, CONFIRM, b, "--out", cj]
            if not use_ease:
                ccmd.insert(3, "--no-ease")
            if not step(lane, tag, seed, "confirm", cj, ccmd):
                failures += 1
                if failures >= 3:
                    emit({"lane": lane, "event": "lane_abort"})
                    return


def preflight():
    helptxt = subprocess.run([PY, TRAINER, "--help"], capture_output=True,
                             text=True).stdout
    ok = "--no-test-eval" in helptxt
    print(f"PREFLIGHT trainer --no-test-eval: {'OK' if ok else 'MISSING'}")
    for tag, (ref, _, lane) in CATS.items():
        if not os.path.exists(os.path.join(HERE, ref)):
            print(f"PREFLIGHT FAIL: missing reference {ref}")
            ok = False
            continue
        cmd = base_args(ref)
        bad = [a for a in cmd if a.startswith("--") and a not in helptxt]
        if bad:
            print(f"PREFLIGHT FAIL ({tag}): unknown flags {bad}")
            ok = False
        else:
            print(f"PREFLIGHT OK ({tag}, lane {lane}): "
                  f"{sum(a.startswith('--') for a in cmd)} flags")
    return 0 if ok else 1


def main():
    if "--preflight" in sys.argv:
        return preflight()
    if preflight() != 0:
        return 1
    os.makedirs(ATT, exist_ok=True)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                            capture_output=True, text=True).stdout.strip()
    diff = subprocess.run(["git", "diff"], cwd=ROOT, capture_output=True,
                          text=True).stdout
    diff_sha = hashlib.sha256(diff.encode("utf-8", "replace")).hexdigest()
    patch_path = os.path.join(
        ATT, f"eg2_dirty_{diff_sha[:12]}.patch")
    if diff and not os.path.exists(patch_path):
        with open(patch_path, "w", encoding="utf-8") as f:
            f.write(diff)
    emit({"event": "campaign_launch", "commit": commit,
          "dirty_diff_sha256": diff_sha,
          "dirty_patch": os.path.basename(patch_path) if diff else None,
          "seeds": list(SEEDS), "lanes": {"A": ["MI", "IS"],
                                          "B": ["VG", "OFFICE", "CDS"]}})
    status("running")
    t0 = time.time()
    ta = threading.Thread(target=lane_worker, args=("A", ["MI", "IS"]))
    tb = threading.Thread(target=lane_worker, args=("B", ["VG", "OFFICE",
                                                          "CDS"]))
    ta.start()
    tb.start()
    ta.join()
    tb.join()
    state = "complete" if _counts["failed"] == 0 else "complete_with_failures"
    status(state)
    emit({"event": "campaign_end", "state": state, **_counts,
          "wall_min": round((time.time() - t0) / 60, 1)})
    print(f"E-G2 DONE: {_counts} in {(time.time()-t0)/60:.1f} min", flush=True)
    return 0 if _counts["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
