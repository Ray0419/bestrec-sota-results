# -*- coding: utf-8 -*-
"""DESIGN_RHO_K_MATCHED_COVERAGE: forced-coverage pool conversion rho(k).

Instrument, not a benchmark: for every test event, build a candidate pool
  pool(K) = top-(K-1) of retriever Q  ∪  {gold}          (coverage forced to 1)
and measure the CONDITIONAL conversion of the ranker M (our trained checkpoint)
  R(k) = P(gold in top-10 of pool | gold in pool),
sliced by the target item's pre-cutoff training degree k.  Because coverage is
1 by construction in every degree bucket, no retriever-induced selection can
enter R (weakness 5.1 of DERIVATION_COVERAGE_BREAKEVEN).  We ALSO record the
natural-coverage subset (gold organically in top-(K-1)) and R on that subset:
the forced-vs-natural gap directly quantifies the selection bias we bypass.

Retrievers (both reported):
  text : cosine(mean frozen-SBERT of the event's warm history, item title)
  pop  : pre-cutoff training degree (static popularity)
Both are availability-masked and seen-excluded exactly like the model scores.

Structural sanity gates (fail -> report nothing):
  G1  hit10(pool) >= hit10(full catalog) per bucket   (pool ⊆ catalog)
  G2  hit10(pool) non-increasing in K                 (larger pool is harder)

Nested pools: retriever top-(Kmax-1) is computed once; every K is a prefix.
Rank of gold in pool = #{j in prefix : s_j > s_gold} with the same tie
convention as poc_temporal_eval (strictly-greater count).
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np
import torch

WORKTREE_RUN = os.path.dirname(os.path.abspath(__file__))
MAIN_RUN = r"C:\Users\rayxc\Documents\R\_bestrec_run"
sys.path.insert(0, WORKTREE_RUN)
sys.path.insert(0, MAIN_RUN)
import run_sasrec_sbert as rsp                      # noqa: E402
from fuse_ease_eval import build_model_from_config  # noqa: E402
from poc_temporal_eval import build_events, DEVICE  # noqa: E402

DEG_BINS = [(0, 0), (1, 2), (3, 5), (6, 10), (11, 20), (21, 50),
            (51, 200), (201, 10 ** 9)]


def bucket_name(lo, hi):
    return f"k{lo}-{hi}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_json")
    ap.add_argument("--ks", default="100,200,500,1000",
                    help="pool sizes; K=200 primary (matches arXiv:2606.29947)")
    ap.add_argument("--event-stride", type=int, default=2,
                    help="same declared thinning as the degree evals")
    ap.add_argument("--top-k", type=int, default=10)
    ap.add_argument("--batch-size", type=int, default=256)
    ap.add_argument("--n-buckets", type=int, default=60)
    ap.add_argument("--window", choices=("outer", "inner"), default="outer",
                    help="AMENDMENT A1 E4: 'inner' evaluates the 0.60-0.75 band")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    KS = sorted(int(x) for x in args.ks.split(","))
    kmax = KS[-1]

    run = json.load(open(args.run_json, encoding="utf-8"))
    cfg = run["config"]
    cat = cfg["category"]
    ctx = build_events(cat, cfg.get("temporal_inner_q", 0.60),
                       cfg.get("temporal_outer_q", 0.75),
                       window=args.window, stride=args.event_stride)
    n_items = ctx["n_items"]
    print(f"=== pool conversion {cat} | {os.path.basename(args.run_json)} ===")
    print(f"  events {len(ctx['test_events']):,}  Ks {KS}", flush=True)

    sb = np.load(rsp.EMB_CACHE_DIR / f"sbert_titles_{cat}.npy").astype(np.float32)[:n_items]
    ck = torch.load(args.run_json.replace(".json", ".best.pt"),
                    map_location="cpu", weights_only=False)
    proto = [t.to(DEVICE) for t in ck.get("proto_assign", [])] or None
    model = build_model_from_config(cfg, n_items, n_items,
                                    None if cfg.get("no_sbert") else sb, proto)
    model.load_state_dict(ck["state_dict"], strict=False)
    model.to(DEVICE).eval()
    model.pad_id = n_items
    with torch.no_grad():
        tab = model.all_item_features().detach().to(DEVICE).float()

    Sn = sb / np.maximum(np.linalg.norm(sb, axis=1, keepdims=True), 1e-8)
    text_S = torch.from_numpy(Sn.astype(np.float32)).to(DEVICE)
    pop_sc = torch.from_numpy(ctx["deg"].astype(np.float32)).to(DEVICE)
    deg = ctx["deg"]
    first_t = torch.from_numpy(ctx["first"]).to(DEVICE)
    warm_np = ctx["warm"]
    by_user = ctx["by_user"]
    ev = ctx["test_events"]
    max_seq_len = cfg["max_seq_len"]

    # accumulators: [retriever][bucket][K] -> counts
    RETR = ("text", "pop")
    Z = lambda: {K: {"n": 0, "hit_forced": 0, "nat_cov": 0, "hit_nat": 0}
                 for K in KS}
    acc = {r: {bucket_name(*b): Z() for b in DEG_BINS} for r in RETR}
    full_hit = {bucket_name(*b): [0, 0] for b in DEG_BINS}   # full-catalog hit10

    bounds = np.linspace(0, len(ev), args.n_buckets + 1).astype(int)
    with torch.no_grad():
        for bi in range(args.n_buckets):
            lo, hi = bounds[bi], bounds[bi + 1]
            if hi <= lo:
                continue
            chunk = ev[lo:hi]
            avail = first_t <= int(chunk[0][3])
            for s0 in range(0, len(chunk), args.batch_size):
                bt = chunk[s0:s0 + args.batch_size]
                B = len(bt)
                ids = torch.full((B, max_seq_len), model.pad_id,
                                 dtype=torch.long, device=DEVICE)
                for k, e in enumerate(bt):
                    u, t = e[0], e[3]
                    h = [x[1] for x in by_user[u]
                         if x[3] < t and warm_np[x[1]]][-max_seq_len:]
                    if h:
                        ids[k, :len(h)] = torch.tensor(h, dtype=torch.long,
                                                       device=DEVICE)
                hid = model.encode(ids, times=None)
                lastp = torch.tensor(
                    [max(0, min(max_seq_len,
                                len([x for x in by_user[e[0]]
                                     if x[3] < e[3] and warm_np[x[1]]])) - 1)
                     for e in bt], device=DEVICE)
                h_last = hid[torch.arange(B, device=DEVICE), lastp, :]
                tgt = torch.tensor([e[1] for e in bt], dtype=torch.long,
                                   device=DEVICE)
                ar = torch.arange(B, device=DEVICE)
                seen = [torch.tensor([x[1] for x in by_user[e[0]]
                                      if x[3] < e[3]],
                                     dtype=torch.long, device=DEVICE)
                        for e in bt]
                # ---- ranker scores (full catalog, masked, gold restored) ----
                base = h_last @ tab.T
                base = base.masked_fill(~avail.unsqueeze(0), -float("inf"))
                for k, sidx in enumerate(seen):
                    if len(sidx):
                        base[k, sidx] = -float("inf")
                base[ar, tgt] = torch.where(
                    torch.isinf(base[ar, tgt]),
                    (h_last * tab[tgt]).sum(-1), base[ar, tgt])
                s_gold = base[ar, tgt]
                full_rank = (base > s_gold.unsqueeze(1)).sum(1)
                # ---- retriever scores, same masking ----
                pad_mask = (ids < n_items).float()
                safe_ids = ids.clamp(max=n_items - 1)
                hist_emb = text_S[safe_ids] * pad_mask.unsqueeze(-1)
                ht = hist_emb.sum(1) / pad_mask.sum(1).clamp_min(1).unsqueeze(-1)
                ht = ht / ht.norm(dim=-1, keepdim=True).clamp_min(1e-8)
                retr_scores = {"text": ht @ text_S.T,
                               "pop": pop_sc.unsqueeze(0).expand(B, -1).clone()}
                tb = deg[[e[1] for e in bt]]
                bnames = []
                for d in tb:
                    for (blo, bhi) in DEG_BINS:
                        if blo <= d <= bhi:
                            bnames.append(bucket_name(blo, bhi))
                            break
                fh = (full_rank < args.top_k).cpu().numpy()
                for k in range(B):
                    full_hit[bnames[k]][0] += int(fh[k])
                    full_hit[bnames[k]][1] += 1
                for rname, rsc in retr_scores.items():
                    rsc = rsc.masked_fill(~avail.unsqueeze(0), -float("inf"))
                    for k, sidx in enumerate(seen):
                        if len(sidx):
                            rsc[k, sidx] = -float("inf")
                    topi = torch.topk(rsc, kmax - 1, dim=1).indices  # (B,kmax-1)
                    pool_sc = torch.gather(base, 1, topi)
                    gt = (pool_sc > s_gold.unsqueeze(1)).long().cumsum(1)
                    isg = (topi == tgt.unsqueeze(1)).long().cumsum(1)
                    for K in KS:
                        cnt = gt[:, K - 2]           # rank among pool w/o gold
                        hit = (cnt < args.top_k).cpu().numpy()
                        nat = (isg[:, K - 2] > 0).cpu().numpy()
                        for k in range(B):
                            a = acc[rname][bnames[k]][K]
                            a["n"] += 1
                            a["hit_forced"] += int(hit[k])
                            a["nat_cov"] += int(nat[k])
                            if nat[k]:
                                a["hit_nat"] += int(hit[k])

    # ---- report + gates ----
    rep = {"run": os.path.basename(args.run_json), "category": cat,
           "ks": KS, "stride": args.event_stride,
           "full_catalog_hit10": {b: {"hit": h, "n": n}
                                  for b, (h, n) in full_hit.items()},
           "pool": acc}
    gates = {"G1": True, "G2": True}
    for rname in RETR:
        for b in acc[rname]:
            n_full = full_hit[b][1]
            r_full = (full_hit[b][0] / n_full) if n_full else 0.0
            prev = 1.1
            for K in KS:
                a = acc[rname][b][K]
                r_pool = (a["hit_forced"] / a["n"]) if a["n"] else 0.0
                if a["n"] >= 50 and r_pool < r_full - 1e-9:
                    gates["G1"] = False
                if a["n"] >= 50 and r_pool > prev + 0.02:   # tolerance
                    gates["G2"] = False
                prev = r_pool
    rep["gates"] = gates
    print(f"\n  gates: G1(pool>=full) {'PASS' if gates['G1'] else 'FAIL'}   "
          f"G2(monotone in K) {'PASS' if gates['G2'] else 'FAIL'}")
    for rname in RETR:
        print(f"\n  --- retriever {rname} (K=200) ---")
        print(f"  {'bucket':<16}{'n':>8}{'R_forced':>10}{'natCov':>8}{'R_nat':>8}{'fullHit':>9}")
        for (blo, bhi) in DEG_BINS:
            b = bucket_name(blo, bhi)
            a = acc[rname][b][200 if 200 in KS else KS[0]]
            if a["n"] == 0:
                continue
            rn = a["hit_nat"] / a["nat_cov"] if a["nat_cov"] else float("nan")
            fh, fn = full_hit[b]
            print(f"  {b:<16}{a['n']:>8}{a['hit_forced']/a['n']:>10.4f}"
                  f"{a['nat_cov']/a['n']:>8.3f}{rn:>8.4f}{fh/max(fn,1):>9.4f}")
    dst = args.out or os.path.join(WORKTREE_RUN, "poc_out",
                                   os.path.basename(args.run_json).replace(
                                       ".json", ".pool_conv.json"))
    json.dump(rep, open(dst, "w", encoding="utf-8"), indent=1)
    print(f"\nwrote {dst}")


if __name__ == "__main__":
    main()
