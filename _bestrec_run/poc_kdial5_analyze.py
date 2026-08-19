# -*- coding: utf-8 -*-
"""MERGED AGENDA step 1 readout: 5-seed k-dial, paired arms.

The load-bearing contrast is the DIFFERENCE OF GAPS across rungs, computed
per seed and aggregated across seeds:

    gap(seed, rung) = NDCG@10(text) - NDCG@10(id)   on CAPPED-item targets
    dd(seed)        = gap(seed, anchor) - gap(seed, rung)

Arms are initialization-paired within a seed, and the capped-item set is
identical across every run, so dd is a within-item, within-seed contrast: the
only thing that changed is the items' training degree.

Reports per-seed values, mean +/- SD, paired t, 95% CI, and the sign count --
the house reporting convention. Also reports the uncapped-item control.
"""
import glob
import gzip
import json
import os
from collections import defaultdict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "poc_out")
RUNGS = ("anchor", "k4", "k0")


def load(path):
    users, tgts, nds = [], [], []
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            users.append(r["user_id"])
            tgts.append(int(r["target_item_id"]))
            nds.append(float(r["ndcg10"]))
    return np.array(users), np.array(tgts), np.array(nds)


def tstats(x):
    x = np.asarray(x, dtype=np.float64)
    n = len(x)
    m = float(x.mean())
    sd = float(x.std(ddof=1)) if n > 1 else float("nan")
    se = sd / np.sqrt(n) if n > 1 else float("nan")
    t = m / se if se and se > 0 else float("nan")
    # t critical for small n, two-sided 95%
    tcrit = {2: 12.706, 3: 4.303, 4: 3.182, 5: 2.776, 6: 2.571}.get(n - 1, 1.96)
    lo, hi = m - tcrit * se, m + tcrit * se
    return {"mean": m, "sd": sd, "t": float(t), "ci95": [float(lo), float(hi)],
            "n_pos": int((x > 0).sum()), "n": n}


def main():
    seeds = sorted({int(os.path.basename(p).split("seed")[1].split(".")[0])
                    for p in glob.glob(os.path.join(OUT, "results_K5_text_anchor_MI_seed*.json"))
                    if "capset" not in p})
    print(f"seeds found: {seeds}")
    capset = json.load(open(os.path.join(
        OUT, f"results_K5_text_k0_MI_seed{seeds[0]}.json.capset.json"),
        encoding="utf-8"))
    cap = set(capset["capped_items"])
    print(f"capped items: {len(cap):,} (identical set across all runs)")

    per_seed = defaultdict(dict)
    ref_u = ref_t = None
    complete = []
    for s in seeds:
        ok = True
        for arm in ("text", "id"):
            for rung in RUNGS:
                p = os.path.join(OUT, f"results_K5_{arm}_{rung}_MI_seed{s}.users.jsonl.gz")
                if not os.path.exists(p):
                    ok = False
                    continue
                u, t, nd = load(p)
                if ref_u is None:
                    ref_u, ref_t = u, t
                    is_cap = np.array([x in cap for x in t])
                    globals()["_IS_CAP"] = is_cap
                else:
                    assert np.array_equal(u, ref_u) and np.array_equal(t, ref_t), \
                        f"eval drift in {arm}/{rung}/{s}"
                per_seed[s][(arm, rung)] = nd
        if ok:
            complete.append(s)
    is_cap = globals()["_IS_CAP"]
    print(f"complete seeds: {complete}  ({len(complete)}/{len(seeds)})")
    print(f"eval targets {len(ref_t):,}: on capped items {int(is_cap.sum()):,}, "
          f"uncapped {int((~is_cap).sum()):,}")
    if not complete:
        return

    rep = {"seeds": complete, "n_capped_items": len(cap),
           "n_cap_targets": int(is_cap.sum()), "rungs": {}, "dd_vs_anchor": {}}

    print("\n=== per-seed text-ID gap on CAPPED-item targets ===")
    print(f"{'seed':>10} " + "  ".join(f"{r:>10}" for r in RUNGS))
    gaps = {r: [] for r in RUNGS}
    for s in complete:
        row = []
        for r in RUNGS:
            g = float(per_seed[s][("text", r)][is_cap].mean()
                      - per_seed[s][("id", r)][is_cap].mean())
            gaps[r].append(g)
            row.append(g)
        print(f"{s:>10} " + "  ".join(f"{v:>+10.5f}" for v in row))

    print("\n=== aggregate across seeds (capped-item targets) ===")
    for r in RUNGS:
        st = tstats(gaps[r])
        rep["rungs"][r] = {"gap": st,
                           "text_mean": float(np.mean([per_seed[s][("text", r)][is_cap].mean()
                                                       for s in complete])),
                           "id_mean": float(np.mean([per_seed[s][("id", r)][is_cap].mean()
                                                     for s in complete]))}
        excl = "EXCLUDES 0" if (st["ci95"][0] > 0 or st["ci95"][1] < 0) else "includes 0"
        print(f"  {r:>7}: text={rep['rungs'][r]['text_mean']:.5f} "
              f"id={rep['rungs'][r]['id_mean']:.5f}  gap={st['mean']:+.5f} "
              f"+-{st['sd']:.5f}  t={st['t']:+.2f}  CI[{st['ci95'][0]:+.5f}, "
              f"{st['ci95'][1]:+.5f}] {excl}  {st['n_pos']}/{st['n']} pos")

    print("\n=== DIFFERENCE OF GAPS vs anchor (the causal contrast) ===")
    for r in RUNGS[1:]:
        dd = [gaps["anchor"][i] - gaps[r][i] for i in range(len(complete))]
        st = tstats(dd)
        rep["dd_vs_anchor"][r] = st
        excl = "EXCLUDES 0" if (st["ci95"][0] > 0 or st["ci95"][1] < 0) else "includes 0"
        print(f"  anchor - {r:>3}: dd={st['mean']:+.5f} +-{st['sd']:.5f} "
              f"t={st['t']:+.2f} CI[{st['ci95'][0]:+.5f}, {st['ci95'][1]:+.5f}] "
              f"{excl}  {st['n_pos']}/{st['n']} pos")

    print("\n=== control: UNCAPPED-item targets (should be ~flat) ===")
    rep["control_uncapped"] = {}
    for r in RUNGS:
        g = [float(per_seed[s][("text", r)][~is_cap].mean()
                   - per_seed[s][("id", r)][~is_cap].mean()) for s in complete]
        st = tstats(g)
        rep["control_uncapped"][r] = st
        print(f"  {r:>7}: gap={st['mean']:+.5f} +-{st['sd']:.5f} "
              f"({st['n_pos']}/{st['n']} pos)")

    dst = os.path.join(OUT, "kdial5_analysis.json")
    json.dump(rep, open(dst, "w", encoding="utf-8"), indent=1)
    print(f"\nwrote {dst}")


if __name__ == "__main__":
    main()
