# -*- coding: utf-8 -*-
"""PREREG_RHO_K_V1 AMENDMENT A1, E1/E2: own-dataset coverage trade + rule validation.

Quota-mix retriever at fixed K (default 200), NO forced gold:
  n_text = round(lambda*K) slots from text-kNN (priority), remainder filled
  from the popularity ranking skipping duplicates -> pool of exactly K unique
  items (declared, exact).  lambda in {0, 0.1, ..., 1.0}.
Per event we record, for every lambda:
  * coverage:  gold in pool            (per degree bucket)
  * success:   gold in pool AND ranked into the pool's top-10 by the ranker
The E2 prediction Sigma_b w_b * dCov_b(lambda) * R_b is computed by the
analysis step from the forced-coverage R_b already on disk; this script only
measures.  Vectorized: dedupe via a scatter buffer + cumsum quota, gold's
in-pool rank via strictly-greater counts over the text part and the taken pop
part (same tie convention as poc_temporal_eval).
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
LAMBDAS = [round(0.1 * i, 1) for i in range(11)]


def bname(lo, hi):
    return f"k{lo}-{hi}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_json")
    ap.add_argument("--k", type=int, default=200)
    ap.add_argument("--top-k", type=int, default=10)
    ap.add_argument("--event-stride", type=int, default=2)
    ap.add_argument("--batch-size", type=int, default=256)
    ap.add_argument("--n-buckets", type=int, default=60)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    K = args.k

    run = json.load(open(args.run_json, encoding="utf-8"))
    cfg = run["config"]
    cat = cfg["category"]
    ctx = build_events(cat, cfg.get("temporal_inner_q", 0.60),
                       cfg.get("temporal_outer_q", 0.75),
                       stride=args.event_stride)
    n_items = ctx["n_items"]
    print(f"=== coverage trade {cat} | {os.path.basename(args.run_json)} "
          f"K={K} ===", flush=True)

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
    pop_sc0 = torch.from_numpy(ctx["deg"].astype(np.float32)).to(DEVICE)
    deg = ctx["deg"]
    first_t = torch.from_numpy(ctx["first"]).to(DEVICE)
    warm_np = ctx["warm"]
    by_user = ctx["by_user"]
    ev = ctx["test_events"]
    max_seq_len = cfg["max_seq_len"]

    NL = [round(l * K) for l in LAMBDAS]           # n_text per lambda
    acc = {bname(*b): {l: {"n": 0, "cov": 0, "suc": 0} for l in LAMBDAS}
           for b in DEG_BINS}

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
                # ranker scores (masked; gold restored so its rank is real)
                base = h_last @ tab.T
                base = base.masked_fill(~avail.unsqueeze(0), -float("inf"))
                for k, sidx in enumerate(seen):
                    if len(sidx):
                        base[k, sidx] = -float("inf")
                base[ar, tgt] = torch.where(
                    torch.isinf(base[ar, tgt]),
                    (h_last * tab[tgt]).sum(-1), base[ar, tgt])
                s_gold = base[ar, tgt]
                # retriever scores, same masking (gold NOT restored: no forcing)
                pad_mask = (ids < n_items).float()
                safe_ids = ids.clamp(max=n_items - 1)
                hist_emb = text_S[safe_ids] * pad_mask.unsqueeze(-1)
                ht = hist_emb.sum(1) / pad_mask.sum(1).clamp_min(1).unsqueeze(-1)
                ht = ht / ht.norm(dim=-1, keepdim=True).clamp_min(1e-8)
                tex = ht @ text_S.T
                pop = pop_sc0.unsqueeze(0).expand(B, -1).clone()
                for sc in (tex, pop):
                    sc.masked_fill_(~avail.unsqueeze(0), -float("inf"))
                    for k, sidx in enumerate(seen):
                        if len(sidx):
                            sc[k, sidx] = -float("inf")
                ti = torch.topk(tex, K, dim=1).indices        # (B, K)
                pi_ = torch.topk(pop, K, dim=1).indices       # (B, K)
                t_sc = torch.gather(base, 1, ti)
                p_sc = torch.gather(base, 1, pi_)
                t_is_g = ti == tgt.unsqueeze(1)
                p_is_g = pi_ == tgt.unsqueeze(1)
                t_gt = (t_sc > s_gold.unsqueeze(1)).long()
                p_gt = (p_sc > s_gold.unsqueeze(1)).long()
                tb = deg[[e[1] for e in bt]]
                bn = []
                for d in tb:
                    for (blo, bhi) in DEG_BINS:
                        if blo <= d <= bhi:
                            bn.append(bname(blo, bhi))
                            break
                buf = torch.zeros((B, n_items), dtype=torch.bool, device=DEVICE)
                for lam, ntx in zip(LAMBDAS, NL):
                    npo = K - ntx
                    # membership buffer for the text part
                    buf.zero_()
                    if ntx:
                        buf.scatter_(1, ti[:, :ntx], True)
                    if npo:
                        is_new = ~torch.gather(buf, 1, pi_)
                        take = is_new & (is_new.long().cumsum(1) <= npo)
                    else:
                        take = torch.zeros_like(p_is_g)
                    cov = ((t_is_g[:, :ntx].any(1) if ntx else
                            torch.zeros(B, dtype=torch.bool, device=DEVICE))
                           | (p_is_g & take).any(1))
                    cnt = ((t_gt[:, :ntx].sum(1) if ntx else
                            torch.zeros(B, dtype=torch.long, device=DEVICE))
                           + (p_gt * take.long()).sum(1))
                    suc = cov & (cnt < args.top_k)
                    cv = cov.cpu().numpy()
                    su = suc.cpu().numpy()
                    for k in range(B):
                        a = acc[bn[k]][lam]
                        a["n"] += 1
                        a["cov"] += int(cv[k])
                        a["suc"] += int(su[k])

    rep = {"run": os.path.basename(args.run_json), "category": cat, "K": K,
           "stride": args.event_stride, "lambdas": LAMBDAS,
           "buckets": {b: {str(l): v for l, v in d.items()}
                       for b, d in acc.items()}}
    # quick console: overall coverage/success vs lambda
    print(f"  {'lam':>5}{'Cov_all':>9}{'S_all':>9}{'Cov_cold(k0)':>13}{'Cov_k1-50':>11}")
    for lam in LAMBDAS:
        n = c = s = 0
        n0 = c0 = 0
        nm = cm = 0
        for (blo, bhi) in DEG_BINS:
            a = acc[bname(blo, bhi)][lam]
            n += a["n"]; c += a["cov"]; s += a["suc"]
            if bhi == 0:
                n0 += a["n"]; c0 += a["cov"]
            if 1 <= blo <= 21:
                nm += a["n"]; cm += a["cov"]
        print(f"  {lam:>5}{c/max(n,1):>9.4f}{s/max(n,1):>9.4f}"
              f"{c0/max(n0,1):>13.4f}{cm/max(nm,1):>11.4f}")
    dst = args.out or os.path.join(WORKTREE_RUN, "poc_out",
                                   os.path.basename(args.run_json).replace(
                                       ".json", ".cov_trade.json"))
    json.dump(rep, open(dst, "w", encoding="utf-8"), indent=1)
    print(f"wrote {dst}", flush=True)


if __name__ == "__main__":
    main()
