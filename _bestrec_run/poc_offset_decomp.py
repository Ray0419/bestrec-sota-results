# -*- coding: utf-8 -*-
"""RECONCILIATION EXPERIMENT: offset-degeneracy vs genuine cold learning.

Bridges two independently-derived agendas:
  * the parallel session's TIER_A_COLDSTART_RESEARCH_AGENDA RQ1 "target-conditioned
    offset degeneracy": adding a constant delta to every cold item's score leaves
    within-cold ordering EXACTLY invariant, yet monotonically inflates cold-target
    full-catalog metrics and deflates warm-target ones.
  * this worktree's RQ1' exchange rate: cold gain vs warm cost, break-even
    prevalence p* = |c|/(g+|c|), with p* ~ sqrt(N_cold).

Their proposition is the NULL MODEL for my law. Any intervention's cold-target
gain decomposes as
    g_total = g_offset  (nuisance: cross-pool score shift, learns nothing)
            + g_within  (genuine: reordering WITHIN the cold pool)
and only g_within is evidence of cold relevance learning.

This script measures, for each variant, on one frozen eval:
    cold-target NDCG@10 over the FULL catalog        (what benchmarks report)
    cold-target NDCG@10 ranked WITHIN the cold pool  (offset-invariant => genuine)
    warm-target NDCG@10 over the FULL catalog        (the externality)
plus the variant's realized mean cold-minus-warm score shift (its effective delta).

Variants: stock; pure score offsets (their intervention, learns nothing);
text-kNN row imputation (mine, demonstrably informative). The decisive test:
does a pure offset matched to imputation's cold gain reproduce imputation's
warm cost and within-cold ordering? If yes, imputation is a disguised offset.
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
from poc_posterior_eval import knn_prior            # noqa: E402

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


def evaluate_pools(model, table, cold_mask_t, offsets, user_seqs, eval_inters,
                   n_items, pad_id, max_seq_len, extra_history=None,
                   user_times=None, extra_times=None, batch_size=512, top_k=10):
    """One encode pass; for each offset delta report full-catalog and
    within-pool NDCG@10 for cold and warm targets separately."""
    model.eval()
    test_dict = {u: i for u, i, _, _ in eval_inters}
    users = sorted(test_dict.keys())
    extra = extra_history or {}
    xtimes = extra_times or {}
    use_times = getattr(model, "use_time_bias", False) and user_times is not None
    acc = {d: {"cold_full": [], "warm_full": [], "cold_within": [],
               "cold_auc": [], "cold_mrr": [], "cold_fauc": []} for d in offsets}
    shift = []                    # realized mean(cold score) - mean(warm score)
    with torch.no_grad():
        for s in range(0, len(users), batch_size):
            bu = users[s:s + batch_size]
            Bn = len(bu)
            input_ids = torch.full((Bn, max_seq_len), pad_id, dtype=torch.long,
                                   device=DEVICE)
            times_t = (torch.zeros((Bn, max_seq_len), dtype=torch.long,
                                   device=DEVICE) if use_times else None)
            hist, real_len = [], []
            for k, u in enumerate(bu):
                seq = list(user_seqs.get(u, []))
                if u in extra:
                    seq = seq + list(extra[u])
                hist.append(seq)
                tr = seq[-max_seq_len:]
                if tr:
                    input_ids[k, :len(tr)] = torch.tensor(tr, dtype=torch.long,
                                                          device=DEVICE)
                if use_times:
                    tms = list(user_times.get(u, []))
                    if u in xtimes:
                        tms = tms + list(xtimes[u])
                    tt = tms[-max_seq_len:]
                    if tt:
                        times_t[k, :len(tt)] = torch.tensor(
                            tt, dtype=torch.long, device=DEVICE)
                real_len.append(len(tr))
            hidden = model.encode(input_ids, times=times_t)
            last_pos = torch.tensor([max(0, rl - 1) for rl in real_len],
                                    device=DEVICE)
            last_h = hidden[torch.arange(Bn, device=DEVICE), last_pos, :]
            base = last_h @ table.T                       # (B, n_items)
            tgt = torch.tensor([test_dict[u] for u in bu], dtype=torch.long,
                               device=DEVICE)
            ar = torch.arange(Bn, device=DEVICE)
            tgt_cold = cold_mask_t[tgt]
            shift.append(float(base[:, cold_mask_t].mean()
                               - base[:, ~cold_mask_t].mean()))
            for k, h in enumerate(hist):
                if h:
                    base[k, torch.tensor(h, dtype=torch.long, device=DEVICE)] = \
                        -float("inf")
            for d in offsets:
                sc = base.clone()
                sc[:, cold_mask_t] += d
                ts = sc[ar, tgt]
                rank_full = (sc > ts.unsqueeze(1)).sum(dim=1)
                nd_full = torch.where(rank_full < top_k,
                                      1.0 / torch.log2(rank_full.float() + 2.0),
                                      torch.zeros_like(rank_full, dtype=torch.float))
                # within-cold rank: only cold competitors (offset cancels exactly)
                sc_cold = sc[:, cold_mask_t]
                rank_in = (sc_cold > ts.unsqueeze(1)).sum(dim=1)
                nd_in = torch.where(rank_in < top_k,
                                    1.0 / torch.log2(rank_in.float() + 2.0),
                                    torch.zeros_like(rank_in, dtype=torch.float))
                # PREREG_DOSE_RESPONSE_V1 §4: scale-free, cutoff-free, and exactly
                # offset-invariant -- replaces within-pool NDCG@10, which degenerates
                # on small pools (top-10 of 85 items is nearly free).
                n_pool = int(cold_mask_t.sum())
                auc_in = 1.0 - rank_in.float() / max(n_pool - 1, 1)
                mrr_in = 1.0 / (rank_in.float() + 1.0)
                acc[d]["cold_full"].extend(nd_full[tgt_cold].cpu().numpy().tolist())
                acc[d]["warm_full"].extend(nd_full[~tgt_cold].cpu().numpy().tolist())
                acc[d]["cold_within"].extend(nd_in[tgt_cold].cpu().numpy().tolist())
                acc[d]["cold_auc"].extend(auc_in[tgt_cold].cpu().numpy().tolist())
                acc[d]["cold_mrr"].extend(mrr_in[tgt_cold].cpu().numpy().tolist())
                # Q2 (rigor review): full-catalog AUC enables the rank-
                # displacement decomposition -- share of the target's total
                # upward movement that is past COLD competitors (genuine).
                fauc = 1.0 - rank_full.float() / max(n_items - 1, 1)
                acc[d]["cold_fauc"].extend(fauc[tgt_cold].cpu().numpy().tolist())
    out = {}
    for d, v in acc.items():
        out[d] = {"cold_full_ndcg10": float(np.mean(v["cold_full"])),
                  "warm_full_ndcg10": float(np.mean(v["warm_full"])),
                  "cold_within_ndcg10": float(np.mean(v["cold_within"])),
                  "cold_within_auc": float(np.mean(v["cold_auc"])),
                  "cold_within_mrr": float(np.mean(v["cold_mrr"])),
                  "cold_full_auc": float(np.mean(v["cold_fauc"])),
                  "n_cold": len(v["cold_full"]), "n_warm": len(v["warm_full"])}
    return out, float(np.mean(shift))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_json")
    ap.add_argument("--offsets", default="0,0.5,1,2,4,8")
    args = ap.parse_args()

    run = json.load(open(args.run_json, encoding="utf-8"))
    cfg = run["config"]
    category = cfg["category"]
    ckpt_path = str(args.run_json).replace(".json", ".best.pt")
    offsets = [float(x) for x in args.offsets.split(",")]

    torch.manual_seed(cfg["seed"])
    np.random.seed(cfg["seed"])
    tr = rsp.load_split_csv(rsp.SPLIT_DIR / f"{category}.train.csv")
    va = rsp.load_split_csv(rsp.SPLIT_DIR / f"{category}.valid.csv")
    te = rsp.load_split_csv(rsp.SPLIT_DIR / f"{category}.test.csv")
    train_inters, valid_inters, test_inters, user_list, item_list = rsp.reindex(
        tr, va, te)
    n_users, n_items = len(user_list), len(item_list)
    pad_id = n_items
    user_seqs = rsp.build_user_sequences(train_inters)
    user_times = (rsp.build_user_time_sequences(train_inters)
                  if cfg.get("time_bias") else None)
    val_extra, val_extra_times = {}, {}
    for u, i, _, t in valid_inters:
        val_extra.setdefault(u, []).append(i)
        val_extra_times.setdefault(u, []).append(t // 1000)

    deg = np.zeros(n_items, dtype=np.int64)
    for _, i, _, _ in train_inters:
        deg[i] += 1
    capset_path = str(args.run_json) + ".capset.json"
    if os.path.exists(capset_path):
        cs = json.load(open(capset_path, encoding="utf-8"))
        if cs.get("item_cap_multi"):
            # multi-dose: each group has its OWN cap. Applying the scalar
            # item_cap_k here would wrongly mark the k=16 group as cold.
            for gk, items in cs["groups"].items():
                if gk == "control" or not items:
                    continue
                idx = np.array(items, dtype=np.int64)
                deg[idx] = np.minimum(deg[idx], int(gk))
            print(f"  multi-dose capset applied: "
                  + ", ".join(f"k={g}:{len(v)}" for g, v in cs["groups"].items()))
        else:
            cap = np.array(cs["capped_items"], dtype=np.int64)
            deg[cap] = np.minimum(deg[cap], cs["item_cap_k"])
            print(f"  capset applied: {len(cap):,} items -> k<={cs['item_cap_k']}")
    cold = deg == 0
    print(f"  n_items={n_items:,}  cold items={int(cold.sum()):,} "
          f"({100*cold.mean():.2f}% of catalog)")

    enc = cfg.get("encoder_cache")
    sbert_npy = (rsp.EMB_CACHE_DIR / f"sbert_titles_{category}.npy"
                 if not enc else enc)
    sbert_emb = np.load(sbert_npy).astype(np.float32)[:n_items]
    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    proto = [t.to(DEVICE) for t in ckpt.get("proto_assign", [])] or None
    model = build_model_from_config(
        cfg, n_items, pad_id, None if cfg.get("no_sbert") else sbert_emb, proto)
    model.load_state_dict(ckpt["state_dict"], strict=False)
    model.to(DEVICE).eval()
    with torch.no_grad():
        E = model.all_item_features().detach().cpu().numpy().astype(np.float64)
    cold_t = torch.from_numpy(cold).to(DEVICE)

    rep = {"run": os.path.basename(args.run_json), "category": category,
           "n_cold_items": int(cold.sum()), "n_items": n_items, "arms": {}}

    print("\n=== ARM A: pure score offset on the STOCK table "
          "(their intervention; learns nothing) ===")
    Et = torch.from_numpy(E.astype(np.float32)).to(DEVICE)
    resA, shiftA = evaluate_pools(model, Et, cold_t, offsets, user_seqs,
                                  test_inters, n_items, pad_id,
                                  cfg["max_seq_len"], extra_history=val_extra,
                                  user_times=user_times,
                                  extra_times=val_extra_times)
    rep["arms"]["stock_plus_offset"] = {"score_shift_cold_minus_warm": shiftA,
                                        "by_offset": {str(k): v for k, v in resA.items()}}
    print(f"{'delta':>7} {'cold FULL':>11} {'cold WITHIN':>13} {'warm FULL':>11}")
    for d in offsets:
        r = resA[d]
        print(f"{d:>7.2f} {r['cold_full_ndcg10']:>11.5f} "
              f"{r['cold_within_ndcg10']:>13.5f} {r['warm_full_ndcg10']:>11.5f}")

    print("\n=== ARM B: text-kNN row imputation (mine; genuinely informative?) ===")
    M_knn = knn_prior(E, sbert_emb.astype(np.float64), deg)
    Eimp = E.copy()
    Eimp[cold] = M_knn[cold]
    Eit = torch.from_numpy(Eimp.astype(np.float32)).to(DEVICE)
    resB, shiftB = evaluate_pools(model, Eit, cold_t, offsets, user_seqs,
                                  test_inters, n_items, pad_id,
                                  cfg["max_seq_len"], extra_history=val_extra,
                                  user_times=user_times,
                                  extra_times=val_extra_times)
    rep["arms"]["knn_imputed_plus_offset"] = {
        "score_shift_cold_minus_warm": shiftB,
        "by_offset": {str(k): v for k, v in resB.items()}}
    print(f"{'delta':>7} {'cold FULL':>11} {'cold WITHIN':>13} {'warm FULL':>11}")
    for d in offsets:
        r = resB[d]
        print(f"{d:>7.2f} {r['cold_full_ndcg10']:>11.5f} "
              f"{r['cold_within_ndcg10']:>13.5f} {r['warm_full_ndcg10']:>11.5f}")

    # ---- the decisive comparison -------------------------------------------
    base = resA[0.0]
    imp = resB[0.0]
    g_total = imp["cold_full_ndcg10"] - base["cold_full_ndcg10"]
    c_total = imp["warm_full_ndcg10"] - base["warm_full_ndcg10"]
    within_gain = imp["cold_within_ndcg10"] - base["cold_within_ndcg10"]
    # matched offset: smallest delta whose cold_full gain >= imputation's
    matched = None
    for d in offsets:
        if d > 0 and resA[d]["cold_full_ndcg10"] >= imp["cold_full_ndcg10"]:
            matched = d
            break
    rep["decisive"] = {
        "imputation_cold_gain_full": g_total,
        "imputation_warm_cost_full": c_total,
        "imputation_within_cold_gain": within_gain,
        "stock_within_cold_ndcg": base["cold_within_ndcg10"],
        "imputed_within_cold_ndcg": imp["cold_within_ndcg10"],
        "matched_offset": matched}
    rep["decisive"]["stock_within_auc"] = base["cold_within_auc"]
    rep["decisive"]["imputed_within_auc"] = imp["cold_within_auc"]
    rep["decisive"]["within_auc_gain"] = imp["cold_within_auc"] - base["cold_within_auc"]
    rep["decisive"]["stock_within_mrr"] = base["cold_within_mrr"]
    rep["decisive"]["imputed_within_mrr"] = imp["cold_within_mrr"]
    rep["decisive"]["n_cold_pool"] = int(cold.sum())
    print("\n=== DECISIVE DECOMPOSITION ===")
    print(f"  cold pool size N                      : {int(cold.sum()):,}")
    print(f"  within-pool AUC (scale-free, offset-invariant): "
          f"{base['cold_within_auc']:.5f} -> {imp['cold_within_auc']:.5f} "
          f"(gain {imp['cold_within_auc']-base['cold_within_auc']:+.5f})")
    print(f"  within-pool MRR                       : "
          f"{base['cold_within_mrr']:.5f} -> {imp['cold_within_mrr']:.5f}")
    print(f"  imputation cold gain (FULL catalog)   : {g_total:+.5f}")
    print(f"  imputation warm cost (FULL catalog)   : {c_total:+.5f}")
    print(f"  imputation WITHIN-COLD gain           : {within_gain:+.5f} "
          f"({base['cold_within_ndcg10']:.5f} -> {imp['cold_within_ndcg10']:.5f})")
    if within_gain > 0:
        print("  => within-cold ordering IMPROVES: the intervention carries "
              "genuine cold relevance, NOT a pure pool offset.")
    else:
        print("  => within-cold ordering does NOT improve: the cold gain is "
              "explained by the pool offset alone (degeneracy).")
    if matched is not None:
        rm = resA[matched]
        print(f"  matched pure offset delta={matched:g} reproduces cold FULL "
              f"{rm['cold_full_ndcg10']:.5f} vs imputation {imp['cold_full_ndcg10']:.5f}")
        print(f"    its warm cost {rm['warm_full_ndcg10']-base['warm_full_ndcg10']:+.5f} "
              f"vs imputation {c_total:+.5f}")
        print(f"    its within-cold {rm['cold_within_ndcg10']:.5f} "
              f"(unchanged by construction) vs imputation {imp['cold_within_ndcg10']:.5f}")

    dst = os.path.join(WORKTREE_RUN, "poc_out",
                       os.path.basename(args.run_json).replace(".json",
                                                               ".offset_decomp.json"))
    json.dump(rep, open(dst, "w", encoding="utf-8"), indent=1)
    print(f"\nwrote {dst}")


if __name__ == "__main__":
    main()
