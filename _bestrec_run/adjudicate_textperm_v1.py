# -*- coding: utf-8 -*-
"""Mechanical adjudicator for PREREG_TEXTPERM_V1 (E-B), frozen BEFORE
launch. First reader of the sequestered test values. Exit 0 = adjudication
completed; 2 = integrity failure; 3 = not ready."""
import glob
import hashlib
import json
import math
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SEEDS = (20260749, 20260750, 20260751)
ARMS = ("aligned", "permA", "permB", "permC", "random")
CATS = {"MI": ("Musical_Instruments",
               "results_MI_V2_ls02_filter16_seed20260608.json"),
        "VG": ("Video_Games",
               "results_V2_ls02_filter8_seed20260610_VG.json")}
SAME_ERA_REF = "results_FIRB_Industrial_and_Scientific_filter_seed20260713.json"
EXEMPT = {"seed", "out", "save_ckpt", "no_test_eval", "encoder_cache",
          "fir_v3", "fir_v3_kernel", "fir_v3_wd"}
MARGIN = 0.0005
ALPHA = 0.05


def welch(x, y):
    nx, ny = len(x), len(y)
    mx, my = sum(x) / nx, sum(y) / ny
    vx = sum((v - mx) ** 2 for v in x) / (nx - 1)
    vy = sum((v - my) ** 2 for v in y) / (ny - 1)
    se = math.sqrt(vx / nx + vy / ny)
    if se == 0:
        print("INTEGRITY FAIL: zero variance in Welch contrast")
        sys.exit(2)
    t = (mx - my) / se
    df = (vx / nx + vy / ny) ** 2 / ((vx / nx) ** 2 / (nx - 1)
                                     + (vy / ny) ** 2 / (ny - 1))
    try:
        from scipy import stats
        p = float(2.0 * stats.t.sf(abs(t), df))
        tc = float(stats.t.ppf(0.975, df))
    except Exception:
        print("FATAL: SciPy required.")
        sys.exit(2)
    est = mx - my
    return est, float(t), float(df), p, (est - tc * se, est + tc * se)


