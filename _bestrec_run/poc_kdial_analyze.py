# -*- coding: utf-8 -*-
"""Analyze the mini k-dial POC (RQ2): interventional degree-response.

For each arm (text, id) and rung (k4, k0), compare per-user NDCG@10 on the
CAPPED items' eval targets against the same arm's anchor run (within-arm,
same seed => initialization-paired: identical weight init, identical data
order except for the capped interactions).

Reports:
  A(k) per arm  = mean NDCG@10 over capped-item targets at that rung
  text-ID gap   = A_text(k) - A_id(k) at each rung  (the causal curve)
  control       = same numbers on UNcapped items (should be ~unchanged)
"""
import gzip
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "poc_out")
SEED = 20260736
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


def main():
    capset_path = os.path.join(OUT, f"results_KDIAL_text_k0_MI_seed{SEED}.json.capset.json")
    cap = set(json.load(open(capset_path, encoding="utf-8"))["capped_items"])
    print(f"capped items: {len(cap):,}")

    data = {}
    for arm in ("text", "id"):
        for rung in RUNGS:
            p = os.path.join(OUT, f"results_KDIAL_{arm}_{rung}_MI_seed{SEED}.users.jsonl.gz")
            if not os.path.exists(p):
                print(f"MISSING {os.path.basename(p)}")
                return
            data[(arm, rung)] = load(p)

    u0, t0, _ = data[("text", "anchor")]
    is_cap = np.array([t in cap for t in t0])
    print(f"eval targets: {len(t0):,}  on capped items: {int(is_cap.sum()):,}  "
          f"uncapped: {int((~is_cap).sum()):,}")
    # verify identical eval order across runs
    for key, (u, t, _) in data.items():
        assert np.array_equal(u, u0) and np.array_equal(t, t0), f"eval drift in {key}"
    print("eval alignment: identical user/target order across all 6 runs")

    rep = {"n_capped_items": len(cap), "n_cap_targets": int(is_cap.sum()),
           "n_uncap_targets": int((~is_cap).sum()), "rungs": {}}
    print("\n=== A(k): NDCG@10 on CAPPED-item targets ===")
    print(f"{'rung':>7} {'text':>10} {'id':>10} {'text-id':>10} "
          f"{'d_vs_anchor(text)':>18} {'d_vs_anchor(id)':>16}")
    at_a = data[("text", "anchor")][2][is_cap].mean()
    ai_a = data[("id", "anchor")][2][is_cap].mean()
    for rung in RUNGS:
        at = data[("text", rung)][2][is_cap].mean()
        ai = data[("id", rung)][2][is_cap].mean()
        rep["rungs"][rung] = {
            "cap_text_ndcg10": float(at), "cap_id_ndcg10": float(ai),
            "cap_text_minus_id": float(at - ai),
            "cap_text_delta_vs_anchor": float(at - at_a),
            "cap_id_delta_vs_anchor": float(ai - ai_a),
            "uncap_text_ndcg10": float(data[("text", rung)][2][~is_cap].mean()),
            "uncap_id_ndcg10": float(data[("id", rung)][2][~is_cap].mean()),
            "overall_text_ndcg10": float(data[("text", rung)][2].mean()),
            "overall_id_ndcg10": float(data[("id", rung)][2].mean())}
        print(f"{rung:>7} {at:>10.5f} {ai:>10.5f} {at-ai:>+10.5f} "
              f"{at-at_a:>+18.5f} {ai-ai_a:>+16.5f}")

    print("\n=== control: NDCG@10 on UNCAPPED-item targets (should be ~flat) ===")
    for rung in RUNGS:
        r = rep["rungs"][rung]
        print(f"{rung:>7} text={r['uncap_text_ndcg10']:.5f} "
              f"id={r['uncap_id_ndcg10']:.5f} "
              f"gap={r['uncap_text_ndcg10']-r['uncap_id_ndcg10']:+.5f}")

    # paired per-user bootstrap CI on the text-id gap at each rung (capped only)
    rng = np.random.RandomState(0)
    idx = np.nonzero(is_cap)[0]
    print("\n=== bootstrap 95% CI on (text - id) at capped targets ===")
    for rung in RUNGS:
        dt = data[("text", rung)][2][idx] - data[("id", rung)][2][idx]
        boots = [dt[rng.randint(0, len(dt), len(dt))].mean() for _ in range(2000)]
        lo, hi = np.percentile(boots, [2.5, 97.5])
        rep["rungs"][rung]["gap_ci95"] = [float(lo), float(hi)]
        print(f"{rung:>7} gap={dt.mean():+.5f}  CI[{lo:+.5f}, {hi:+.5f}]  "
              f"{'EXCLUDES 0' if lo > 0 or hi < 0 else 'includes 0'}")

    dst = os.path.join(OUT, "kdial_analysis.json")
    json.dump(rep, open(dst, "w", encoding="utf-8"), indent=1)
    print(f"\nwrote {dst}")


if __name__ == "__main__":
    main()
