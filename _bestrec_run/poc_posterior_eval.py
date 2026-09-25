# -*- coding: utf-8 -*-
"""H4 training-free posterior-map evaluation (RESEARCH_QUESTIONS_COLDSTART RQ1).

Loads a trained checkpoint, rebuilds the model (fuse_ease_eval pattern), and
re-scores the frozen eval with modified ITEM SCORING TABLES:

  stock   : model.all_item_features() unchanged (harness validation: must
            reproduce the run's recorded best_test NDCG@10)
  k0fix   : only rows with train degree k=0 replaced by the norm-calibrated
            cross-fitted text-prior prediction m(x) (zero parameters)
  eb(c)   : alpha_i = k_i/(k_i+c); row = alpha*E + (1-alpha)*m_cal(x);
            k=0 rows as k0fix. c selected on VALIDATION only; test reported
            once at the selected c (other c values recorded as exploratory).

Input-side (sequence-encoding) embeddings stay stock: the intervention is on
the scoring table only. Per-user NDCG@10 sliced by target-item train degree.

Usage: poc_posterior_eval.py <run.json> [--ckpt p] [--c-grid 0.5,1,2,4,8,16]
       [--out p]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import torch

WORKTREE_RUN = os.path.dirname(os.path.abspath(__file__))
MAIN_RUN = r"C:\Users\rayxc\Documents\R\_bestrec_run"
sys.path.insert(0, WORKTREE_RUN)
sys.path.insert(0, MAIN_RUN)
import poc_eb_core as eb            # noqa: E402  (worktree)
import run_sasrec_sbert as rsp      # noqa: E402  (main repo)
from fuse_ease_eval import build_model_from_config  # noqa: E402 (main repo)

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
DEG_EDGES = [(0, 0), (1, 2), (3, 5), (6, 10), (11, 20), (21, 50), (51, 150),
             (151, 500), (501, 10 ** 9)]


def bucket_of(k):
    for b, (lo, hi) in enumerate(DEG_EDGES):
        if lo <= k <= hi:
            return b
    return None


def eval_tables(model, tables, user_seqs, eval_inters, n_items, pad_id,
                max_seq_len, extra_history=None, user_times=None,
                extra_times=None, batch_size=512, top_k=10):
    """One encode pass, score every table in `tables` (dict name->tensor).

    Returns {name: {"ndcg":..,"hr":..}}, and per-user ndcg arrays per name
    aligned with the sorted user order, plus target ids.
    """
    model.eval()
    test_dict = {u: i for u, i, _, _ in eval_inters}
    users = sorted(test_dict.keys())
    n_eval = len(users)
    extra = extra_history or {}
    xtimes = extra_times or {}
    use_times = getattr(model, "use_time_bias", False) and user_times is not None
    agg = {n: {"ndcg": 0.0, "hr": 0.0, "hr100": 0.0} for n in tables}
    per_user = {n: [] for n in tables}
    per_rank = {n: [] for n in tables}
    tgts_all = []
    t0 = time.time()
    with torch.no_grad():
        for s in range(0, n_eval, batch_size):
            batch_users = users[s:s + batch_size]
            Bn = len(batch_users)
            input_ids = torch.full((Bn, max_seq_len), pad_id, dtype=torch.long,
                                   device=DEVICE)
            times_t = (torch.zeros((Bn, max_seq_len), dtype=torch.long,
                                   device=DEVICE) if use_times else None)
            hist = []
            real_len = []
            for k, u in enumerate(batch_users):
                seq = list(user_seqs.get(u, []))
                if u in extra:
                    seq = seq + list(extra[u])
                hist.append(seq)
                trunc = seq[-max_seq_len:]
                if trunc:
                    input_ids[k, :len(trunc)] = torch.tensor(
                        trunc, dtype=torch.long, device=DEVICE)
                if use_times:
                    tms = list(user_times.get(u, []))
                    if u in xtimes:
                        tms = tms + list(xtimes[u])
                    tt = tms[-max_seq_len:]
                    if tt:
                        times_t[k, :len(tt)] = torch.tensor(
                            tt, dtype=torch.long, device=DEVICE)
                real_len.append(len(trunc))
            hidden = model.encode(input_ids, times=times_t)
            last_pos = torch.tensor([max(0, rl - 1) for rl in real_len],
                                    device=DEVICE)
            last_h = hidden[torch.arange(Bn, device=DEVICE), last_pos, :]
            tgt = torch.tensor([test_dict[u] for u in batch_users],
                               dtype=torch.long, device=DEVICE)
            tgts_all.extend(tgt.cpu().numpy().tolist())
            ar = torch.arange(Bn, device=DEVICE)
            mask_idx = [(k, torch.tensor(h, dtype=torch.long, device=DEVICE))
                        for k, h in enumerate(hist) if h]
            for name, tab in tables.items():
                scores = last_h @ tab.T
                for k, idx in mask_idx:
                    scores[k, idx] = -float("inf")
                ts = scores[ar, tgt]
                rank0 = (scores > ts.unsqueeze(1)).sum(dim=1)
                hit = rank0 < top_k
                nd = torch.where(hit, 1.0 / torch.log2(rank0.float() + 2.0),
                                 torch.zeros_like(rank0, dtype=torch.float))
                agg[name]["ndcg"] += float(nd.sum())
                agg[name]["hr"] += float(hit.sum())
                agg[name]["hr100"] += float((rank0 < 100).sum())
                per_user[name].extend(nd.cpu().numpy().tolist())
                per_rank[name].extend(rank0.cpu().numpy().tolist())
            if (s // batch_size) % 40 == 0:
                print(f"    [{s + Bn:,}/{n_eval:,}  {time.time()-t0:.0f}s]",
                      flush=True)
    for n in agg:
        for m in agg[n]:
            agg[n][m] /= n_eval
    return agg, per_user, per_rank, np.array(tgts_all), users


def knn_prior(E, S, deg, warm_min=21, topk=20, temp=0.07):
    """Text-kNN imputation in ROW space (cold_synth mechanism, post-hoc):
    m_i = sum_j w_ij E_j over the top-k warm text-neighbors of i, softmax(cos/temp),
    norm-restored to sum_j w_ij ||E_j|| (the tau_i trick)."""
    Sg = torch.from_numpy((S / np.maximum(np.linalg.norm(S, axis=1, keepdims=True),
                                          1e-8)).astype(np.float32)).to(DEVICE)
    Eg = torch.from_numpy(E.astype(np.float32)).to(DEVICE)
    warm = torch.from_numpy((deg >= warm_min)).to(DEVICE)
    warm_idx = torch.nonzero(warm, as_tuple=False).squeeze(1)
    Sw = Sg[warm_idx]
    M = torch.empty_like(Eg)
    n = Eg.shape[0]
    for s in range(0, n, 2048):
        cs = Sg[s:s + 2048] @ Sw.T                       # (b, n_warm)
        # drop self-matches (cos==1 for warm rows in their own neighbor set)
        vals, idx = torch.topk(cs, topk + 1, dim=1)
        keep = vals < 0.99999
        keep[:, -1] |= ~keep[:, :-1].any(dim=1)
        w = torch.where(keep, vals / temp, torch.full_like(vals, -1e30))
        w = torch.softmax(w, dim=1)
        nbr = warm_idx[idx]                              # (b, topk+1)
        rows = (Eg[nbr] * w.unsqueeze(-1)).sum(dim=1)
        tgt_norm = (Eg[nbr].norm(dim=-1) * w).sum(dim=1, keepdim=True)
        rows = rows * (tgt_norm / rows.norm(dim=-1, keepdim=True).clamp_min(1e-8))
        M[s:s + 2048] = rows
    return M.cpu().numpy().astype(np.float64)


def build_dev_tables(E, M_knn, deg, t_grid=(0.7, 1.0, 1.4), h_bar=None,
                     orth_t_grid=(1.0, 1.4, 2.0)):
    """Hierarchical imputation: k0 row = mu_low + t * (knn_row - mu_warm).

    Keeps the neighborhood-specific deviation, swaps the warm popularity
    baseline for a low-degree baseline — targets the specificity-vs-spam
    trade-off seen in the k0knn_s sweep. If h_bar (mean user state) is given,
    also emits k0orth_t*: deviation projected orthogonal to h_bar — removing
    the component that scores uniformly for everyone (the spam axis)."""
    mu_warm = E[deg >= 21].mean(axis=0)
    mu_low = E[(deg >= 1) & (deg <= 5)].mean(axis=0)
    dev = M_knn - mu_warm[None, :]
    out = {}
    z = deg == 0
    for t in t_grid:
        T = E.copy()
        T[z] = mu_low[None, :] + t * dev[z]
        out[f"k0dev_t{t:g}"] = torch.from_numpy(T.astype(np.float32)).to(DEVICE)
    if h_bar is not None:
        h = h_bar / max(np.linalg.norm(h_bar), 1e-8)
        dev_o = dev - np.outer(dev @ h, h)
        for t in orth_t_grid:
            T = E.copy()
            T[z] = mu_low[None, :] + t * dev_o[z]
            out[f"k0orth_t{t:g}"] = torch.from_numpy(
                T.astype(np.float32)).to(DEVICE)
    return out


def sample_user_state(model, user_seqs, eval_inters, pad_id, max_seq_len,
                      user_times=None, n_sample=4096, batch_size=512):
    """Mean last-position hidden state over a sample of eval users."""
    users = sorted({u for u, _, _, _ in eval_inters})[:n_sample]
    use_times = getattr(model, "use_time_bias", False) and user_times is not None
    acc = None
    cnt = 0
    with torch.no_grad():
        for s in range(0, len(users), batch_size):
            batch_users = users[s:s + batch_size]
            Bn = len(batch_users)
            input_ids = torch.full((Bn, max_seq_len), pad_id, dtype=torch.long,
                                   device=DEVICE)
            times_t = (torch.zeros((Bn, max_seq_len), dtype=torch.long,
                                   device=DEVICE) if use_times else None)
            real_len = []
            for k, u in enumerate(batch_users):
                seq = list(user_seqs.get(u, []))[-max_seq_len:]
                if seq:
                    input_ids[k, :len(seq)] = torch.tensor(
                        seq, dtype=torch.long, device=DEVICE)
                if use_times:
                    tms = list(user_times.get(u, []))[-max_seq_len:]
                    if tms:
                        times_t[k, :len(tms)] = torch.tensor(
                            tms, dtype=torch.long, device=DEVICE)
                real_len.append(len(seq))
            hidden = model.encode(input_ids, times=times_t)
            last_pos = torch.tensor([max(0, rl - 1) for rl in real_len],
                                    device=DEVICE)
            last_h = hidden[torch.arange(Bn, device=DEVICE), last_pos, :]
            acc = last_h.sum(dim=0) if acc is None else acc + last_h.sum(dim=0)
            cnt += Bn
    return (acc / cnt).cpu().numpy().astype(np.float64)


def build_tables(E, M_cal, M_knn, deg, c_grid, s_grid=(0.4, 0.55, 0.7, 0.85, 1.0)):
    """dict of scoring tables per variant (float32 tensors on DEVICE).

    - ebrdg_c*: alpha(k)-mix toward the ridge prior (k0 rows = ridge prior)
    - k0knn_s*: ONLY k=0 rows replaced by s * M_knn — the imputation-shrinkage
      sweep (s<1 = EB-style damping of the imputed row's own uncertainty,
      controlling the loud-generic-row competitor-set cost)
    """
    Et = torch.from_numpy(E.astype(np.float32)).to(DEVICE)
    k = torch.from_numpy(deg.astype(np.float32)).to(DEVICE)
    z = (k == 0).unsqueeze(1)
    tables = {"stock": Et}
    Mr = torch.from_numpy(M_cal.astype(np.float32)).to(DEVICE)
    tables["k0fixrdg"] = torch.where(z, Mr, Et)
    for c in c_grid:
        a = (k / (k + c)).unsqueeze(1)
        tables[f"ebrdg_c{c:g}"] = torch.where(z, Mr, a * Et + (1.0 - a) * Mr)
    Mk = torch.from_numpy(M_knn.astype(np.float32)).to(DEVICE)
    for s in s_grid:
        tables[f"k0knn_s{s:g}"] = torch.where(z, s * Mk, Et)
    return tables


def degree_slices(per_user_nd, per_user_rank, tgts, deg):
    out = {}
    nd = np.asarray(per_user_nd)
    rk = np.asarray(per_user_rank)
    b_of = np.array([bucket_of(int(deg[t])) if t < len(deg) else -1
                     for t in tgts])
    for b, (lo, hi) in enumerate(DEG_EDGES):
        m = b_of == b
        if m.sum():
            out[f"k{lo}-{hi}"] = {
                "n": int(m.sum()), "ndcg10": float(nd[m].mean()),
                "hr10": float((rk[m] < 10).mean()),
                "hr100": float((rk[m] < 100).mean()),
                "median_rank": int(np.median(rk[m]))}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_json")
    ap.add_argument("--ckpt", default=None)
    ap.add_argument("--c-grid", default="1,2,4")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    run = json.load(open(args.run_json, encoding="utf-8"))
    cfg = run["config"]
    category = cfg["category"]
    ckpt_path = Path(args.ckpt) if args.ckpt else \
        Path(args.run_json).with_suffix(".best.pt")
    c_grid = [float(x) for x in args.c_grid.split(",")]
    print(f"=== posterior-map eval: {category}  ckpt={ckpt_path.name} ===",
          flush=True)

    torch.manual_seed(cfg["seed"])
    np.random.seed(cfg["seed"])
    train_rows = rsp.load_split_csv(rsp.SPLIT_DIR / f"{category}.train.csv")
    valid_rows = rsp.load_split_csv(rsp.SPLIT_DIR / f"{category}.valid.csv")
    test_rows = rsp.load_split_csv(rsp.SPLIT_DIR / f"{category}.test.csv")
    train_inters, valid_inters, test_inters, user_list, item_list = rsp.reindex(
        train_rows, valid_rows, test_rows)
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
    # K-DIAL runs: the model's EFFECTIVE train degree for capped items is the
    # cap, not the full-split degree. Apply the capset so "cold" means what the
    # model actually saw.
    capset_path = str(args.run_json) + ".capset.json"
    if os.path.exists(capset_path):
        cs = json.load(open(capset_path, encoding="utf-8"))
        capped = np.array(cs["capped_items"], dtype=np.int64)
        deg[capped] = np.minimum(deg[capped], cs["item_cap_k"])
        print(f"  K-DIAL capset applied: {len(capped):,} items capped to "
              f"k<={cs['item_cap_k']}", flush=True)
    print(f"  n_users={n_users:,} n_items={n_items:,} deg0={(deg == 0).sum()}",
          flush=True)

    enc_cache = cfg.get("encoder_cache")
    sbert_npy = Path(enc_cache) if enc_cache else \
        rsp.EMB_CACHE_DIR / f"sbert_titles_{category}.npy"
    sbert_emb = np.load(sbert_npy).astype(np.float32)[:n_items]

    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    proto_assign = [t.to(DEVICE) for t in ckpt.get("proto_assign", [])] or None
    model_sbert = None if cfg.get("no_sbert") else sbert_emb
    model = build_model_from_config(cfg, n_items, pad_id, model_sbert,
                                    proto_assign)
    missing, unexpected = model.load_state_dict(ckpt["state_dict"], strict=False)
    unexpected = [k for k in unexpected if not k.startswith("proto_assign")]
    missing = [k for k in missing
               if not (k.startswith("sbert_table") or k.startswith("proto_assign")
                       or k in ("time_boundaries",))]
    if missing or unexpected:
        print(f"  WARN state_dict mismatch: missing={missing} "
              f"unexpected={unexpected}", flush=True)
    model.to(DEVICE).eval()
    print(f"  ckpt epoch {ckpt['epoch']} (val NDCG@10 {ckpt['val_NDCG10']:.5f}) "
          f"recorded best_test NDCG@10="
          f"{run.get('best_test', {}).get('NDCG@10')}", flush=True)

    with torch.no_grad():
        E = model.all_item_features().detach().cpu().numpy().astype(np.float64)

    S = sbert_emb.astype(np.float64)
    M = eb.fit_prior_mean(S, E, deg, warm_min=20, n_folds=5)
    # norm calibration of prior rows: match the modest-warm scale
    ref = (deg >= 3) & (deg <= 10)
    target_norm = float(np.median(np.linalg.norm(E[ref], axis=1)))
    Mn = np.linalg.norm(M, axis=1, keepdims=True)
    M_cal = M * (target_norm / np.maximum(Mn, 1e-8))
    print(f"  ridge prior: target_norm={target_norm:.4f}  "
          f"median||M||={float(np.median(Mn)):.4f}", flush=True)
    M_knn = knn_prior(E, S, deg)
    print(f"  knn prior: median||M_knn||="
          f"{float(np.median(np.linalg.norm(M_knn, axis=1))):.4f}", flush=True)

    h_bar = sample_user_state(model, user_seqs, valid_inters, pad_id,
                              cfg["max_seq_len"], user_times=user_times)
    print(f"  mean user state ||h||={np.linalg.norm(h_bar):.4f}", flush=True)
    tables = build_tables(E, M_cal, M_knn, deg, c_grid)
    tables.update(build_dev_tables(E, M_knn, deg, h_bar=h_bar))

    print("  -- VALIDATION pass (selection) --", flush=True)
    val_agg, _, _, _, _ = eval_tables(model, tables, user_seqs, valid_inters,
                                      n_items, pad_id, cfg["max_seq_len"],
                                      user_times=user_times)
    for n, m in val_agg.items():
        print(f"    val {n:>12}: NDCG@10={m['ndcg']:.5f} HR@10={m['hr']:.5f} "
              f"HR@100={m['hr100']:.5f}", flush=True)
    eb_names = [n for n in tables if n != "stock"]
    sel = max(eb_names, key=lambda n: val_agg[n]["ndcg"])
    print(f"  selected on val: {sel}", flush=True)

    print("  -- TEST pass --", flush=True)
    test_agg, per_user, per_rank, tgts, _ = eval_tables(
        model, tables, user_seqs, test_inters, n_items, pad_id,
        cfg["max_seq_len"], extra_history=val_extra, user_times=user_times,
        extra_times=val_extra_times)

    report = {"run_json": os.path.basename(args.run_json), "category": category,
              "ckpt_epoch": int(ckpt["epoch"]),
              "recorded_best_test_ndcg10": run.get("best_test", {}).get("NDCG@10"),
              "n_deg0": int((deg == 0).sum()), "target_norm": target_norm,
              "val": {n: m for n, m in val_agg.items()},
              "selected_eb": sel, "test": {}, "test_slices": {}}
    for n, m in test_agg.items():
        report["test"][n] = m
        report["test_slices"][n] = degree_slices(per_user[n], per_rank[n],
                                                 tgts, deg)
        print(f"    test {n:>12}: NDCG@10={m['ndcg']:.5f} HR@10={m['hr']:.5f} "
              f"HR@100={m['hr100']:.5f}", flush=True)
    # Pareto readout: k0-slice gain vs warm cost (overall excluding k0 targets)
    b_of0 = np.array([1 if (t < len(deg) and deg[t] == 0) else 0 for t in tgts])
    nz = b_of0 == 0
    stock_nd = np.asarray(per_user["stock"])
    report["pareto"] = {}
    for n in tables:
        nd = np.asarray(per_user[n])
        report["pareto"][n] = {
            "k0_ndcg": float(nd[~nz].mean()) if (~nz).sum() else None,
            "nonk0_delta_vs_stock": float((nd[nz] - stock_nd[nz]).mean())}
        p = report["pareto"][n]
        print(f"    pareto {n:>12}: k0_ndcg={p['k0_ndcg']:.5f} "
              f"warm_cost={p['nonk0_delta_vs_stock']:+.6f}", flush=True)
    # headline slices
    for n in ("stock", "k0fixrdg", sel):
        sl = report["test_slices"][n]
        for kb in ("k0-0", "k1-2", "k3-5", "k6-10"):
            if kb in sl:
                s = sl[kb]
                print(f"    {n:>12} {kb:>6}: ndcg={s['ndcg10']:.5f} "
                      f"hr100={s['hr100']:.4f} medrank={s['median_rank']} "
                      f"n={s['n']}", flush=True)

    out = Path(args.out) if args.out else Path(WORKTREE_RUN) / "poc_out" / (
        Path(args.run_json).stem + ".posterior_eval.json")
    out.parent.mkdir(exist_ok=True)
    json.dump(report, open(out, "w", encoding="utf-8"), indent=1)
    print(f"  wrote {out}", flush=True)


if __name__ == "__main__":
    main()
