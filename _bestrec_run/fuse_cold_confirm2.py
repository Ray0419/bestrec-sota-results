# -*- coding: utf-8 -*-
"""PREREG_COLDFUSE_V2 streaming confirmatory evaluator (E-G2).

Differences from the deviated E-G evaluator, all frozen in the prereg:
 - endpoint bin is f1-5 (train frequency 1..5); f0 is a SEPARATE diagnostic
   bin excluded from every benefit endpoint; mid 6-20; head >20;
 - candidate grid brackets above 0.2: tail in {.1,.15,.2,.25,.3,.4,.6},
   mid/head in {0,.05,.1}, monotone t>=m>=h; profiles uniform/exp0.9 (84);
 - VAL selection maximizes f1-5 subject to guardrails: overall >= ref-0.0002
   AND mid >= ref_mid-0.0010 AND head >= ref_head-0.0005;
 - control arms evaluated once on TEST at the selected policy: C1
   frequency-only additive prior (no text), C2 dimension-matched random
   features (frozen rng 12345), C3 within-frequency-bin permuted text
   (frozen rng 12345), C4 pure-text diagnostic;
 - TEST metric values are SEQUESTERED: never printed; written only to the
   artifact files, whose first reader is the committed adjudicator.

Usage: python fuse_cold_confirm2.py <base_run.json> [--no-ease] [--out o]
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_sasrec_sbert as rsp
from fuse_ease_eval import build_model_from_config, ease_B

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
T_SET = (0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.6)
MH_SET = (0.0, 0.05, 0.1)
G_OVER, G_MID, G_HEAD = 0.0002, 0.0010, 0.0005
BATCH = 512
CTRL_SEED = 12345


def candidates():
    out = []
    for prof in ("uniform", "exp0.9"):
        for t in T_SET:
            for m2 in MH_SET:
                for h in MH_SET:
                    if t >= m2 >= h:
                        out.append({"profile": prof, "wt_tail": t,
                                    "wt_mid": m2, "wt_head": h})
    return out              # 2 x 7 x 6 = 84


def zrow(x):
    mu = x.mean(dim=1, keepdim=True)
    sd = x.std(dim=1, keepdim=True).clamp_min(1e-8)
    return (x - mu) / sd


def stream_eval(model, users, user_seqs, extra, user_times, xtimes, cfg,
                pad_id, n_items, EMBS, B_gpu, we, systems, bin_idx4,
                tgt_dict, collect_per_user=False, silent=False):
    """systems: {"name", "kind": ref|text|const, "profile", "wvec",
    "emb": key into EMBS or None}. Four-bin accounting (f0/f15/mid/head)."""
    n = len(users)
    max_seq_len = cfg["max_seq_len"]
    use_times = getattr(model, "use_time_bias", False) and user_times is not None
    acc = {s["name"]: {"nd": 0.0, "hit": 0.0, "nd_b": np.zeros(4),
                       "n_b": np.zeros(4)} for s in systems}
    per_user = ({s["name"]: np.zeros(n, dtype=np.float32) for s in systems}
                if collect_per_user else None)
    need = sorted({(s["emb"], s["profile"]) for s in systems
                   if s["kind"] == "text"})
    t0 = time.time()
    with torch.no_grad():
        all_items = model.all_item_features()
        for s0 in range(0, n, BATCH):
            bu = users[s0:s0 + BATCH]
            Bn = len(bu)
            input_ids = torch.full((Bn, max_seq_len), pad_id, dtype=torch.long,
                                   device=DEVICE)
            times_t = (torch.zeros((Bn, max_seq_len), dtype=torch.long,
                                   device=DEVICE) if use_times else None)
            hists, real_len = [], []
            for k, u in enumerate(bu):
                seq = list(user_seqs.get(u, []))
                if u in extra:
                    seq = seq + list(extra[u])
                hists.append(seq)
                tr = seq[-max_seq_len:]
                if tr:
                    input_ids[k, :len(tr)] = torch.tensor(
                        tr, dtype=torch.long, device=DEVICE)
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
            last = hidden[torch.arange(Bn, device=DEVICE),
                          torch.tensor([max(0, r - 1) for r in real_len],
                                       device=DEVICE), :]
            zs = zrow(last @ all_items.T)
            if B_gpu is not None and we != 0.0:
                xu = torch.zeros((Bn, n_items), device=DEVICE)
                for k, hh in enumerate(hists):
                    if hh:
                        xu[k, torch.tensor(hh, dtype=torch.long,
                                           device=DEVICE)] = 1.0
                ref = zs + we * zrow(xu @ B_gpu)
            else:
                ref = zs
            zt = {}
            for emb_key, prof in need:
                E_gpu = EMBS[emb_key]
                P = torch.zeros((Bn, E_gpu.shape[1]), device=DEVICE)
                for k, hh in enumerate(hists):
                    if not hh:
                        continue
                    idx = torch.tensor(hh, dtype=torch.long, device=DEVICE)
                    V = E_gpu[idx]
                    if prof == "uniform":
                        P[k] = V.mean(dim=0)
                    else:
                        w = torch.pow(torch.tensor(0.9, device=DEVICE),
                                      torch.arange(len(hh) - 1, -1, -1,
                                                   device=DEVICE,
                                                   dtype=torch.float))
                        P[k] = (V * (w / w.sum()).unsqueeze(1)).sum(dim=0)
                zt[(emb_key, prof)] = zrow(P @ E_gpu.T)
            hmax = max((len(h) for h in hists), default=1) or 1
            seen_idx = torch.zeros((Bn, hmax), dtype=torch.long, device=DEVICE)
            seen_msk = torch.zeros((Bn, hmax), dtype=torch.bool, device=DEVICE)
            for k, hh in enumerate(hists):
                if hh:
                    seen_idx[k, :len(hh)] = torch.tensor(
                        hh, dtype=torch.long, device=DEVICE)
                    seen_msk[k, :len(hh)] = True
            tgt = torch.tensor([tgt_dict[u] for u in bu], dtype=torch.long,
                               device=DEVICE)
            ar = torch.arange(Bn, device=DEVICE)
            tb = bin_idx4[tgt.cpu().numpy()]
            for sysd in systems:
                if sysd["kind"] == "ref":
                    F = ref
                elif sysd["kind"] == "const":
                    F = ref + sysd["wvec"]
                elif sysd["kind"] == "puretext":
                    F = zt[(sysd["emb"], sysd["profile"])]
                else:
                    F = ref + zt[(sysd["emb"], sysd["profile"])] * sysd["wvec"]
                ts = F[ar, tgt]
                base = (F > ts.unsqueeze(1)).sum(dim=1)
                sc = F.gather(1, seen_idx)
                corr = ((sc > ts.unsqueeze(1)) & seen_msk).sum(dim=1)
                r0 = (base - corr).cpu().numpy()
                nd = np.where(r0 < 10, 1.0 / np.log2(r0 + 2.0), 0.0)
                a = acc[sysd["name"]]
                a["nd"] += float(nd.sum())
                a["hit"] += float((r0 < 10).sum())
                for b in range(4):
                    m2 = tb == b
                    a["nd_b"][b] += float(nd[m2].sum())
                    a["n_b"][b] += int(m2.sum())
                if collect_per_user:
                    per_user[sysd["name"]][s0:s0 + Bn] = nd
            if not silent and (s0 // BATCH) % 40 == 0:
                print(f"    [{s0 + Bn:,}/{n:,} {time.time()-t0:.0f}s]",
                      flush=True)
    res = {}
    for name, a in acc.items():
        res[name] = {"overall": a["nd"] / n, "hr": a["hit"] / n, "n": n,
                     "f0": a["nd_b"][0] / max(a["n_b"][0], 1),
                     "f15": a["nd_b"][1] / max(a["n_b"][1], 1),
                     "mid": a["nd_b"][2] / max(a["n_b"][2], 1),
                     "head": a["nd_b"][3] / max(a["n_b"][3], 1),
                     "n_f0": int(a["n_b"][0]), "n_f15": int(a["n_b"][1])}
    return res, per_user


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_json")
    ap.add_argument("--no-ease", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    base = json.load(open(args.run_json, encoding="utf-8"))
    cfg = base["config"]
    category = cfg["category"]
    print(f"=== COLDFUSE2 confirm: {category} seed {cfg['seed']} "
          f"(ease={'no' if args.no_ease else 'yes'}; test sequestered) ===",
          flush=True)

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
    val_dict = {u: i for u, i, _, _ in valid_inters}
    test_dict = {u: i for u, i, _, _ in test_inters}
    val_users = sorted(val_dict.keys())
    test_users = sorted(test_dict.keys())

    freq = np.zeros(n_items, dtype=np.int64)
    for _, i, _, _ in train_inters:
        freq[i] += 1
    bin4 = np.where(freq == 0, 0,
                    np.where(freq <= 5, 1,
                             np.where(freq <= 20, 2, 3))).astype(np.int64)

    enc_cache = cfg.get("encoder_cache")
    sbert_npy = Path(enc_cache) if enc_cache else \
        rsp.EMB_CACHE_DIR / f"sbert_titles_{category}.npy"
    Eraw = np.load(sbert_npy).astype(np.float32)[:n_items]
    E = Eraw / np.clip(np.linalg.norm(Eraw, axis=1, keepdims=True), 1e-8, None)
    rng = np.random.default_rng(CTRL_SEED)
    Erand = rng.standard_normal(E.shape).astype(np.float32)
    Erand /= np.clip(np.linalg.norm(Erand, axis=1, keepdims=True), 1e-8, None)
    Eperm = E.copy()
    for b in range(4):
        idx = np.where(bin4 == b)[0]
        Eperm[idx] = Eperm[rng.permutation(idx)]
    EMBS = {"aligned": torch.from_numpy(E).to(DEVICE),
            "random": torch.from_numpy(Erand).to(DEVICE),
            "permuted": torch.from_numpy(Eperm).to(DEVICE)}

    ckpt = torch.load(Path(args.run_json).with_suffix(".best.pt"),
                      map_location="cpu", weights_only=False)
    proto_assign = [t.to(DEVICE) for t in ckpt.get("proto_assign", [])] or None
    model = build_model_from_config(cfg, n_items, pad_id, Eraw, proto_assign)
    model.load_state_dict(ckpt["state_dict"], strict=False)
    model.to(DEVICE).eval()

    if args.no_ease:
        we, l2, B_gpu = 0.0, None, None
        ref_name = "seq"
    else:
        fus = json.load(open(args.run_json[:-5] + ".fusion.json",
                             encoding="utf-8"))
        assert fus.get("val_only"), "E-G2 requires a --val-only fusion record"
        l2 = float(fus["selected"]["l2"])
        we = float(fus["selected"]["w"])
        _, B = ease_B(train_inters, n_users, n_items, l2)
        B_gpu = torch.from_numpy(B).to(DEVICE)
        del B
        ref_name = "fused2"

    wvecs = []
    for c in candidates():
        wv = np.zeros(n_items, dtype=np.float32)
        wv[bin4 == 1] = c["wt_tail"]        # f1-5 endpoint bin
        wv[bin4 == 0] = c["wt_tail"]        # f0 gets the same weight but is
        wv[bin4 == 2] = c["wt_mid"]         # excluded from every endpoint
        wv[bin4 == 3] = c["wt_head"]
        wvecs.append({"name": json.dumps(c, sort_keys=True), "kind": "text",
                      "emb": "aligned", "profile": c["profile"],
                      "wvec": torch.from_numpy(wv).to(DEVICE), "combo": c})
    systems_val = [{"name": "REF", "kind": "ref", "emb": None,
                    "profile": None, "wvec": None}] + wvecs

    print(f"  [val] streaming sweep: {len(systems_val)} systems ...",
          flush=True)
    vres, _ = stream_eval(model, val_users, user_seqs, {}, user_times, {},
                          cfg, pad_id, n_items, EMBS, B_gpu, we, systems_val,
                          bin4, val_dict)
    ref_v = vres["REF"]
    best = None
    feasible = 0
    for s in wvecs:
        r = vres[s["name"]]
        if (r["overall"] >= ref_v["overall"] - G_OVER
                and r["mid"] >= ref_v["mid"] - G_MID
                and r["head"] >= ref_v["head"] - G_HEAD):
            feasible += 1
            if best is None or r["f15"] > best[0]:
                best = (r["f15"], s)
    if best is None:
        print("  NO feasible candidate under the guardrails; selecting REF "
              "(null result recorded)", flush=True)
        sel = None
    else:
        sel = best[1]
        print(f"  VAL selected {sel['combo']} (feasible {feasible}/84; "
              f"val f15 {best[0]:.5f} vs ref {ref_v['f15']:.5f})", flush=True)

    print("  [test] sequestered pass: ref + selected + 4 controls ...",
          flush=True)
    test_systems = [{"name": "REF", "kind": "ref", "emb": None,
                     "profile": None, "wvec": None}]
    if sel is not None:
        test_systems.append({"name": "SEL", "kind": "text", "emb": "aligned",
                             "profile": sel["profile"], "wvec": sel["wvec"]})
        test_systems.append({"name": "C1_freqonly", "kind": "const",
                             "emb": None, "profile": None,
                             "wvec": sel["wvec"]})
        test_systems.append({"name": "C2_random", "kind": "text",
                             "emb": "random", "profile": sel["profile"],
                             "wvec": sel["wvec"]})
        test_systems.append({"name": "C3_permuted", "kind": "text",
                             "emb": "permuted", "profile": sel["profile"],
                             "wvec": sel["wvec"]})
        test_systems.append({"name": "C4_puretext", "kind": "puretext",
                             "emb": "aligned", "profile": sel["profile"],
                             "wvec": None})
    tres, pu = stream_eval(model, test_users, user_seqs, val_extra,
                           user_times, val_extra_times, cfg, pad_id, n_items,
                           EMBS, B_gpu, we, test_systems, bin4,
                           test_dict, collect_per_user=True, silent=True)
    print("  test pass complete (values sequestered to the artifact)",
          flush=True)

    out = Path(args.out) if args.out else Path(args.run_json).with_name(
        f"results_{category}_COLDFUSE2_confirm_seed{cfg['seed']}.json")
    report = {"category": category, "seed": cfg["seed"],
              "reference": ref_name, "ease": {"l2": l2, "we": we},
              "guardrails": {"overall": G_OVER, "mid": G_MID, "head": G_HEAD},
              "bins": "f0 / f1-5 (endpoint) / mid 6-20 / head >20",
              "control_seed": CTRL_SEED,
              "val_sweep": {s["name"]: vres[s["name"]] for s in systems_val},
              "feasible_candidates": feasible,
              "selected": sel["combo"] if sel else None,
              "test": tres}
    json.dump(report, open(out, "w", encoding="utf-8"), indent=1)
    tb = np.array([bin4[test_dict[u]] for u in test_users], dtype=np.int64)
    np.savez_compressed(str(out)[:-5] + ".perusers.npz",
                        users=np.array(test_users, dtype=np.int64),
                        target_bin4=tb,
                        **{f"{k}_ndcg": v for k, v in (pu or {}).items()})
    print(f"wrote {out} (metrics sequestered)", flush=True)


if __name__ == "__main__":
    main()
