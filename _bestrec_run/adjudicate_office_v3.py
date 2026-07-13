#!/usr/bin/env python
"""Mechanical adjudicator for PREREG_OFFICE_V3.md (frozen gate).

Headline rule (identical to the corrected V1 adjudication, mirroring
office_prereg_tools.py::_final_full): the FINAL-epoch FULL-catalog eval --
history[-1].test with n_eval == 223,308 asserted -- NOT best_test.

Gate (frozen), per kernel arm (k16, k8) over seeds 20260728..20260732:
  PASS iff the two-sided 95% Student-t CI LOWER BOUND of final-epoch
  full-catalog NDCG@10 exceeds 0.0279 (environment-matched local regeneration,
  the stricter reference; > published 0.0271 by construction) AND >=4/5 seeds
  individually exceed 0.0279.
Campaign is a second-category confirmation only if BOTH arms pass.

Comparability conditions (all three must hold, else the campaign is VOID):
  1. Dataset identity: every run manifest must show 223,308 users / 77,551
     items; total interactions 1,800,878 (within +/-1 of the comparator
     pipeline's 1,800,877 -- the known CSV-header quirk, THEIRS_ON_OURS_REPORT.md).
  2. Environment-matched reference: the theirs_runs/office_hstu_blair source
     artifacts must hash-match the pinned RELEASE_MANIFEST.json reference_runs
     entries, and the reference readings re-derived from metrics.jsonl must
     still be best full-eval 0.0279 / final 0.0275 (4 dp).
  3. Provenance: every run manifest must show a clean tracked tree
     (git_dirty_tracked false), embedded code hashes present and identical
     across all 10 runs, and data SHA256s identical across all 10 runs.

Appends one idempotent dated block per invocation-content to
OFFICE_V3_RESULTS.md at the repo root (created with a header if absent).

Exit codes: --report (default) always 0. --gate exits 1 unless the campaign
verdict is PASS. --no-append skips the results-file write (validation use).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RES_MD = ROOT / "OFFICE_V3_RESULTS.md"
REF_DIR = HERE / "theirs_runs"

# Frozen in PREREG_OFFICE_V3.md
ARMS = [16, 8]
SEEDS = [20260728, 20260729, 20260730, 20260731, 20260732]
T975_DF4 = 2.776
REF_LOCAL = 0.0279     # environment-matched local regeneration, best full-eval
REF_PUBLISHED = 0.0271  # published HSTU-BLaIR point estimate
REF_FINAL_LOCAL = 0.0275
N_USERS = 223308
N_ITEMS = 77551
N_INTER_OURS = 1800878      # our split total (train+valid+test)
N_INTER_THEIRS = 1800877    # comparator corpus (CSV-header quirk: -1)
REFERENCE_FILES = [  # pinned in RELEASE_MANIFEST.json reference_runs.files
    "_bestrec_run/theirs_runs/office_hstu_blair/hstu-sampled-softmax-n512-blair.gin",
    "_bestrec_run/theirs_runs/office_hstu_blair/metrics.jsonl",
    "_bestrec_run/theirs_runs/office_hstu_blair/run_meta.json",
    "_bestrec_run/theirs_runs/office_hstu_blair/tb_logdir_intended.txt",
    "_bestrec_run/theirs_runs/office_hstu_blair.log",
]

HEADER = """# Office_Products V3 campaign results (PREREG_OFFICE_V3.md)

