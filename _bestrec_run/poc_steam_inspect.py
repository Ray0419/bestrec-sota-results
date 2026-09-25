# -*- coding: utf-8 -*-
"""Inspect the Steam crawl files: format, fields, counts (CPU-only)."""
import ast
import gzip
import sys

D = r"C:\Users\rayxc\Documents\R\data_raw_proper\steam"

print("=== steam_games.json.gz: first 2 records + count ===")
n = 0
with gzip.open(D + r"\steam_games.json.gz", "rt", encoding="utf-8") as f:
    for line in f:
        n += 1
        if n <= 2:
            r = ast.literal_eval(line)   # McAuley crawls are python-literal lines
            print({k: (str(v)[:60] + "..." if len(str(v)) > 60 else v)
                   for k, v in list(r.items())[:10]})
print(f"games: {n:,}")

print("\n=== steam_reviews.json.gz: first 2 records + sample fields ===")
n = 0
with gzip.open(D + r"\steam_reviews.json.gz", "rt", encoding="utf-8") as f:
    for line in f:
        n += 1
        if n <= 2:
            r = ast.literal_eval(line)
            print({k: (str(v)[:50] + "..." if len(str(v)) > 50 else v)
                   for k, v in list(r.items())[:12]})
        if n >= 200000:
            print("(stopping count at 200k for speed; full count in adapter)")
            break
print(f"reviews seen: {n:,}")
