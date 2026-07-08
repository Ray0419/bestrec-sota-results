"""Print a leaderboard of all SASRec/TIGER/BERT4Rec results on Beauty_and_PC.

Scans `_bestrec_run/results_*_Beauty*.json` for any file containing a
test NDCG@10 value, extracts the headline numbers, and prints a table
sorted descending by test NDCG@10.

Usage:
    uv run python compare_beauty_results.py
"""
from __future__ import annotations

import json
from pathlib import Path


def extract_ndcg(d):
    """Return (test_ndcg10, hr10, mrr, n_eval) or None."""
    # Try multiple schemas
    if "test" in d and isinstance(d["test"], dict):
        t = d["test"]
        return (t.get("NDCG@10"), t.get("HR@10"), t.get("MRR"), t.get("n_eval"))
    if "best_test" in d and isinstance(d["best_test"], dict):
        t = d["best_test"]
        return (t.get("NDCG@10"), t.get("HR@10"), t.get("MRR"), t.get("n_eval"))
    if "results" in d:
        return extract_ndcg(d["results"])
    # Look for direct keys
    return (d.get("NDCG@10"), d.get("HR@10"), d.get("MRR"), d.get("n_eval"))


def main():
    base = Path(__file__).parent
    rows = []
    for p in sorted(base.glob("results_*_Beauty*.json")):
        try:
            d = json.load(open(p))
        except Exception as e:
            print(f"  SKIP {p.name}: {e}")
            continue
        ndcg, hr, mrr, n_eval = extract_ndcg(d)
        if ndcg is None or ndcg <= 0:
            continue
        cfg = d.get("config", {})
        rows.append({
            "file": p.name,
            "ndcg": ndcg,
            "hr": hr if hr else 0.0,
            "mrr": mrr if mrr else 0.0,
            "n_eval": n_eval if n_eval else 0,
            "d": cfg.get("d_model", "?"),
            "drop": cfg.get("dropout", "?"),
            "epochs": cfg.get("epochs", "?"),
            "ench": str(cfg.get("encoder_cache", "")).split("/")[-1].replace("_Beauty_and_Personal_Care.npy", "") or "sbert",
            "mlp": cfg.get("mlp_adaptor", False),
            "sbo": cfg.get("sbert_only", False),
            "aug": cfg.get("augment_factor", 1),
            "loss": "chk-CE" if cfg.get("chunked_full_softmax") else ("in-batch" if cfg.get("in_batch_negs") else f"sampled-{cfg.get('sampled_negs', '?')}"),
        })

    rows.sort(key=lambda r: -r["ndcg"])
    print(f"{'NDCG@10':>8} {'HR@10':>8} d={ {}}drop=mlp sbo aug loss          ench-{'name':<40}")
    print(f"{'NDCG@10':>8} {'HR@10':>8} {'d':>3} {'drop':>5} {'mlp':>4} {'sbo':>4} {'aug':>3} {'loss':<10} {'enc':<24} file")
    print("-" * 130)
    for r in rows:
        print(f"{r['ndcg']:>8.4f} {r['hr']:>8.4f} {str(r['d']):>3} {str(r['drop']):>5} {str(r['mlp'])[:1]:>4} {str(r['sbo'])[:1]:>4} {str(r['aug']):>3} {str(r['loss'])[:10]:<10} {str(r['ench'])[:24]:<24} {r['file']}")
    print()
    print(f"Published reference: LIGER ~0.045+, TIGER ~0.031 (NDCG@10 on Amazon Reviews 2023 Beauty_and_PC 5-core)")
    if rows:
        gap = 0.045 - rows[0]["ndcg"]
        gap_pct = 100 * gap / 0.045
        print(f"Best so far: {rows[0]['file']} @ {rows[0]['ndcg']:.4f}  (gap to LIGER: {gap:+.4f} = {gap_pct:.0f}% short)")


if __name__ == "__main__":
    main()
