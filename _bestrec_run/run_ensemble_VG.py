#!/usr/bin/env python
"""c4 — empirical 2-model score-level ensemble on Video_Games (the one planned
but never-executed direction; previously only *analytically* ruled out at a
~0.066 ceiling).

Trains N members of the EXACT winning HSTU stack (faithful-HSTU + TAPE-512 +
time-bias + text-sim-bias + pos-rab + chunked-full-softmax, dropout 0.5, 40ep,
warmup_cosine) that differ ONLY in their frozen text encoder cache, keeps each
member's best-by-val weights in memory, then runs ONE full-catalog leave-last-out
eval that fuses the members' item scores.

Why fusion needs care: the winning recipe scores with raw DOT PRODUCT
(cosine_scoring=False), so different members' logits live on different scales —
a naive mean would let the larger-norm model dominate. We therefore report three
scale-aware fusions and each member's solo score in the same pass:
  * mean   — plain average of raw logits (scale-naive baseline)
  * zmean  — per-query z-score each member over the item axis, then average
             (scale-invariant; the principled choice for dot-product members)
  * rank   — per-query rank-average (most robust to scale, ignores magnitude)

Members are index-aligned: both caches were generated from a byte-identical
asin2idx ordering (verified in O1), and both align to the SAME item_list from
reindex(), so item i is the same product across members and per-item logit
fusion is valid. No leakage: each member only ever sees training history.

Reuses the canonical SASRecSBERT / train_one_epoch / data helpers verbatim, so
each member is bit-for-bit the winning stack apart from its text cache + seed.
"""
import argparse
import copy
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader

# Import the canonical building blocks so members are identical to headline runs.
import run_sasrec_sbert as R
from run_sasrec_sbert import (
    SASRecSBERT, SASRecDataset, collate_batch, evaluate,
    load_split_csv, reindex, build_user_sequences, build_user_time_sequences,
    train_one_epoch, torch_kmeans,
    SPLIT_DIR, EMB_CACHE_DIR, DEVICE, N_TIME_BUCKETS,
)

CATEGORY = "Video_Games"

# Winning recipe (read verbatim from results_BEST_VG_seed*.json / results_N1_blair_VG.json).
RECIPE = dict(
    epochs=40, batch_size=256, max_seq_len=50, d_model=64, n_layers=4, n_heads=2,
    dropout=0.5, lr=1e-3, item_chunk=32768, proto_tau=0.05, proto_k=512,
)


def build_proto_assign(sbert_emb, n_items, seed, K, tau):
    """TAPE frozen soft-assignments (verbatim from main())."""
    x = torch.from_numpy(sbert_emb).to(DEVICE)
    x = F.normalize(x, dim=1)
    C = torch_kmeans(x, K, iters=25, seed=seed)
    A = torch.softmax((x @ C.T) / tau, dim=1)
    A_pad = torch.zeros((n_items + 1, K), dtype=torch.float32, device=DEVICE)
    A_pad[:n_items] = A
    eff = float((A.max(dim=1).values).mean())
    print(f"    TAPE K={K} mean max-assignment = {eff:.3f}")
    return [A_pad]