def main():
    # regenerate control caches locally and hash them (determinism gate)
    r = subprocess.run([sys.executable,
                        os.path.join(ROOT, "cloud", "make_control_caches.py")],
                       capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        print("INTEGRITY FAIL: control-cache regeneration failed")
        print(r.stdout[-1500:], r.stderr[-1500:])
        return 2
    cache_sha = {}
    for line in r.stdout.splitlines():
        if line.startswith("CACHE "):
            _, name, sha = line.split()
            cache_sha[name] = sha.split("=")[1]
    for tag, (cat, _) in CATS.items():
        p = os.path.join(ROOT, "cache_5core", f"sbert_titles_{cat}.npy")
        cache_sha[f"{cat}__aligned"] = hashlib.sha256(
            open(p, "rb").read()).hexdigest()

    era = json.load(open(os.path.join(HERE, SAME_ERA_REF),
                         encoding="utf-8"))["config"]
    decl = {f"results_{t}_TEXTPERM_{a}_seed{s}.json"
            for t in CATS for a in ARMS for s in SEEDS}
    got = {os.path.basename(p) for p in glob.glob(
        os.path.join(HERE, "results_*_TEXTPERM_*_seed*.json"))
        if not p.endswith(".finaleval.json")}
    und = sorted(got - decl)
    if und:
        print(f"INTEGRITY FAIL: undeclared files {und}")
        return 2
    if not glob.glob(os.path.join(HERE, "attempts", "cloud_shard*.jsonl")):
        print("INTEGRITY FAIL: no cloud shard ledgers present")
        return 2

    missing, era_seen = [], {}
    vals = {t: {a: [] for a in ARMS} for t in CATS}
    extra_rows = {t: {a: [] for a in ARMS} for t in CATS}
    for tag, (cat, ref_name) in CATS.items():
        ref_cfg = json.load(open(os.path.join(HERE, ref_name),
                                 encoding="utf-8"))["config"]
        for arm in ARMS:
            for seed in SEEDS:
                b = os.path.join(
                    HERE, f"results_{tag}_TEXTPERM_{arm}_seed{seed}.json")
                fe = b[:-5] + ".finaleval.json"
                if not (os.path.exists(b) and os.path.exists(fe)):
                    missing += [os.path.basename(x)
                                for x in (b, fe) if not os.path.exists(x)]
                    continue
                base = json.load(open(b, encoding="utf-8"))
                cfg = base["config"]
                if base.get("best_test") is not None:
                    print(f"INTEGRITY FAIL: test not sequestered in "
                          f"{os.path.basename(b)}")
                    return 2
                if not base.get("best_ckpt_sha256"):
                    print(f"INTEGRITY FAIL: no ckpt sha in "
                          f"{os.path.basename(b)}")
                    return 2
                bad = [k for k in set(ref_cfg) - EXEMPT
                       if cfg.get(k, "__M__") != ref_cfg[k]]
                for k in sorted(set(cfg) - set(ref_cfg) - EXEMPT):
                    if k not in era or cfg[k] != era[k] or \
                            era_seen.setdefault(k, cfg[k]) != cfg[k]:
                        bad.append(f"extra:{k}")
                if bad or cfg.get("seed") != seed \
                        or cfg.get("category") != cat:
                    print(f"INTEGRITY FAIL: config gate {bad[:5]} in "
                          f"{os.path.basename(b)}")
                    return 2
                f = json.load(open(fe, encoding="utf-8"))
                want = cache_sha[f"{cat}__{'aligned' if arm == 'aligned' else arm}"]
                if f["cache_sha256"] != want:
                    print(f"INTEGRITY FAIL: cache provenance in "
                          f"{os.path.basename(fe)} (arm {arm})")
                    return 2
                npz = np.load(fe[:-5] + ".perusers.npz")
                users = npz["users"]
                tb = npz["target_bin4"]
                n = f["test"]["n"]
                if (len(users) != n or len(np.unique(users)) != n
                        or not bool((np.diff(users) > 0).all())):
                    print(f"INTEGRITY FAIL: NPZ users in "
                          f"{os.path.basename(fe)}")
                    return 2
                arr = npz["ref_ndcg"]
                if (abs(float(arr.mean()) - f["test"]["overall"]) > 1e-6
                        or abs(float(arr[tb == 1].mean()) - f["test"]["f15"])
                        > 1e-6):
                    print(f"INTEGRITY FAIL: NPZ reconstruction in "
                          f"{os.path.basename(fe)}")
                    return 2
                vals[tag][arm].append(f["test"]["f15"])
                extra_rows[tag][arm].append(
                    {k: f["test"][k] for k in
                     ("overall", "f0", "mid", "head")})
    if missing:
        print(f"NOT READY: {len(missing)} files missing")
        for m in sorted(set(missing))[:10]:
            print("  -", m)
        return 3

    print("PREREG_TEXTPERM_V1 adjudication (mechanical; first reader)")
    rows = {}
    for tag in CATS:
        al = vals[tag]["aligned"]
        pm = vals[tag]["permA"] + vals[tag]["permB"] + vals[tag]["permC"]
        rd = vals[tag]["random"]
        est, t, df, p, ci = welch(al, pm)
        est_r, _, _, p_r, ci_r = welch(al, rd)
        rows[tag] = {"aligned_mean": sum(al) / len(al),
                     "permuted_mean": sum(pm) / len(pm),
                     "random_mean": sum(rd) / len(rd),
                     "vs_permuted": {"est": est, "t": t, "df": df, "p": p,
                                     "ci": ci},
                     "vs_random": {"est": est_r, "p": p_r, "ci": ci_r},
                     "per_arm_f15": {a: vals[tag][a] for a in ARMS},
                     "descriptive": {a: extra_rows[tag][a] for a in ARMS}}
        print(f"  {tag}: aligned f15 {rows[tag]['aligned_mean']:.5f} vs "
              f"permuted {rows[tag]['permuted_mean']:.5f} -> est "
              f"{est:+.5f} [{ci[0]:+.5f},{ci[1]:+.5f}] p={p:.4f} | vs "
              f"random est {est_r:+.5f} p={p_r:.4f}")
    order = sorted(CATS, key=lambda c: rows[c]["vs_permuted"]["p"])
    alive = True
    for rank, c in enumerate(order):
        thr = ALPHA / (2 - rank)
        sig = bool(alive and rows[c]["vs_permuted"]["p"] <= thr)
        if not sig:
            alive = False
        rows[c]["holm_significant"] = sig
    verdicts = {}
    for c in CATS:
        r = rows[c]
        lo, hi = r["vs_permuted"]["ci"]
        if r["holm_significant"] and r["vs_permuted"]["est"] > 0:
            verdicts[c] = "W-TP-SEM"
        elif -MARGIN < lo and hi < MARGIN:
            verdicts[c] = "W-TP-PERMEQ"
        else:
            verdicts[c] = "W-TP-INC"
        print(f"VERDICT {c}: {verdicts[c]}")
    outp = os.path.join(HERE, "textperm_v1_adjudication.json")
    json.dump({"verdicts": verdicts, "alpha": ALPHA, "margin": MARGIN,
               "rows": rows}, open(outp, "w", encoding="utf-8"), indent=2)
    print(f"wrote {outp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
