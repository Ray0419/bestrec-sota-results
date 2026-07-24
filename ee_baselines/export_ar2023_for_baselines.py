# -*- coding: utf-8 -*-
"""E-E setup: export our EXACT AR2023 5-core LLOO split into a clean, documented
interchange format that external baselines (AlphaFuse, LLM2Emb, ...) can be
adapted to consume. This is the reusable, apples-to-apples core: same users,
same items, same leave-last-out targets, same full-catalog universe as our
runs -- so any baseline number is comparable to ours.

It reads ONLY committed/available inputs; it writes NOTHING back into the
governed tree (outputs go to ee_baselines/export/<category>/), and it computes
no test metric (it is data prep, not evaluation).

Per category it emits:
  <cat>.sequences.jsonl : one line per user
      {"user": <int>, "train": [item_int...], "valid": [item_int...],
       "test": [item_int...], "train_ts":[...], "valid_ts":[...], "test_ts":[...]}
  <cat>.items.jsonl     : one line per item
      {"item": <int>, "parent_asin": <str>, "title": <str|null>}
  <cat>.manifest.json   : n_users, n_items, split hashes, title coverage,
                          and the contiguous id map provenance.

Usage:
  python ee_baselines/export_ar2023_for_baselines.py --categories Office_Products Video_Games
  python ee_baselines/export_ar2023_for_baselines.py --verify   # counts vs known
"""
import argparse
import csv
import hashlib
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPLIT_DIR = os.path.join(ROOT, "data_5core", "5core", "last_out")
OUT_DIR = os.path.join(ROOT, "ee_baselines", "export")
# raw meta (item titles) per category, where available
META = {
    "Office_Products": ("office", "meta_Office_Products.jsonl"),
    "Video_Games": ("video_games", "meta_Video_Games.jsonl"),
    "CDs_and_Vinyl": ("cds_vinyl", "meta_CDs_and_Vinyl.jsonl"),
    "Industrial_and_Scientific": ("industrial_sci",
                                  "meta_Industrial_and_Scientific.jsonl"),
    "Beauty_and_Personal_Care": ("beauty_and_pc",
                                 "meta_Beauty_and_Personal_Care.jsonl"),
}
# known (n_users, n_items) from our results JSONs, for the --verify gate
KNOWN = {
    "Office_Products": (223308, 77551),
    "Video_Games": (94762, 25612),
    "CDs_and_Vinyl": (123876, 89370),
    "Industrial_and_Scientific": (50985, 25848),
    "Musical_Instruments": (57439, 24587),
}


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]


def load_split(path):
    rows = []
    with io.open(path, encoding="utf-8") as f:
        r = csv.DictReader(f)
        for d in r:
            rows.append((d["user_id"], d["parent_asin"], int(d["timestamp"])))
    return rows


def load_titles(cat):
    if cat not in META:
        return {}
    sub, fn = META[cat]
    p = os.path.join(ROOT, "data_raw_proper", sub, fn)
    if not os.path.exists(p):
        return {}
    titles = {}
    with io.open(p, encoding="utf-8") as f:
        for line in f:
            try:
                j = json.loads(line)
            except Exception:
                continue
            a = j.get("parent_asin")
            if a and a not in titles:
                titles[a] = (j.get("title") or "").strip()
    return titles


def export_category(cat):
    tr = load_split(os.path.join(SPLIT_DIR, f"{cat}.train.csv"))
    va = load_split(os.path.join(SPLIT_DIR, f"{cat}.valid.csv"))
    te = load_split(os.path.join(SPLIT_DIR, f"{cat}.test.csv"))
    # contiguous, deterministic id maps: users by first train appearance,
    # items by first appearance across train+valid+test (train order first)
    uids, iids = {}, {}
    for u, i, _ in tr + va + te:
        if u not in uids:
            uids[u] = len(uids)
    for u, i, _ in tr + va + te:
        if i not in iids:
            iids[i] = len(iids)
    n_users, n_items = len(uids), len(iids)

    per_user = {u: {"train": [], "valid": [], "test": [],
                    "train_ts": [], "valid_ts": [], "test_ts": []}
                for u in range(n_users)}
    for split_name, rows in (("train", tr), ("valid", va), ("test", te)):
        for u, i, t in rows:
            d = per_user[uids[u]]
            d[split_name].append(iids[i])
            d[split_name + "_ts"].append(t)

    cdir = os.path.join(OUT_DIR, cat)
    os.makedirs(cdir, exist_ok=True)
    with io.open(os.path.join(cdir, f"{cat}.sequences.jsonl"), "w",
                 encoding="utf-8") as f:
        for u in range(n_users):
            f.write(json.dumps({"user": u, **per_user[u]}) + "\n")

    titles = load_titles(cat)
    inv = {v: k for k, v in iids.items()}
    cov = 0
    with io.open(os.path.join(cdir, f"{cat}.items.jsonl"), "w",
                 encoding="utf-8") as f:
        for it in range(n_items):
            asin = inv[it]
            title = titles.get(asin)
            if title:
                cov += 1
            f.write(json.dumps({"item": it, "parent_asin": asin,
                                "title": title}) + "\n")

    man = {"category": cat, "n_users": n_users, "n_items": n_items,
           "n_interactions_train": len(tr), "n_test_targets": len(te),
           "title_coverage": f"{cov}/{n_items} "
                             f"({100.0*cov/max(n_items,1):.1f}%)",
           "split_sha16": {s: sha(os.path.join(SPLIT_DIR, f"{cat}.{s}.csv"))
                           for s in ("train", "valid", "test")},
           "id_map": "users by first train appearance; items by first "
                     "appearance across train+valid+test (contiguous 0-based)",
           "note": "LLOO: test = each user's held-out last interaction; "
                   "full-catalog ranking universe = all n_items."}
    json.dump(man, io.open(os.path.join(cdir, f"{cat}.manifest.json"), "w",
                           encoding="utf-8"), indent=1)
    ok = ""
    if cat in KNOWN:
        ku, ki = KNOWN[cat]
        ok = "  MATCH" if (ku, ki) == (n_users, n_items) else \
             f"  MISMATCH (known {ku}/{ki})"
    print(f"{cat}: users={n_users:,} items={n_items:,} "
          f"test={len(te):,} titles={man['title_coverage']}{ok}")
    return (cat in KNOWN) and (KNOWN[cat] == (n_users, n_items))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--categories", nargs="+",
                    default=["Office_Products", "Video_Games"])
    ap.add_argument("--verify", action="store_true",
                    help="assert exported counts match the known n_users/n_items")
    args = ap.parse_args()
    allok = True
    for cat in args.categories:
        if not os.path.exists(os.path.join(SPLIT_DIR, f"{cat}.train.csv")):
            print(f"{cat}: SKIP (no split csv)")
            allok = False
            continue
        allok = export_category(cat) and allok
    if args.verify and not allok:
        print("VERIFY: FAIL (a count mismatched or a category was skipped)")
        return 2
    print("done ->", OUT_DIR)
    return 0


if __name__ == "__main__":
    sys.exit(main())
