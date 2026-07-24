# -*- coding: utf-8 -*-
"""Generate PREREG_TEXTPERM_V1 (E-B) shard files for N pods.

30 pipelines (train --no-test-eval --save-ckpt -> sequestered final eval):
  2 categories x { aligned x3 seeds, permA/B/C x3 seeds, random x3 seeds }.
Round-robin by estimated runtime. Usage:
  python cloud/make_shards_eb.py --pods 8
"""
import argparse
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEEDS = (20260749, 20260750, 20260751)
REFS = {"MI": ("results_MI_V2_ls02_filter16_seed20260608.json",
               "Musical_Instruments", 16),
        "VG": ("results_V2_ls02_filter8_seed20260610_VG.json",
               "Video_Games", 15)}
ARMS = ("aligned", "permA", "permB", "permC", "random")
EXCLUDE = {"seed", "out", "category", "save_ckpt", "no_test_eval",
           "encoder_cache", "fir_v3", "fir_v3_kernel", "fir_v3_wd"}


def base_args(ref):
    cfg = json.load(open(os.path.join(ROOT, "_bestrec_run", ref),
                         encoding="utf-8"))["config"]
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pods", type=int, default=8)
    args = ap.parse_args()
    jobs = []
    for tag, (ref, cat, minutes) in REFS.items():
        for arm in ARMS:
            for seed in SEEDS:
                out = f"_bestrec_run/results_{tag}_TEXTPERM_{arm}_seed{seed}.json"
                cmd = (["python", "_bestrec_run/run_sasrec_sbert.py"]
                       + base_args(ref)
                       + ["--save-ckpt", "--no-test-eval",
                          "--seed", str(seed), "--out", out])
                if arm != "aligned":
                    cmd += ["--encoder-cache",
                            f"cache_5core/controls/{cat}__{arm}.npy"]
                jobs.append({"id": f"{tag}_{arm}_{seed}", "minutes": minutes,
                             "artifact": out,
                             "steps": [
                                 {"phase": "train", "exists": out, "cmd": cmd},
                                 {"phase": "finaleval",
                                  "exists": out[:-5] + ".finaleval.json",
                                  "cmd": ["python", "cloud/eval_final_model.py",
                                          out]}]})
    jobs.sort(key=lambda j: -j["minutes"])
    shards = [{"shard": i, "jobs": []} for i in range(args.pods)]
    loads = [0.0] * args.pods
    for j in jobs:
        i = loads.index(min(loads))
        shards[i]["jobs"].append(j)
        loads[i] += j["minutes"]
    os.makedirs(os.path.join(ROOT, "cloud", "shards"), exist_ok=True)
    for s in shards:
        p = os.path.join(ROOT, "cloud", "shards", f"eb_shard{s['shard']}.json")
        json.dump(s, open(p, "w", encoding="utf-8"), indent=1)
        print(f"shard {s['shard']}: {len(s['jobs'])} jobs, "
              f"~{loads[s['shard']]:.0f} min")
    print(f"total {len(jobs)} pipelines across {args.pods} shards")
    return 0


if __name__ == "__main__":
    import sys as _s
    print("VOID: E-B / PREREG_TEXTPERM_V1 is tombstoned (audit 2026-07-24); "
          "this script hard-refuses. A corrected PREREG_TEXTPERM_V2 in a new "
          "namespace is required before any run.", file=_s.stderr)
    _s.exit(3)