def train_member(name, cache_path, seed, shared):
    """Train one winning-stack member with its own text cache. Returns the model
    restored to its best-by-val weights (kept in memory, never written to disk)."""
    n_items = shared["n_items"]
    pad_id = shared["pad_id"]
    user_seqs = shared["user_seqs"]
    user_times = shared["user_times"]
    valid_inters = shared["valid_inters"]

    print(f"\n=== member '{name}': cache={cache_path} seed={seed} ===")
    sbert_emb = np.load(cache_path).astype(np.float32)
    if sbert_emb.shape[0] != n_items:
        print(f"    WARN cache has {sbert_emb.shape[0]} rows, split has {n_items}; aligning by index")
        sbert_emb = sbert_emb[:n_items]
    print(f"    text dim = {sbert_emb.shape[1]}")

    torch.manual_seed(seed)
    np.random.seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

    proto_assign = build_proto_assign(sbert_emb, n_items, seed,
                                       RECIPE["proto_k"], RECIPE["proto_tau"])

    model = SASRecSBERT(
        n_items=n_items, pad_id=pad_id, max_seq_len=RECIPE["max_seq_len"],
        d_model=RECIPE["d_model"], n_layers=RECIPE["n_layers"],
        n_heads=RECIPE["n_heads"], dropout=RECIPE["dropout"],
        sbert_emb=sbert_emb, sbert_only=False, mlp_adaptor=False,
        mlp_hidden=300, mlp_dropout=0.2,
        time_bias=True, text_sim_bias=True, proto_assign=proto_assign,
        encoder="hstu", pos_rab=True,
        time_decay_kernel=False, time_decay_bases=8, n_experts=0,
    ).to(DEVICE)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"    params: {n_params:,}")

    dataset = SASRecDataset(user_seqs, RECIPE["max_seq_len"], n_items, pad_id,
                            augment_factor=1, user_times=user_times)
    loader = DataLoader(dataset, batch_size=RECIPE["batch_size"], shuffle=True,
                        num_workers=0, collate_fn=collate_batch, drop_last=False)

    opt = torch.optim.Adam(model.parameters(), lr=RECIPE["lr"], weight_decay=1e-5)
    total_steps = RECIPE["epochs"] * len(loader)
    warmup_steps = max(1, int(0.05 * total_steps))
    warmup = torch.optim.lr_scheduler.LinearLR(opt, start_factor=1e-3, end_factor=1.0,
                                               total_iters=warmup_steps)
    cosine = torch.optim.lr_scheduler.CosineAnnealingLR(
        opt, T_max=max(1, total_steps - warmup_steps), eta_min=0)
    scheduler = torch.optim.lr_scheduler.SequentialLR(
        opt, schedulers=[warmup, cosine], milestones=[warmup_steps])

    best_val, best_state, best_epoch = -1.0, None, 0
    for epoch in range(1, RECIPE["epochs"] + 1):
        t0 = time.time()
        loss, _ = train_one_epoch(
            model, loader, opt, pad_id, DEVICE,
            sampled_negs=0, in_batch_negs=False, chunked_full_softmax=True,
            item_chunk=RECIPE["item_chunk"], scheduler=scheduler,
            cosine=False, temp=0.05, text_distill_weight=0.0)
        dt = time.time() - t0
        if epoch % 10 == 0 or epoch == RECIPE["epochs"]:
            # Subsampled val just to PICK the best epoch (fast). Final headline
            # eval is full-catalog in ensemble_eval().
            vm = evaluate(model, user_seqs, valid_inters, n_items, pad_id,
                          RECIPE["max_seq_len"], DEVICE, subsample_users=10000,
                          subsample_seed=0, user_times=user_times, cosine=False)
            print(f"    epoch {epoch:>3d} loss={loss:.4f} val(10k)NDCG={vm['NDCG@10']:.4f} ({dt:.1f}s)")
            if vm["NDCG@10"] > best_val:
                best_val, best_epoch = vm["NDCG@10"], epoch
                best_state = copy.deepcopy(model.state_dict())
        else:
            print(f"    epoch {epoch:>3d} loss={loss:.4f} ({dt:.1f}s)")

    print(f"    best val(10k) NDCG@10={best_val:.4f} @epoch {best_epoch}")
    model.load_state_dict(best_state)
    model.eval()
    return model, {"name": name, "cache": str(cache_path), "seed": seed,
                   "best_val_subsample_NDCG10": best_val, "best_epoch": best_epoch,
                   "text_dim": int(sbert_emb.shape[1]), "n_params": n_params}