Mechanical adjudication blocks appended by `_bestrec_run/adjudicate_office_v3.py`.
Gate (frozen before any run): per kernel arm over 5 fresh seeds, final-epoch
FULL-catalog NDCG@10 (history[-1].test, n_eval == 223,308) 95% t-CI lower bound
must exceed 0.0279 (environment-matched local regeneration of the comparator)
with >=4/5 seeds individually above it; both arms must pass; comparability
conditions 1-3 must hold. One-sided failures, nulls and voids are published
with identical prominence.
"""


def sha256(p: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def final_full(d: dict) -> dict:
    """Mirror of office_prereg_tools.py::_final_full on a loaded results dict."""
    fin = [h for h in d["history"] if "test" in h][-1]
    t = fin["test"]
    assert t["n_eval"] == N_USERS, f"final eval not full-catalog: {t['n_eval']}"
    return t


def load_run(path: Path):
    if not path.exists():
        return None, "missing"
    try:
        d = json.load(open(path, encoding="utf-8"))
    except Exception as e:
        return None, f"unparseable ({e.__class__.__name__})"
    if not d.get("history"):
        return None, "no history"
    return d, None


def check_condition2(lines: list[str]) -> bool:
    """Reference-artifact identity vs RELEASE_MANIFEST + re-derived readings."""
    ok = True
    try:
        man = json.load(open(ROOT / "RELEASE_MANIFEST.json", encoding="utf-8"))
        pinned = man["reference_runs"]["files"]
    except Exception as e:
        lines.append(f"- cond2: cannot read RELEASE_MANIFEST.json reference_runs ({e})")
        return False
    for rel in REFERENCE_FILES:
        p = ROOT / rel
        if rel not in pinned:
            lines.append(f"- cond2: {rel} not pinned in RELEASE_MANIFEST reference_runs")
            ok = False
            continue
        if not p.exists():
            lines.append(f"- cond2: {rel} MISSING on disk")
            ok = False
            continue
        h = sha256(p)
        if h != pinned[rel]["sha256"]:
            lines.append(f"- cond2: {rel} sha256 DRIFT (disk {h[:16]}... != pinned "
                         f"{pinned[rel]['sha256'][:16]}...)")
            ok = False
    # re-derive the reference readings from the pinned metrics stream
    try:
        best = None
        final = None
        with open(REF_DIR / "office_hstu_blair" / "metrics.jsonl", encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                if r.get("prefix") == "eval_epoch_full":
                    v = r["ndcg@10"]
                    final = v
                    best = v if best is None else max(best, v)
        rb, rf = round(best, 4), round(final, 4)
        lines.append(f"- cond2: re-derived reference best full-eval NDCG@10 = {best:.5f} "
                     f"(-> {rb}) / final = {final:.5f} (-> {rf})")
        if rb != REF_LOCAL or rf != REF_FINAL_LOCAL:
            lines.append(f"- cond2: re-derived readings != frozen references "
                         f"({REF_LOCAL}/{REF_FINAL_LOCAL}) -> VOID")
            ok = False
    except Exception as e:
        lines.append(f"- cond2: cannot re-derive reference readings ({e})")
        ok = False
    if ok:
        lines.append(f"- cond2 OK: all {len(REFERENCE_FILES)} reference artifacts hash-match "
                     f"RELEASE_MANIFEST; references re-derived as {REF_LOCAL} (best) / "
                     f"{REF_FINAL_LOCAL} (final)")
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gate", action="store_true",
                    help="exit 1 unless campaign verdict is PASS (default --report: always exit 0)")
    ap.add_argument("--report", action="store_true", help="report mode (default)")
    ap.add_argument("--no-append", action="store_true",
                    help="print only; do not touch OFFICE_V3_RESULTS.md")
    args = ap.parse_args()

    lines: list[str] = []
    cond_ok = True

    # ---- load runs -------------------------------------------------------
    runs = {}
    missing = []
    for arm in ARMS:
        for s in SEEDS:
            p = HERE / f"results_OFFICEV3_k{arm}_seed{s}.json"
            d, why = load_run(p)
            if d is None:
                missing.append(f"k{arm} seed {s}: {why}")
            else:
                runs[(arm, s)] = d
    if missing:
        lines.append(f"- runs present: {len(runs)}/10; " + "; ".join(missing))

    # ---- comparability condition 1 + 3 (over present runs) ---------------
    for (arm, s), d in sorted(runs.items()):
        prov = d.get("provenance", {})
        ni = prov.get("n_interactions", {})
        tot = sum(ni.values()) if ni else -1
        if d.get("n_users") != N_USERS or d.get("n_items") != N_ITEMS:
            lines.append(f"- cond1 FAIL k{arm} seed {s}: users/items "
                         f"{d.get('n_users')}/{d.get('n_items')} != {N_USERS}/{N_ITEMS}")
            cond_ok = False
        if tot != N_INTER_OURS or abs(tot - N_INTER_THEIRS) > 1:
            lines.append(f"- cond1 FAIL k{arm} seed {s}: interactions {tot} "
                         f"(expected {N_INTER_OURS}; comparator {N_INTER_THEIRS} +/-1)")
            cond_ok = False
        if prov.get("git_dirty_tracked") is not False:
            # PREREG_OFFICE_V3.md ERRATUM E1: the two external audit-log files
            # are exempt. A dirty flag is acceptable ONLY if the driver's
            # per-run treestate sidecar shows every dirty path is exempt.
            E1_EXEMPT = {"PAPER_REVIEW_AUDIT.md", "RESPONSE_TO_PAPER_REVIEW_AUDIT.md"}
            ts_path = HERE / f"results_OFFICEV3_k{arm}_seed{s}.json.treestate.txt"
            ok_e1 = False
            if ts_path.exists():
                paths = set()
                for ln in open(ts_path, encoding="utf-8", errors="replace"):
                    ln = ln.rstrip("\n")
                    if not ln or ln.startswith("----"):
                        continue
                    paths.add(ln[3:].strip().replace("\\", "/"))
                ok_e1 = bool(paths) and paths.issubset(E1_EXEMPT)
            if ok_e1:
                lines.append(f"- cond3 OK (E1) k{arm} seed {s}: dirty tree consists only of "
                             "exempt audit-log files per PREREG_OFFICE_V3.md E1 "
                             "(treestate sidecar verified)")
            else:
                lines.append(f"- cond3 FAIL k{arm} seed {s}: git_dirty_tracked = "
                             f"{prov.get('git_dirty_tracked')!r} and treestate sidecar does "
                             "not prove E1-exempt-only dirt (clean tracked tree required)")
                cond_ok = False
        if not prov.get("code_sha256", {}).get("run_sasrec_sbert.py"):
            lines.append(f"- cond3 FAIL k{arm} seed {s}: embedded code hashes missing")
            cond_ok = False
        if d.get("config", {}).get("seed") != s:
            lines.append(f"- VOID k{arm} seed {s}: config seed "
                         f"{d.get('config', {}).get('seed')} (seed substitution)")
            cond_ok = False
        # sidecar presence (warn-level): final-epoch per-user records are the
        # best-by-val sidecar when best epoch == final epoch.
        if not (prov.get("user_records_final_path") or prov.get("user_records_path")):
            lines.append(f"- WARN k{arm} seed {s}: no per-user sidecar recorded in manifest")
    if runs:
        code_ids = {prov_code for prov_code in
                    (json.dumps(d["provenance"].get("code_sha256"), sort_keys=True)
                     for d in runs.values())}
        if len(code_ids) != 1:
            lines.append("- cond3 FAIL: embedded code hashes differ across runs")
            cond_ok = False
        data_ids = {json.dumps(d["provenance"].get("data_sha256"), sort_keys=True)
                    for d in runs.values()}
        if len(data_ids) != 1:
            lines.append("- cond3 FAIL: data_sha256 differ across runs")
            cond_ok = False
        commits = {d["provenance"].get("git_commit") for d in runs.values()}
        lines.append(f"- git commits across runs: {sorted(str(c)[:12] for c in commits)}"
                     + (" (multiple; code identity via embedded hashes)" if len(commits) > 1 else ""))
        if len(runs) == 10 and cond_ok:
            lines.append(f"- cond1 OK: all 10 manifests record {N_USERS:,} users / "
                         f"{N_ITEMS:,} items / {N_INTER_OURS:,} interactions "
                         f"(comparator {N_INTER_THEIRS:,}, delta 1 <= 1)")
            lines.append("- cond3 OK: clean tracked tree, identical embedded code hashes "
                         "and data SHA256s across all 10 runs")

    # ---- comparability condition 2 ----------------------------------------
    cond2_ok = check_condition2(lines)
    cond_ok = cond_ok and cond2_ok

    # ---- per-arm gate ------------------------------------------------------
    arm_verdicts = {}
    for arm in ARMS:
        vals = []
        bad = False
        for s in SEEDS:
            d = runs.get((arm, s))
            if d is None:
                bad = True
                continue
            try:
                t = final_full(d)
            except AssertionError as e:
                lines.append(f"- VOID k{arm} seed {s}: {e}")
                bad = True
                continue
            vals.append((s, t["NDCG@10"]))
        for s, v in vals:
            lines.append(f"- k{arm} seed {s}: final-epoch full-catalog NDCG@10 = {v:.5f} "
                         f"({'>' if v > REF_LOCAL else '<='} {REF_LOCAL}; "
                         f"{'>' if v > REF_PUBLISHED else '<='} {REF_PUBLISHED})")
        if bad or len(vals) < 5:
            arm_verdicts[arm] = "VOID"
            lines.append(f"- **ARM k{arm}: VOID** (<5 valid final-epoch full-catalog runs)")
            continue
        xs = [v for _, v in vals]
        mean = sum(xs) / 5
        sd = math.sqrt(sum((x - mean) ** 2 for x in xs) / 4)
        lb = mean - T975_DF4 * sd / math.sqrt(5)
        npos_local = sum(1 for x in xs if x > REF_LOCAL)
        npos_pub = sum(1 for x in xs if x > REF_PUBLISHED)
        gate = (lb > REF_LOCAL) and (npos_local >= 4)
        arm_verdicts[arm] = "PASS" if gate else "FAIL"
        lines.append(f"- **ARM k{arm}**: mean {mean:.5f}  sd {sd:.5f}  95% CI-LB {lb:.5f}  "
                     f"vs {REF_LOCAL}: LB {'>' if lb > REF_LOCAL else '<='} ref, "
                     f"{npos_local}/5 seeds above; vs {REF_PUBLISHED}: "
                     f"LB {'>' if lb > REF_PUBLISHED else '<='} ref, {npos_pub}/5 seeds above "
                     f"-> **{arm_verdicts[arm]}**")

    # ---- campaign verdict ---------------------------------------------------
    if not cond_ok or any(v == "VOID" for v in arm_verdicts.values()) or len(runs) < 10:
        campaign = "VOID"
    elif all(arm_verdicts.get(a) == "PASS" for a in ARMS):
        campaign = "PASS"
    else:
        campaign = "FAIL"
    lines.append(f"\n**CAMPAIGN VERDICT: {campaign}** "
                 f"(arms: " + ", ".join(f"k{a}: {arm_verdicts.get(a, 'VOID')}" for a in ARMS)
                 + f"; comparability conditions {'OK' if cond_ok else 'VIOLATED'})")
    if campaign == "PASS":
        lines.append("\nFrozen claim wording applies (PREREG_OFFICE_V3.md): a per-category "
                     "point-estimate comparison against the published 0.0271 and the "
                     "environment-matched single-run local regeneration 0.0279; no paired or "
                     "distributional superiority claimed; not SOTA on Office_Products, not SOTA "
                     "on Amazon Reviews 2023, and not a general-SOTA claim of any kind.")

    body = "".join(l + "\n" for l in lines)
    block_id = hashlib.sha256(body.encode()).hexdigest()[:12]
    date = time.strftime("%Y-%m-%d %H:%M:%S")
    block = (f"\n---\n\n## Adjudication {date} (block-id {block_id})\n"
             f"Arms k16/k8; seeds {SEEDS}; gate frozen in PREREG_OFFICE_V3.md.\n\n"
             + body)
    print(block)

    if not args.no_append:
        if not RES_MD.exists():
            RES_MD.write_text(HEADER, encoding="utf-8")
        existing = RES_MD.read_text(encoding="utf-8")
        if f"block-id {block_id}" in existing:
            print(f"(identical adjudication block {block_id} already recorded; append skipped)")
        else:
            with RES_MD.open("a", encoding="utf-8") as f:
                f.write(block)
            print(f"appended block {block_id} to {RES_MD}")

    if args.gate:
        return 0 if campaign == "PASS" else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
