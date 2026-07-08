#!/usr/bin/env python
"""Evaluate the SOTA_CONFIRM_PREREG_V2 dual gate from the V2 result JSONs.
Prints the per-seed table, per-arm stats, gate verdicts, and manifest checks
(git commit consistency + dirty flag + data hashes vs the prereg)."""
import glob
import hashlib
import json
import math
import sys

TARGET = 0.0406
SEEDS = [20260618, 20260619, 20260620, 20260621, 20260622]
T975_DF4 = 2.776
PREREG_HASHES = {
    "train_csv": "1f56c4abf0515e59090d728174db6b35ffa97f06929a0f955f2be924560f9dba",
    "valid_csv": "f1240768bd813fe84620fdff9d91c1055f560f51be42cf8ae9de45d7ee8d76bc",
    "test_csv": "19f3ed965a5adafec9f55575cdbe113556ae5ee156e41591da364cfb89cda36a",
    "text_cache": "406979249f4f89cb14d520bf9ca33994763e9caffd215280bb5f5ee7a49ed90b",
}


def main():
    overall_pass = True
    commits = set()
    for arm in (16, 8):
        vals = []
        print(f"\n=== ARM k{arm} ===")
        for s in SEEDS:
            path = f"_bestrec_run/results_SOTACONF_V2_k{arm}_MI_seed{s}.json"
            try:
                d = json.load(open(path))
            except FileNotFoundError:
                print(f"  seed {s}: MISSING"); overall_pass = False; continue
            b = d["best_test"]; p = d.get("provenance", {})
            n = b["NDCG@10"]
            vals.append(n)
            commits.add((p.get("git_commit"), p.get("git_dirty_tracked")))
            hash_ok = all(p.get("data_sha256", {}).get(k) == v
                          for k, v in PREREG_HASHES.items())
            print(f"  seed {s}: NDCG@10={n:.5f} HR@10={b['HR@10']:.5f} "
                  f"n_eval={b['n_eval']} best_ep={p.get('best_test_epoch')} "
                  f"hashes_ok={hash_ok} >{TARGET}: {n > TARGET}")
            if not hash_ok:
                overall_pass = False
        if len(vals) == 5:
            m = sum(vals) / 5
            sd = math.sqrt(sum((x - m) ** 2 for x in vals) / 4)
            lb = m - T975_DF4 * sd / math.sqrt(5)
            npos = sum(1 for x in vals if x > TARGET)
            gate = lb > TARGET
            print(f"  mean={m:.5f} sd={sd:.5f} CI-LB={lb:.5f} "
                  f"seeds>{TARGET}: {npos}/5")
            print(f"  ARM GATE (CI-LB > {TARGET}): {'PASS' if gate else 'FAIL'}")
            overall_pass = overall_pass and gate and npos >= 4
        else:
            overall_pass = False
    print("\n=== provenance consistency ===")
    for c, dirty in sorted(commits, key=str):
        print(f"  git_commit={c} dirty_tracked={dirty}")
    if len({c for c, _ in commits}) > 1:
        print("  WARNING: runs span multiple commits — VOID per prereg"); overall_pass = False
    if any(dirty for _, dirty in commits):
        print("  WARNING: dirty tracked tree during runs — VOID per prereg"); overall_pass = False
    print(f"\n=== DUAL GATE VERDICT: {'PASS' if overall_pass else 'FAIL'} ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
