# -*- coding: utf-8 -*-
"""PREREG_DOSE_RESPONSE_V1 readout. Statistics fixed before the runs.

H1 (primary): Spearman rho(k, gap) > 0 with 5/5 seeds positive.
H2: gap(k=0) CI includes 0 AND gap(k=16) CI excludes 0.
H3: dd = gap(16) - gap(0) > 0, 5/5 seeds, CI excludes 0.

gap(s,k) = mean NDCG@10 text - mean NDCG@10 id over eval targets in group G_k.
Arms are initialization-paired within a seed; groups are identical items in
every run; all doses live in the SAME run at constant global density.

Memory: per-user records are reduced to per-group scalars in-loop, so peak
memory is O(n_eval), never O(n_eval x n_items).
"""
import glob
import gzip
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "poc_out")
DOSES = [0, 1, 2, 4, 8, 16]
TCRIT = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571}


def load(path):
    t, nd = [], []
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            t.append(int(r["target_item_id"]))
            nd.append(float(r["ndcg10"]))
    return np.array(t), np.array(nd)


def tstat(x):
    x = np.asarray(x, dtype=np.float64)
    n = len(x)
    m = float(x.mean())
    sd = float(x.std(ddof=1)) if n > 1 else float("nan")
    se = sd / np.sqrt(n) if n > 1 else float("nan")
    tc = TCRIT.get(n - 1, 1.96)
    return {"mean": m, "sd": sd, "t": float(m / se) if se else float("nan"),
            "ci95": [m - tc * se, m + tc * se], "n_pos": int((x > 0).sum()), "n": n}


def spearman(a, b):
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    ra -= ra.mean(); rb -= rb.mean()
    return float((ra * rb).sum() / np.sqrt((ra ** 2).sum() * (rb ** 2).sum()))


def main():
    seeds = sorted({int(os.path.basename(p).split("seed")[1].split(".")[0])
                    for p in glob.glob(os.path.join(OUT, "results_DOSE_text_MI_seed*.json"))
                    if "capset" not in p})
    cs = json.load(open(os.path.join(
        OUT, f"results_DOSE_text_MI_seed{seeds[0]}.json.capset.json"), encoding="utf-8"))
    groups = {g: np.array(v) for g, v in cs["groups"].items()}
    print(f"seeds: {seeds}  per-group items: {cs['per_group_n']}  "
          f"eligible: {cs['n_eligible']:,}")

    per_seed = {}
    for s in seeds:
        f = {}
        for arm in ("text", "id"):
            p = os.path.join(OUT, f"results_DOSE_{arm}_MI_seed{s}.users.jsonl.gz")
            if not os.path.exists(p):
                f = None
                break
            f[arm] = load(p)
        if f:
            per_seed[s] = f
    complete = sorted(per_seed)
    print(f"complete seeds: {complete} ({len(complete)}/{len(seeds)})")
    if len(complete) < 2:
        return

    tgt = per_seed[complete[0]]["text"][0]
    masks = {g: np.isin(tgt, items) for g, items in groups.items()}
    for g in list(groups) :
        print(f"  group {g:>8}: {int(masks[g].sum()):>6,} eval targets")

    gaps = {k: [] for k in DOSES}
    ctrl = []
    for s in complete:
        tt, tn = per_seed[s]["text"]
        it, inn = per_seed[s]["id"]
        assert np.array_equal(tt, it), f"eval drift seed {s}"
        for k in DOSES:
            m = masks[str(k)]
            gaps[k].append(float(tn[m].mean() - inn[m].mean()))
        m = masks["control"]
        ctrl.append(float(tn[m].mean() - inn[m].mean()))

    rep = {"seeds": complete, "per_group_items": cs["per_group_n"],
           "n_targets": {g: int(masks[g].sum()) for g in groups},
           "doses": {}, "control": tstat(ctrl)}

    print(f"\n=== dose-response: text-ID gap by training degree ===")
    print(f"{'seed':>10} " + "  ".join(f"k={k:<7}" for k in DOSES) + "   control")
    for i, s in enumerate(complete):
        print(f"{s:>10} " + "  ".join(f"{gaps[k][i]:>+9.5f}" for k in DOSES)
              + f"  {ctrl[i]:>+9.5f}")
    print(f"\n{'dose':>8} {'gap':>11} {'sd':>10} {'t':>7} {'95% CI':>26} {'signs':>7}")
    for k in DOSES:
        st = tstat(gaps[k])
        rep["doses"][str(k)] = st
        ex = "excl 0" if (st["ci95"][0] > 0 or st["ci95"][1] < 0) else "incl 0"
        print(f"{k:>8} {st['mean']:>+11.5f} {st['sd']:>10.5f} {st['t']:>+7.2f} "
              f"[{st['ci95'][0]:>+9.5f},{st['ci95'][1]:>+9.5f}] {ex}  "
              f"{st['n_pos']}/{st['n']}")
    cst = rep["control"]
    print(f"{'control':>8} {cst['mean']:>+11.5f} {cst['sd']:>10.5f} "
          f"{cst['t']:>+7.2f} [{cst['ci95'][0]:>+9.5f},{cst['ci95'][1]:>+9.5f}]  "
          f"{cst['n_pos']}/{cst['n']}")

    # ---- pre-registered tests ---------------------------------------------
    rhos = [spearman(np.array(DOSES, dtype=float),
                     np.array([gaps[k][i] for k in DOSES])) for i in range(len(complete))]
    rst = tstat(rhos)
    dd = [gaps[16][i] - gaps[0][i] for i in range(len(complete))]
    dst = tstat(dd)
    h1 = rst["mean"] > 0 and rst["n_pos"] == rst["n"]
    g0, g16 = rep["doses"]["0"], rep["doses"]["16"]
    h2 = (g0["ci95"][0] <= 0 <= g0["ci95"][1]) and (g16["ci95"][0] > 0)
    h3 = dst["n_pos"] == dst["n"] and dst["ci95"][0] > 0
    rep["H1_spearman"] = {"per_seed": rhos, **rst, "PASS": bool(h1)}
    rep["H3_dd_16_minus_0"] = {**dst, "PASS": bool(h3)}
    rep["H2_PASS"] = bool(h2)
    print("\n=== PRE-REGISTERED TESTS ===")
    print(f"  H1 monotone dose-response: rho per seed "
          f"{['%+.3f' % r for r in rhos]}  mean {rst['mean']:+.3f}  "
          f"{rst['n_pos']}/{rst['n']} pos  ->  {'PASS' if h1 else 'FAIL'}")
    print(f"  H2 abolition at k=0 and effect at k=16: "
          f"k0 CI {'incl' if g0['ci95'][0] <= 0 <= g0['ci95'][1] else 'EXCL'} 0, "
          f"k16 CI {'excl' if g16['ci95'][0] > 0 else 'incl'} 0  ->  "
          f"{'PASS' if h2 else 'FAIL'}")
    print(f"  H3 dd = gap(16)-gap(0) = {dst['mean']:+.5f} +-{dst['sd']:.5f} "
          f"t={dst['t']:+.2f} CI[{dst['ci95'][0]:+.5f},{dst['ci95'][1]:+.5f}] "
          f"{dst['n_pos']}/{dst['n']}  ->  {'PASS' if h3 else 'FAIL'}")

    dst_path = os.path.join(OUT, "dose_analysis.json")
    json.dump(rep, open(dst_path, "w", encoding="utf-8"), indent=1)
    print(f"\nwrote {dst_path}")


if __name__ == "__main__":
    main()
