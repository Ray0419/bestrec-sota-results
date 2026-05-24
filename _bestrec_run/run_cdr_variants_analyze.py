"""Analyzes _bestrec_run/results_cdr_variants.json and per-pair JSONL files
to print a final summary table:

  - per-(dataset, variant) NDCG@10 mean+/-std, HR@10, MRR, avg fit time
  - per-(dataset, variant) per-USER paired Wilcoxon vs CDR_validated
    (two-sided + one-sided 'greater'), Holm-corrected across non-CDR variants
  - per-(dataset, variant) selected-alpha distribution

This is the report-time aggregator. Run after the main driver finishes.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import wilcoxon


def _read_jsonl(path):
    if not path.exists(): return []
    out = []
    with open(path) as fh:
        for line in fh:
            try: out.append(json.loads(line))
            except Exception: pass
    return out


def _per_user_from_jsonl(records, method=None):
    by_u = defaultdict(list)
    for r in records:
        if method is not None and r.get("method") != method: continue
        by_u[r["user_id"]].append(r["ndcg10"])
    return {u: float(np.mean(vs)) for u, vs in by_u.items()}


def analyze(json_path, out_md_path=None):
    data = json.load(open(json_path))
    json_dir = Path(json_path).parent

    lines = []
    def p(*a):
        s = " ".join(str(x) for x in a)
        lines.append(s); print(s)

    variants = data.get("variants", ["CDR_validated", "CDR_Q", "CDR_R2", "CDR_K", "CDR_S"])

    p("\n# CDR variants: aggregated results\n")
    p(f"seeds: {data['seeds']}")
    p(f"variants: {variants}\n")

    for ds, dsdata in data["datasets"].items():
        p(f"\n## {ds.upper()}\n")
        pf = dsdata.get("perfold", {})

        # NDCG / HR / MRR / fit_time table
        p("### Per-fold means")
        p(f"|{'variant':<18}|{'NDCG@10 (mean±std)':>22}|{'HR@10':>9}|{'MRR':>9}|{'fit time (s)':>14}|")
        p(f"|{'-'*18}|{'-'*22}|{'-'*9}|{'-'*9}|{'-'*14}|")
        for v in variants:
            if v not in pf: continue
            nd = pf[v]["NDCG@10"]; hr = pf[v]["HR@10"]; mrr = pf[v]["MRR"]
            ft = pf[v].get("fit_time", [0.0])
            p(f"|{v:<18}|{np.mean(nd):.4f} ± {np.std(nd):.4f}     |{np.mean(hr):8.4f} |{np.mean(mrr):8.4f} |{np.mean(ft):13.1f} |")

        # Selected alpha distribution
        p("\n### Inner-validation-selected alpha (distribution across (seed, fold) pairs)")
        sa = dsdata.get("selected_alphas", {})
        for v in variants:
            if v not in sa: continue
            alphas = [s["alpha"] for s in sa[v]]
            c = Counter(alphas)
            kv_str = ", ".join(f"{k:.2f}:{c[k]}" for k in sorted(c))
            p(f"  - {v}: {{{kv_str}}}")

        # Wilcoxon
        wx = dsdata.get("wilcoxon_vs_cdr_validated", {})
        p("\n### Per-USER paired Wilcoxon vs CDR_validated")
        p(f"|{'variant':<18}|{'n_users':>8}|{'variant mean':>14}|{'CDR mean':>10}|{'delta':>10}|{'p_two_sided':>13}|{'p_Holm':>11}|{'marker':>7}|")
        p(f"|{'-'*18}|{'-'*8}|{'-'*14}|{'-'*10}|{'-'*10}|{'-'*13}|{'-'*11}|{'-'*7}|")
        for v in variants:
            if v == "CDR_validated" or v not in wx: continue
            w = wx[v]
            p(f"|{v:<18}|{w['n_users']:8d}|{w['variant_mean']:14.4f}|{w['cdr_mean']:10.4f}|{w['delta']:+10.4f}|{w['p_two_sided']:13.3e}|{w.get('p_two_sided_holm', w['p_two_sided']):11.3e}|{w['marker']:>7}|")

    if out_md_path:
        with open(out_md_path, "w") as fh: fh.write("\n".join(lines) + "\n")
        print(f"\nwrote {out_md_path}")


if __name__ == "__main__":
    p = Path(__file__).parent / "results_cdr_variants.json"
    if len(sys.argv) > 1: p = Path(sys.argv[1])
    out_md = None
    if len(sys.argv) > 2: out_md = Path(sys.argv[2])
    analyze(p, out_md)
