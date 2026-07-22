# -*- coding: utf-8 -*-
"""E-G stage-1 driver: exploratory cold/sparse fusion on MI, chained behind
E-F. Runs fuse_cold_eval.py on two E-F checkpoints (seeds 20260721-22),
then prints the mechanical promotion-rule precheck (VAL-only rule from
EXPERIMENT_PROGRAM.md E-G). Skip-if-exists; one GPU job at a time."""
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
SEEDS = (20260721, 20260722)
EF_STATUS = os.path.join(HERE, "ef_hybrid_v1_status.json")
STATUS = os.path.join(HERE, "eg_coldfuse_status.json")
TAIL_MIN_GAIN = 0.0005
NONINF = 0.0002


def wait_for_gpu():
    while True:
        state = None
        if os.path.exists(EF_STATUS):
            try:
                state = json.load(open(EF_STATUS, encoding="utf-8")).get("state")
            except Exception:
                state = None
        if state != "running":
            print(f"E-F state = {state!r} -> GPU free, starting E-G",
                  flush=True)
            return
        print("E-F still running; waiting 300 s", flush=True)
        time.sleep(300)


def main():
    wait_for_gpu()
    t0 = time.time()
    outs = []
    for seed in SEEDS:
        base = os.path.join(HERE, f"results_MI_HYBRIDV1_base_seed{seed}.json")
        out = os.path.join(
            HERE, f"results_Musical_Instruments_COLDFUSE_explore_seed{seed}.json")
        outs.append(out)
        if os.path.exists(out):
            print(f"[skip existing] {os.path.basename(out)}", flush=True)
            continue
        if not os.path.exists(base):
            print(f"MISSING base {base}", flush=True)
            json.dump({"state": "aborted"}, open(STATUS, "w"))
            return 1
        r = subprocess.run([PY, os.path.join(HERE, "fuse_cold_eval.py"), base])
        if r.returncode != 0:
            print(f"FAILED seed {seed} (exit {r.returncode})", flush=True)
            json.dump({"state": "aborted"}, open(STATUS, "w"))
            return 1
        json.dump({"state": "running", "done": len([o for o in outs
                                                    if os.path.exists(o)]),
                   "elapsed_min": round((time.time() - t0) / 60, 1)},
                  open(STATUS, "w"))

    # mechanical promotion precheck (VAL-only rule; test never consulted)
    verdict = {"rule": {"noninferiority": NONINF,
                        "tail_min_gain": TAIL_MIN_GAIN},
               "per_seed": [], "promote": True}
    for out in outs:
        d = json.load(open(out, encoding="utf-8"))
        ref = d["fused2"]["val"]
        rows = {}
        for label in ("selected_global", "selected_binned"):
            v = d[label]["val"]
            rows[label] = {
                "overall_ok": bool(v["ndcg"] >= ref["ndcg"] - NONINF),
                "tail_gain": v["tail"]["ndcg"] - ref["tail"]["ndcg"],
                "combo": d[label]["combo"]}
        seed_ok = any(r["overall_ok"] and r["tail_gain"] >= TAIL_MIN_GAIN
                      for r in rows.values())
        verdict["per_seed"].append({"seed": d["seed"], "rows": rows,
                                    "seed_ok": bool(seed_ok)})
        verdict["promote"] = bool(verdict["promote"] and seed_ok)
    json.dump(verdict, open(os.path.join(
        HERE, "eg_coldfuse_explore_verdict.json"), "w", encoding="utf-8"),
        indent=2)
    print("E-G PRECHECK:", "PROMOTE (both seeds pass the VAL rule)"
          if verdict["promote"] else "DO NOT PROMOTE (rule failed)",
          flush=True)
    json.dump({"state": "complete", "promote": verdict["promote"],
               "elapsed_min": round((time.time() - t0) / 60, 1)},
              open(STATUS, "w"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
