# -*- coding: utf-8 -*-
"""PREREG_TEMPORAL_V1 reporting evaluation: per-event, availability-constrained.

Protocol ported from the parallel session's run_poc_temporal_lc2c_v1.py.
Their design; our sequential backbone at ~70x their catalog size.

Differences from the trainer's internal eval (which is a SELECTION PROXY ONLY):
  * per EVENT, not one target per user -- a user contributes every post-cutoff
    event they have;
  * per-event history = the user's interactions strictly BEFORE that event,
    restricted to WARM items (first appearance <= inner cutoff), i.e. items the
    model actually has trained embeddings for. The trainer freezes history at
    the training cutoff, which makes far-future events artificially hard;
  * FIRST-AVAILABILITY constraint: at an event with time t, only items with
    first appearance <= t may be candidates. Implemented by time-bucketing --
    availability is monotone in time, so one mask per bucket via searchsorted
    gives O(buckets x items) instead of O(events x items). Each bucket uses its
    EARLIEST event time, so the mask is strictly leak-free (never admits an item
    that had not yet appeared) and is applied identically to every arm.

Endpoints (prereg S3): E1 within-pool AUC gain, E2 offset-matched efficiency
ratio, E3 break-even p*, E4 PRIMARY aggregate effect at observed prevalence.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict

import numpy as np
import torch

WORKTREE_RUN = os.path.dirname(os.path.abspath(__file__))
MAIN_RUN = r"C:\Users\rayxc\Documents\R\_bestrec_run"
sys.path.insert(0, WORKTREE_RUN)
sys.path.insert(0, MAIN_RUN)
import run_sasrec_sbert as rsp                      # noqa: E402
from fuse_ease_eval import build_model_from_config  # noqa: E402
from poc_posterior_eval import knn_prior            # noqa: E402

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


def build_events(category, inner_q, outer_q, window="outer", stride=1):
    tr = rsp.load_split_csv(rsp.SPLIT_DIR / f"{category}.train.csv")
    va = rsp.load_split_csv(rsp.SPLIT_DIR / f"{category}.valid.csv")
    te = rsp.load_split_csv(rsp.SPLIT_DIR / f"{category}.test.csv")
    a, b, c, users, items = rsp.reindex(tr, va, te)
    pooled = a + b + c
    n_items = len(items)
    ts = np.array([e[3] for e in pooled], dtype=np.int64)
    t_in = int(np.quantile(ts, inner_q, method="nearest"))
    t_out = int(np.quantile(ts, outer_q, method="nearest"))
    first = np.full(n_items, np.iinfo(np.int64).max, dtype=np.int64)
    for (_, i, _, t) in pooled:
        if t < first[i]:
            first[i] = t
    warm = first <= t_in                      # items the model can have learned
    by_user = defaultdict(list)
    for e in pooled:
        by_user[e[0]].append(e)
    for u in by_user:
        by_user[u].sort(key=lambda e: e[3])
    hist_users = {u for u, evs in by_user.items() if any(e[3] <= t_in for e in evs)}
    if window == "inner":
        # OOS analysis (rigor review F01): the 0.60-0.75 band, disjoint from the
        # reporting window, same training cutoff and cold definition.
        test_events = [e for e in pooled if t_in < e[3] <= t_out
                       and e[0] in hist_users]
    else:
        test_events = [e for e in pooled if e[3] > t_out and e[0] in hist_users]
    test_events.sort(key=lambda e: e[3])
    if stride > 1:
        test_events = test_events[::stride]   # deterministic thinning, declared
    # training degree (pre-inner-cutoff) per item: 0 for cold, >=1 for sparse/warm.
    deg = np.zeros(n_items, dtype=np.int64)
    for (_, i, _, t) in pooled:
        if t <= t_in:
            deg[i] += 1
    return dict(pooled=pooled, by_user=by_user, first=first, warm=warm,
                t_in=t_in, t_out=t_out, n_items=n_items, deg=deg,
                test_events=test_events)


def evaluate(model, tables, ctx, max_seq_len, offsets, n_buckets=60,
             batch_size=256, top_k=10, use_times=False, text_S=None,
             fusion_w=0.2):
    """Per-event, availability-masked scoring of every table x offset.

    Family arms (PREREG_STEAM_V1 S3.3): a table named "fusion" is scored as
    score-level z-fusion  z(stock scores) + fusion_w * z(text-cosine scores),
    where the text score is cosine(mean sbert of the event's history, item).
    fusion_w = 0.2 is the repo's COLDFUSE-adjudicated tail weight, transferred
    without retuning (declared). Requires text_S (n_items, d_t) normalized.
    The tensor stored under "fusion" must be the STOCK table.
    """
    ev = ctx["test_events"]
    first_t = torch.from_numpy(ctx["first"]).to(DEVICE)
    warm_np = ctx["warm"]
    cold_t = torch.from_numpy(~warm_np).to(DEVICE)
    n_pool_cold = int((~warm_np).sum())
    by_user, t_in = ctx["by_user"], ctx["t_in"]
    keys = [(n, d) for n in tables for d in offsets]
    acc = {k: {"nd": [], "cold": [], "auc": [], "inv": []} for k in keys}
    is_cold_all = []
    bounds = np.linspace(0, len(ev), n_buckets + 1).astype(int)
    with torch.no_grad():
        for bi in range(n_buckets):
            lo, hi = bounds[bi], bounds[bi + 1]
            if hi <= lo:
                continue
            chunk = ev[lo:hi]
            # leak-free: earliest event time in the bucket gates availability
            avail = first_t <= int(chunk[0][3])
            for s in range(0, len(chunk), batch_size):
                bt = chunk[s:s + batch_size]
                B = len(bt)
                ids = torch.full((B, max_seq_len), model.pad_id, dtype=torch.long,
                                 device=DEVICE)
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
                tex_sc = None
                if text_S is not None:
                    pad_mask = (ids < text_S.shape[0]).float()      # pad row out
                    safe_ids = ids.clamp(max=text_S.shape[0] - 1)
                    hist_emb = text_S[safe_ids] * pad_mask.unsqueeze(-1)
                    ht = hist_emb.sum(1) / pad_mask.sum(1).clamp_min(1).unsqueeze(-1)
                    ht = ht / ht.norm(dim=-1, keepdim=True).clamp_min(1e-8)
                    tex_sc = ht @ text_S.T                          # (B, n_items)
                tgt = torch.tensor([e[1] for e in bt], dtype=torch.long,
                                   device=DEVICE)
                tcold = cold_t[tgt]
                is_cold_all.extend(tcold.cpu().numpy().tolist())
                ar = torch.arange(B, device=DEVICE)
                seen = [torch.tensor([x[1] for x in by_user[e[0]] if x[3] < e[3]],
                                     dtype=torch.long, device=DEVICE) for e in bt]
                for name, tab in tables.items():
                    base = h_last @ tab.T
                    if name.startswith("fusion") and tex_sc is not None:
                        w_eff = (float(name.split("_w")[1]) if "_w" in name
                                 else fusion_w)
                        def _z(x):
                            return ((x - x.mean(dim=1, keepdim=True))
                                    / x.std(dim=1, keepdim=True).clamp_min(1e-8))
                        base = _z(base) + w_eff * _z(tex_sc)
                    base = base.masked_fill(~avail.unsqueeze(0), -float("inf"))
                    for k, sidx in enumerate(seen):
                        if len(sidx):
                            base[k, sidx] = -float("inf")
                    base[ar, tgt] = torch.where(
                        torch.isinf(base[ar, tgt]),
                        (h_last * tab[tgt]).sum(-1), base[ar, tgt])
                    for d in offsets:
                        sc = base.clone()
                        if d:
                            sc[:, cold_t] += d
                        ts_ = sc[ar, tgt]
                        rank = (sc > ts_.unsqueeze(1)).sum(1)
                        nd = torch.where(rank < top_k,
                                         1.0 / torch.log2(rank.float() + 2.0),
                                         torch.zeros_like(rank, dtype=torch.float))
                        acc[(name, d)]["nd"].extend(nd.cpu().numpy().tolist())
                        sc_c = sc[:, cold_t]
                        rin = (sc_c > ts_.unsqueeze(1)).sum(1).float()
                        auc = 1.0 - rin / max(n_pool_cold - 1, 1)
                        a2 = auc.clone()
                        a2[~tcold] = float("nan")
                        acc[(name, d)]["auc"].extend(a2.cpu().numpy().tolist())
                        if d == 0:
                            # Q4 instrumentation: did any cold item invade this
                            # event's top-k? (aggregated over warm events later)
                            kth = torch.topk(sc, top_k, dim=1).values[:, -1:]
                            inv = ((sc >= kth) & cold_t.unsqueeze(0)).any(dim=1)
                            acc[(name, d)]["inv"].extend(
                                inv.float().cpu().numpy().tolist())
    isc = np.array(is_cold_all, dtype=bool)
    # SPARSE-REGIME slices: target item's pre-cutoff training degree.
    tgt_deg = np.array([ctx["deg"][e[1]] for e in ev], dtype=np.int64)
    DEG_BINS = [(0, 0), (1, 2), (3, 5), (6, 10), (11, 20), (21, 50),
                (51, 200), (201, 10 ** 9)]
    out = {}
    for k, v in acc.items():
        nd = np.array(v["nd"])
        au = np.array(v["auc"], dtype=float)
        out[k] = {"overall": float(nd.mean()),
                  "cold": float(nd[isc].mean()) if isc.any() else float("nan"),
                  "warm": float(nd[~isc].mean()) if (~isc).any() else float("nan"),
                  "cold_auc": float(np.nanmean(au)) if isc.any() else float("nan")}
        if v["inv"]:
            iv = np.array(v["inv"], dtype=float)
            out[k]["warm_invasion_rate"] = (float(iv[~isc].mean())
                                            if (~isc).any() else float("nan"))
        if k[1] == 0.0:      # degree slices only needed at offset 0
            sl = {}
            for lo, hi in DEG_BINS:
                m = (tgt_deg >= lo) & (tgt_deg <= hi)
                if m.sum():
                    sl[f"k{lo}-{hi}"] = {"n": int(m.sum()),
                                         "ndcg10": float(nd[m].mean())}
            out[k]["by_degree"] = sl
    return out, float(isc.mean()), int(isc.sum()), len(isc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_json")
    ap.add_argument("--offsets", default="0,2,4,8")
    ap.add_argument("--family", action="store_true",
                    help="PREREG_STEAM_V1 S3.3: add ridge-imputation and "
                         "z-fusion (w=0.2, COLDFUSE-transferred) arms")
    ap.add_argument("--window", choices=("outer", "inner"), default="outer",
                    help="OOS analysis (F01): 'inner' evaluates the 0.60-0.75 "
                         "band instead of the reporting window")
    ap.add_argument("--event-stride", type=int, default=1,
                    help="deterministic every-Nth-event thinning (declared)")
    ap.add_argument("--fusion-sweep", default="",
                    help="comma-separated fusion weights, e.g. '0.05,0.1,0.2,"
                         "0.5,1.0' (Q3: tuned-vs-transferred control)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    run = json.load(open(args.run_json, encoding="utf-8"))
    cfg = run["config"]
    cat = cfg["category"]
    inner = cfg.get("temporal_inner_q", 0.60)
    outer = cfg.get("temporal_outer_q", 0.75)
    offsets = [float(x) for x in args.offsets.split(",")]
    ctx = build_events(cat, inner, outer, window=args.window,
                       stride=args.event_stride)
    print(f"=== temporal eval {cat} q_in={inner} q_out={outer} "
          f"window={args.window} stride={args.event_stride} ===")
    print(f"  test events {len(ctx['test_events']):,}  "
          f"cold items {int((~ctx['warm']).sum()):,}", flush=True)

    sb = np.load(rsp.EMB_CACHE_DIR / f"sbert_titles_{cat}.npy").astype(np.float32)[:ctx["n_items"]]
    ck = torch.load(args.run_json.replace(".json", ".best.pt"),
                    map_location="cpu", weights_only=False)
    proto = [t.to(DEVICE) for t in ck.get("proto_assign", [])] or None
    model = build_model_from_config(cfg, ctx["n_items"], ctx["n_items"],
                                    None if cfg.get("no_sbert") else sb, proto)
    model.load_state_dict(ck["state_dict"], strict=False)
    model.to(DEVICE).eval()
    model.pad_id = ctx["n_items"]
    with torch.no_grad():
        E = model.all_item_features().detach().cpu().numpy().astype(np.float64)

    deg = np.zeros(ctx["n_items"], dtype=np.int64)
    for (_, i, _, t) in ctx["pooled"]:
        if t <= ctx["t_in"]:
            deg[i] += 1
    M = knn_prior(E, sb.astype(np.float64), deg)
    Eimp = E.copy()
    Eimp[~ctx["warm"]] = M[~ctx["warm"]]
    tabs = {"stock": torch.from_numpy(E.astype(np.float32)).to(DEVICE),
            "imputed": torch.from_numpy(Eimp.astype(np.float32)).to(DEVICE)}
    text_S = None
    if args.family:
        import poc_eb_core as eb
        Mr = eb.fit_prior_mean(sb.astype(np.float64), E, deg, warm_min=20,
                               n_folds=5)
        ref = (deg >= 3) & (deg <= 10)
        tn = float(np.median(np.linalg.norm(E[ref], axis=1)))
        Mr = Mr * (tn / np.maximum(np.linalg.norm(Mr, axis=1, keepdims=True),
                                   1e-8))
        Er = E.copy()
        Er[~ctx["warm"]] = Mr[~ctx["warm"]]
        tabs["ridge"] = torch.from_numpy(Er.astype(np.float32)).to(DEVICE)
        tabs["fusion"] = tabs["stock"]          # scored as z-fusion in evaluate()
        Sn = sb.astype(np.float32)
        Sn = Sn / np.maximum(np.linalg.norm(Sn, axis=1, keepdims=True), 1e-8)
        text_S = torch.from_numpy(Sn).to(DEVICE)
    if args.fusion_sweep:
        for w in args.fusion_sweep.split(","):
            tabs[f"fusion_w{float(w):g}"] = tabs["stock"]
        if text_S is None:
            Sn = sb.astype(np.float32)
            Sn = Sn / np.maximum(np.linalg.norm(Sn, axis=1, keepdims=True), 1e-8)
            text_S = torch.from_numpy(Sn).to(DEVICE)
    res, pi, n_cold, n_tot = evaluate(model, tabs, ctx, cfg["max_seq_len"],
                                      offsets, text_S=text_S)
    print(f"  observed prevalence pi_t = {100*pi:.2f}%  "
          f"({n_cold:,}/{n_tot:,} events)", flush=True)
    print(f"\n{'arm':>9} {'delta':>6} {'overall':>9} {'cold':>9} {'warm':>9} {'coldAUC':>9}")
    for (n, d), v in res.items():
        print(f"{n:>9} {d:>6g} {v['overall']:>9.5f} {v['cold']:>9.5f} "
              f"{v['warm']:>9.5f} {v['cold_auc']:>9.5f}")
    b, i0 = res[("stock", 0.0)], res[("imputed", 0.0)]
    g = i0["cold"] - b["cold"]
    c = b["warm"] - i0["warm"]
    rep = {"run": os.path.basename(args.run_json), "category": cat,
           "pi_t": pi, "n_events": n_tot, "n_cold_events": n_cold,
           "n_cold_items": int((~ctx["warm"]).sum()),
           "results": {f"{n}@{d:g}": v for (n, d), v in res.items()},
           "E1_auc_gain": i0["cold_auc"] - b["cold_auc"],
           "E3_pstar": (abs(c) / (g + abs(c))) if (g + abs(c)) > 0 else None,
           "E4_overall_delta": i0["overall"] - b["overall"]}
    print(f"\nE1 within-pool AUC gain : {rep['E1_auc_gain']:+.5f}")
    print(f"E3 break-even p*        : {rep['E3_pstar'] if rep['E3_pstar'] is None else round(100*rep['E3_pstar'],2)}%"
          f"   (observed pi_t = {100*pi:.2f}%)")
    print(f"E4 PRIMARY overall delta: {rep['E4_overall_delta']:+.6f}  "
          f"=> imputation {'PAYS' if rep['E4_overall_delta'] > 0 else 'does NOT pay'} "
          f"at observed prevalence")
    dst = args.out or os.path.join(WORKTREE_RUN, "poc_out",
                                   os.path.basename(args.run_json).replace(
                                       ".json", ".temporal_eval.json"))
    json.dump(rep, open(dst, "w", encoding="utf-8"), indent=1)
    print(f"wrote {dst}")


if __name__ == "__main__":
    main()
