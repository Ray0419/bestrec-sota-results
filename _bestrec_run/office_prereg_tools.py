#!/usr/bin/env python
"""Helpers for SOTA_CONFIRM_PREREG_OFFICE.md.

  stats      — after preprocessing: record split hashes, n_users/items/inters,
               mean distinct-users-per-item U, and apply the pre-registered P1
               rule MECHANICALLY (before any training run). Appends to
               SOTA_CONFIRM_OFFICE_RESULTS.md.
  adjudicate — after the 16 runs: evaluate P2 (dual gate vs 0.0271), the P1
               tail contrast, and the floor check. Appends verdicts.
"""
import glob
import gzip
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPLIT = ROOT / "data_5core" / "5core" / "last_out"
RES = ROOT / "SOTA_CONFIRM_OFFICE_RESULTS.md"
CAT = "Office_Products"
TARGET = 0.0271
SEEDS = [20260623, 20260624, 20260625, 20260626, 20260627]
T975 = 2.776


def _sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _append(text):
    with RES.open("a", encoding="utf-8") as f:
        f.write(text)


def stats():
    import csv
    from collections import defaultdict
    rows = {}
    users_per_item = defaultdict(set)
    n = {}
    for sp in ("train", "valid", "test"):
        p = SPLIT / f"{CAT}.{sp}.csv"
        cnt = 0
        for r in csv.reader(open(p, encoding="utf-8")):
            if not r or r[0] == "user_id":
                continue
            cnt += 1
            if sp == "train":
                users_per_item[r[1]].add(r[0])
        n[sp] = cnt
        rows[sp] = _sha(p)
    U = sum(len(v) for v in users_per_item.values()) / max(1, len(users_per_item))
    users = n["test"]
    items = len({i for i in users_per_item})
    if U < 2.5:
        pred = "PREDICT tail Delta > 0 (MI-like regime)"
    elif U >= 3.0:
        pred = "PREDICT tail Delta ~ 0 / null (VG/Beauty-like regime)"
    else:
        pred = "VOID (pre-declared ambiguous zone 2.5 <= U < 3.0)"
    cache = ROOT / "cache_5core" / f"sbert_titles_{CAT}.npy"
    _append(
        f"\n## STATS + P1 PREDICTION (recorded BEFORE any training run)\n\n"
        f"- splits sha256: train `{rows['train'][:16]}...` valid `{rows['valid'][:16]}...` "
        f"test `{rows['test'][:16]}...`\n"
        f"- full hashes: train {rows['train']} / valid {rows['valid']} / test {rows['test']}\n"
        f"- text cache sha256: {_sha(cache) if cache.exists() else 'MISSING'}\n"
        f"- n interactions: train {n['train']:,} / valid {n['valid']:,} / test {n['test']:,} "
        f"(total {sum(n.values()):,}); n_users(test rows) = {users:,}; n_items(train) = {items:,}\n"
        f"- **U = mean distinct users/item (TRAIN) = {U:.3f}**\n"
        f"- **P1 mechanical application: {pred}** (rule frozen in SOTA_CONFIRM_PREREG_OFFICE.md; "
        f"reference points MI 2.34 / VG 3.70 / Beauty 3.51)\n")
    print(f"U={U:.3f} -> {pred}")
    return 0


def _arm(vals):
    m = sum(vals) / len(vals)
    sd = math.sqrt(sum((x - m) ** 2 for x in vals) / (len(vals) - 1))
    lb = m - T975 * sd / math.sqrt(len(vals))
    return m, sd, lb


def _final_full(path):
    """Prereg-compliant headline: the FINAL-epoch FULL-catalog eval (the prereg
    declares headline numbers come from full-catalog all-user evaluations only;
    best-by-val checkpoints were evaluated on the 30k subsample)."""
    d = json.load(open(path))
    fin = [h for h in d["history"] if "test" in h][-1]
    t = fin["test"]
    assert t["n_eval"] == 223308, f"final eval not full-catalog: {t['n_eval']}"
    return t


