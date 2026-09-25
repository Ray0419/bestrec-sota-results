# -*- coding: utf-8 -*-
"""PREREG_STEAM_V1 adapter: McAuley/Kang Steam crawl -> repo 5-core LLOO CSVs.

Emits (NEW files only, never overwrites):
  <main>/data_5core/5core/last_out/Steam.{train,valid,test}.csv
      columns user_id,parent_asin,rating,timestamp  (rating=1.0 implicit;
      timestamp = epoch ms of the review date, day granularity, with a
      deterministic (page, page_order) tiebreak folded into the ms field)
  <main>/cache_5core/steam_item_text.json   product_id -> "title. genres. tags."
      (input for the MiniLM encode step; row order = sorted(product_id) strings,
       the same string sort run_sasrec_sbert.reindex() applies)

5-core: iterative user>=5 & item>=5 until stable. LLOO: per user by time,
last -> test, second-last -> valid, rest -> train (repo convention).
Sanity target (SASRec paper): ~334k users / ~13k items / ~3.5M actions.
"""
import ast
import gzip
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone

D = r"C:\Users\rayxc\Documents\R\data_raw_proper\steam"
OUT_SPLIT = r"C:\Users\rayxc\Documents\R\data_5core\5core\last_out"
OUT_CACHE = r"C:\Users\rayxc\Documents\R\cache_5core"


def parse_reviews():
    inter = []
    bad = 0
    with gzip.open(os.path.join(D, "steam_reviews.json.gz"), "rt",
                   encoding="utf-8") as f:
        for ln, line in enumerate(f, 1):
            try:
                r = ast.literal_eval(line)
                u = r.get("username")
                i = r.get("product_id")
                d = r.get("date")
                if not (u and i and d):
                    bad += 1
                    continue
                ts = int(datetime.strptime(d, "%Y-%m-%d")
                         .replace(tzinfo=timezone.utc).timestamp() * 1000)
                # deterministic within-day tiebreak, capped below one day
                tb = (int(r.get("page", 0)) * 100 + int(r.get("page_order", 0))) % 86_400_000
                inter.append((u, str(i), ts + tb))
            except Exception:
                bad += 1
            if ln % 1_000_000 == 0:
                print(f"  parsed {ln:,} lines ({len(inter):,} kept)", flush=True)
    print(f"parsed: {len(inter):,} interactions, {bad:,} bad lines", flush=True)
    return inter


def five_core(inter):
    rnd = 0
    while True:
        rnd += 1
        uc = Counter(u for u, _, _ in inter)
        ic = Counter(i for _, i, _ in inter)
        keep = [(u, i, t) for u, i, t in inter if uc[u] >= 5 and ic[i] >= 5]
        print(f"  5-core round {rnd}: {len(inter):,} -> {len(keep):,}", flush=True)
        if len(keep) == len(inter):
            return keep
        inter = keep


def main():
    for p in ("Steam.train.csv", "Steam.valid.csv", "Steam.test.csv"):
        if os.path.exists(os.path.join(OUT_SPLIT, p)):
            print(f"REFUSING to overwrite existing {p}; delete manually to redo")
            return
    inter = parse_reviews()
    # dedupe exact (user,item,ts) repeats
    inter = sorted(set(inter))
    print(f"after dedupe: {len(inter):,}", flush=True)
    inter = five_core(inter)
    users = {u for u, _, _ in inter}
    items = {i for _, i, _ in inter}
    print(f"5-core: {len(users):,} users, {len(items):,} items, "
          f"{len(inter):,} actions", flush=True)

    by_user = defaultdict(list)
    for u, i, t in inter:
        by_user[u].append((t, i))
    tr, va, te = [], [], []
    for u, lst in by_user.items():
        lst.sort()
        if len(lst) < 3:
            tr += [(u, i, t) for t, i in lst]
            continue
        tr += [(u, i, t) for t, i in lst[:-2]]
        va.append((u, lst[-2][1], lst[-2][0]))
        te.append((u, lst[-1][1], lst[-1][0]))
    os.makedirs(OUT_SPLIT, exist_ok=True)
    for name, rows in (("train", tr), ("valid", va), ("test", te)):
        p = os.path.join(OUT_SPLIT, f"Steam.{name}.csv")
        with open(p, "w", encoding="utf-8", newline="") as f:
            f.write("user_id,parent_asin,rating,timestamp\n")
            for u, i, t in rows:
                uq = '"' + u.replace('"', '""') + '"' if ("," in u or '"' in u) else u
                f.write(f"{uq},{i},1.0,{t}\n")
        print(f"wrote {p} ({len(rows):,} rows)", flush=True)

    # item text map for the encode step
    meta = {}
    with gzip.open(os.path.join(D, "steam_games.json.gz"), "rt",
                   encoding="utf-8") as f:
        for line in f:
            try:
                r = ast.literal_eval(line)
                gid = str(r.get("id") or r.get("url", "").rstrip("/").split("/app/")[-1].split("/")[0])
                if not gid:
                    continue
                title = r.get("title") or r.get("app_name") or ""
                genres = r.get("genres") or []
                tags = r.get("tags") or []
                if isinstance(genres, str):
                    genres = ast.literal_eval(genres)
                if isinstance(tags, str):
                    tags = ast.literal_eval(tags)
                meta[gid] = f"{title}. {', '.join(genres)}. {', '.join(tags[:10])}"
            except Exception:
                continue
    text = {i: meta.get(i, "") for i in sorted(items)}
    n_missing = sum(1 for v in text.values() if not v)
    with open(os.path.join(OUT_CACHE, "steam_item_text.json"), "w",
              encoding="utf-8") as f:
        json.dump(text, f)
    print(f"item text map: {len(text):,} items, {n_missing:,} without metadata "
          f"({100*n_missing/len(text):.1f}%)", flush=True)
    print("SANITY TARGET: ~334k users / ~13k items / ~3.5M actions (SASRec paper)")


if __name__ == "__main__":
    main()