@torch.no_grad()
def ensemble_eval(members, shared, top_k=10, batch_size=512, max_users=0):
    """One full-catalog leave-last-out eval pass. For every test user, compute
    each member's logits over all items, then rank the target under each member
    solo AND under three fusions. Returns dict of metric dicts keyed by variant."""
    user_seqs = shared["user_seqs"]
    test_inters = shared["test_inters"]
    valid_inters = shared["valid_inters"]
    n_items = shared["n_items"]
    pad_id = shared["pad_id"]
    user_times = shared["user_times"]
    L = RECIPE["max_seq_len"]

    # test eval includes the val item in the input history (matches main()).
    valid_dict = {u: i for u, i, _, _ in valid_inters}
    extra = {u: [i] for u, i in valid_dict.items()}
    extra_times = {u: [t // 1000] for u, _, _, t in valid_inters}

    test_dict = {u: i for u, i, _, _ in test_inters}
    users = sorted(test_dict.keys())
    if max_users and max_users < len(users):
        users = users[:max_users]
        print(f"  [override] capping ensemble eval to {max_users} users (SMOKE)")
    n_eval = len(users)

    # Precompute each member's (n_items, d) item table once.
    item_tabs = [m.all_item_features() for m, _ in members]  # raw (dot-product recipe)
    M = len(members)
    variants = [f"solo:{meta['name']}" for _, meta in members] + ["mean", "zmean", "rank"]
    acc = {v: {"ndcg": [], "hr": [], "rr": []} for v in variants}
    # diversity: collect per-user target rank under each member to measure error corr.
    member_ranks = [[] for _ in range(M)]

    print(f"\n=== ensemble eval: {n_eval:,} users, {M} members, full catalog n_items={n_items:,} ===")
    t0 = time.time()
    for s in range(0, n_eval, batch_size):
        bu = users[s:s + batch_size]
        B = len(bu)
        input_ids = torch.full((B, L), pad_id, dtype=torch.long, device=DEVICE)
        times_t = torch.zeros((B, L), dtype=torch.long, device=DEVICE)
        seqs, reals = [], []
        for k, u in enumerate(bu):
            seq = list(user_seqs.get(u, [])) + list(extra.get(u, []))
            tms = list(user_times.get(u, [])) + list(extra_times.get(u, []))
            seq, tms = seq[-L:], tms[-L:]
            seqs.append(seq)
            if seq:
                input_ids[k, :len(seq)] = torch.tensor(seq, dtype=torch.long, device=DEVICE)
                times_t[k, :len(tms)] = torch.tensor(tms, dtype=torch.long, device=DEVICE)
            reals.append(len(seq))
        last_pos = torch.tensor([max(0, r - 1) for r in reals], device=DEVICE)
        ar = torch.arange(B, device=DEVICE)

        # per-member logits (B, n_items)
        logits = []
        for (m, _), tab in zip(members, item_tabs):
            h = m.encode(input_ids, times=times_t)
            lh = h[ar, last_pos, :]
            lg = lh @ tab.T
            logits.append(lg)

        # mask history per member BEFORE fusion stats? We z-score over ALL items
        # (incl. history) then mask, matching how a deployed score would be
        # normalized; masked entries become -inf and never rank.
        masks = []
        for k, seq in enumerate(seqs):
            if seq:
                masks.append((k, torch.tensor(seq, device=DEVICE)))

        # ---- fusion tensors ----
        stack = torch.stack(logits, dim=0)            # (M, B, n_items)
        fused = {}
        fused["mean"] = stack.mean(dim=0)
        mu = stack.mean(dim=2, keepdim=True)
        sd = stack.std(dim=2, keepdim=True) + 1e-8
        fused["zmean"] = ((stack - mu) / sd).mean(dim=0)
        # rank fusion: per member, ascending rank (higher logit -> higher rank score).
        # Vectorized inverse-permutation via scatter_: ranks[m,b,order[m,b,j]] = j.
        order = stack.argsort(dim=2)                   # ascending, (M,B,n_items)
        ranks = torch.empty_like(stack)
        src = (torch.arange(n_items, device=DEVICE, dtype=stack.dtype)
               .view(1, 1, -1).expand(M, B, n_items).contiguous())
        ranks.scatter_(2, order, src)
        fused["rank"] = ranks.mean(dim=0)

        # ---- score every variant ----
        def rank_target(final):
            # apply -inf history mask, return target rank0 per user
            for k, idx in masks:
                final[k, idx] = -float("inf")
            out = []
            for k, u in enumerate(bu):
                if reals[k] == 0:
                    out.append(None); continue
                tgt = test_dict[u]
                ts = final[k, tgt].item()
                out.append(int((final[k] > ts).sum().item()))
            return out

        for mi, (_, meta) in enumerate(members):
            r0 = rank_target(logits[mi].clone())
            for k, rk in enumerate(r0):
                if rk is None:
                    continue
                member_ranks[mi].append(rk)
                v = f"solo:{meta['name']}"
                acc[v]["ndcg"].append(1.0 / math.log2(rk + 2) if rk < top_k else 0.0)
                acc[v]["hr"].append(1.0 if rk < top_k else 0.0)
                acc[v]["rr"].append(1.0 / (rk + 1))
        for fv in ("mean", "zmean", "rank"):
            r0 = rank_target(fused[fv].clone())
            for rk in r0:
                if rk is None:
                    continue
                acc[fv]["ndcg"].append(1.0 / math.log2(rk + 2) if rk < top_k else 0.0)
                acc[fv]["hr"].append(1.0 if rk < top_k else 0.0)
                acc[fv]["rr"].append(1.0 / (rk + 1))
        if (s // batch_size) % 10 == 0:
            print(f"    [{s + B:,}/{n_eval:,} elapsed {time.time()-t0:.1f}s]")

    print(f"  eval done in {time.time()-t0:.1f}s")
    res = {}
    for v in variants:
        res[v] = {"NDCG@10": float(np.mean(acc[v]["ndcg"])),
                  "HR@10": float(np.mean(acc[v]["hr"])),
                  "MRR": float(np.mean(acc[v]["rr"])),
                  "n_eval": len(acc[v]["ndcg"])}
    # error-correlation diagnostic (Spearman of target ranks across the 2 members)
    if M == 2 and len(member_ranks[0]) == len(member_ranks[1]) and len(member_ranks[0]) > 1:
        a = np.array(member_ranks[0], dtype=float)
        b = np.array(member_ranks[1], dtype=float)
        ar_ = np.argsort(np.argsort(a)); br_ = np.argsort(np.argsort(b))
        corr = float(np.corrcoef(ar_, br_)[0, 1])
        res["_diag"] = {"member_rank_spearman": corr,
                        "note": "lower corr = more diverse errors = more ensemble headroom"}
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--members", default="sbert,blair",
                    help="Comma list from {sbert,blair,dual}. Default 2-model sbert,blair.")
    ap.add_argument("--out", default=str(Path(__file__).parent / "results_c4_ensemble_VG.json"))
    ap.add_argument("--epochs", type=int, default=0, help="Override RECIPE epochs (0=use 40). For smoke tests.")
    ap.add_argument("--max-eval-users", type=int, default=0,
                    help="Cap ensemble-eval users (0=full catalog, all users). For smoke tests.")
    args = ap.parse_args()
    if args.epochs > 0:
        RECIPE["epochs"] = args.epochs
        print(f"  [override] epochs={args.epochs}")

    cache_map = {
        "sbert": (EMB_CACHE_DIR / f"sbert_titles_{CATEGORY}.npy", 20260609),
        "blair": (EMB_CACHE_DIR / f"blair_titles_{CATEGORY}.npy", 20260608),
        "dual":  (EMB_CACHE_DIR / f"dualtext_sbert_blair_{CATEGORY}.npy", 20260608),
    }
    chosen = [m.strip() for m in args.members.split(",") if m.strip()]
    for m in chosen:
        if m not in cache_map:
            print(f"ERROR unknown member '{m}'"); return 2
        if not Path(cache_map[m][0]).exists():
            print(f"ERROR cache missing for '{m}': {cache_map[m][0]}"); return 2

    # ---- shared data setup (verbatim from main()) ----
    print(f"=== {CATEGORY}: load splits ===")
    tr = load_split_csv(SPLIT_DIR / f"{CATEGORY}.train.csv")
    va = load_split_csv(SPLIT_DIR / f"{CATEGORY}.valid.csv")
    te = load_split_csv(SPLIT_DIR / f"{CATEGORY}.test.csv")
    train_inters, valid_inters, test_inters, user_list, item_list = reindex(tr, va, te)
    n_items = len(item_list)
    shared = dict(
        n_items=n_items, pad_id=n_items,
        user_seqs=build_user_sequences(train_inters),
        user_times=build_user_time_sequences(train_inters),
        valid_inters=valid_inters, test_inters=test_inters,
    )
    print(f"  n_users={len(user_list):,} n_items={n_items:,}")

    members = []
    member_metas = []
    for m in chosen:
        cache, seed = cache_map[m]
        model, meta = train_member(m, cache, seed, shared)
        members.append((model, meta))
        member_metas.append(meta)

    res = ensemble_eval(members, shared, max_users=args.max_eval_users)

    # ---- report ----
    print("\n=== c4 ENSEMBLE RESULTS (full-catalog LLOO test NDCG@10) ===")
    solo = {meta["name"]: res[f"solo:{meta['name']}"]["NDCG@10"] for _, meta in members}
    best_solo = max(solo.values())
    for k, v in solo.items():
        print(f"  solo {k:>6s}: {v:.4f}")
    for fv in ("mean", "zmean", "rank"):
        d = res[fv]["NDCG@10"]
        tag = "  <-- best fusion" if d == max(res['mean']['NDCG@10'], res['zmean']['NDCG@10'], res['rank']['NDCG@10']) else ""
        print(f"  fuse {fv:>6s}: {d:.4f}  HR@10={res[fv]['HR@10']:.4f}{tag}")
    best_fuse = max(res["mean"]["NDCG@10"], res["zmean"]["NDCG@10"], res["rank"]["NDCG@10"])
    if "_diag" in res:
        print(f"  member-rank Spearman corr = {res['_diag']['member_rank_spearman']:.3f}")
    print(f"\n  best solo   = {best_solo:.4f}")
    print(f"  best fusion = {best_fuse:.4f}  (lift over best solo = {best_fuse-best_solo:+.4f})")
    print(f"  vs single-seed campaign best 0.0639 : {best_fuse-0.0639:+.4f}")
    print(f"  vs published HSTU-BLaIR mandate 0.0760: {best_fuse-0.0760:+.4f}")

    out = {
        "experiment": "c4_2model_score_ensemble",
        "category": CATEGORY, "recipe": RECIPE, "members": member_metas,
        "results": res, "best_solo_NDCG10": best_solo, "best_fusion_NDCG10": best_fuse,
        "campaign_single_best_0639": 0.0639, "mandate_0760": 0.0760,
    }
    Path(args.out).write_text(json.dumps(out, indent=2))
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