def adjudicate():
    out = ["\n## FINAL ADJUDICATION — prereg-compliant headline (final-epoch FULL-catalog eval; "
           "supersedes the earlier best_test-based sections above)\n",
           "> NOTE: 'P2 DUAL GATE' below reports the gate ARITHMETIC only (CI-LBs vs 0.0271). "
           "The pre-registration as a whole is VOID — the floor check failed (+44% above the "
           "published SASRec; anomaly explained and VOID deliberately retained, see "
           "THEIRS_ON_OURS_REPORT.md S4.1 and the paper's Appendix A.0). Gate values are "
           "provisional/descriptive, never a confirmatory pass.\n"]
    ok = True
    # P2 dual gate
    for arm in (16, 8):
        vals = []
        for s in SEEDS:
            p = ROOT / "_bestrec_run" / f"results_OFFICE_k{arm}_seed{s}.json"
            try:
                vals.append(_final_full(p)["NDCG@10"])
            except FileNotFoundError:
                out.append(f"- ARM k{arm} seed {s}: MISSING\n")
                ok = False
        if len(vals) == 5:
            m, sd, lb = _arm(vals)
            npos = sum(1 for v in vals if v > TARGET)
            gate = lb > TARGET and npos >= 4
            ok = ok and gate
            out.append(f"- **ARM k{arm}**: {['%.5f' % v for v in vals]} mean {m:.5f} sd {sd:.5f} "
                       f"CI-LB {lb:.5f} ({npos}/5 > {TARGET}) -> {'PASS' if gate else 'FAIL'}\n")
    # P1 tail contrast (text = k8 arm; id-only arm)
    hits = {"text": {}, "id": {}}
    for s in SEEDS:
        for tag, fn in (("text", f"results_OFFICE_k8_seed{s}.json"),
                        ("id", f"results_OFFICE_idonly_seed{s}.json")):
            try:
                bp = _final_full(ROOT / "_bestrec_run" / fn)["by_popularity"]["tail"]
                for K in (10, 20, 50, 100):
                    hits[tag].setdefault(K, []).append(bp.get(f"n_hit@{K}", 0))
                hits[tag].setdefault("n", []).append(bp["n"])
            except FileNotFoundError:
                pass
    if hits["text"].get(10) and hits["id"].get(10):
        N = hits["text"]["n"][0] * len(hits["text"]["n"])
        out.append("- **P1 tail contrast (pooled hits text vs id; z RETRACTED 2026-07-19 as inference — clustered repeated users, descriptive counts only; see manuscript/office.tailwelch.* cells)**: ")
        from math import erf, sqrt
        for K in (10, 20, 50, 100):
            ht, hi = sum(hits["text"][K]), sum(hits["id"][K])
            pp = (ht + hi) / (2 * N)
            se = sqrt(max(pp * (1 - pp) * 2 / N, 1e-12))
            z = (ht / N - hi / N) / se if se > 0 else 0
            pv = 2 * (1 - 0.5 * (1 + erf(abs(z) / sqrt(2))))
            out.append(f"@{K}: {ht} vs {hi} (retracted-z record: {z:.2f})  ")
        out.append("\n")
    # floor
    try:
        fl = json.load(open(ROOT / "_bestrec_run" / f"results_OFFICE_sasrecfloor_seed{SEEDS[0]}.json"))
        out.append(f"- floor SASRec NDCG@10 = {fl['best_test']['NDCG@10']:.5f} "
                   f"(published SASRec 0.0153; must not be far ABOVE it)\n")
    except FileNotFoundError:
        out.append("- floor run MISSING\n")
    out.append(f"\n**P2 DUAL GATE: {'PASS' if ok else 'FAIL'}**\n")
    text = "".join(out)
    # idempotent: rebuild runs adjudicate repeatedly; only record a block once
    if text in RES.read_text(encoding="utf-8"):
        print("(identical adjudication already recorded in results file; append skipped)")
    else:
        _append(text)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit({"stats": stats, "adjudicate": adjudicate}[sys.argv[1]]())
