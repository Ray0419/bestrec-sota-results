#!/usr/bin/env python
"""FLAG-REPLICATION exploratory probe (Candidate A pre-prereg calibration).

EXPLORATORY — not pre-registered, no confirmatory claims. Purpose: calibrate
the headline uncertainty of the planned seed-stability audit ("do loss-based
denoising flags replicate across seeds?") before freezing a prereg, as
recommended by the 2026-08-01 screening run.

Setup: ADT/T-CE-style truncated-loss denoising on an MF-BCE backbone,
Taobao `buy` behavior + 10% popularity-matched injected noise (reusing the
CRI pilot's injection machinery). Per seed: train with T-CE truncation
(linear drop-rate ramp to eps_max, per ADT), record per-interaction drop
frequency over the final FLAG_EPOCHS epochs; flag set = top-10% by drop
frequency. Report: cross-seed flag-set Jaccard, flag-score Spearman,
noise-capture precision/recall, plus the same for a plain high-loss ranking
(no truncation feedback) as contrast.
"""

import json
import sys
import time
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "cri_pilot"))
from run_pilot import load_behavior, inject_noise, auc  # noqa: E402

DATA = HERE.parent / "cri_pilot" / "data"
OUT = HERE / "results"
D_DIM = 64
LR = 1e-3
L2 = 1e-5
EPOCHS = 30
FLAG_EPOCHS = 10          # drop-frequency window = last N epochs
EPS_MAX = 0.20            # ADT-style max drop rate
EPS_RAMP_EPOCHS = 10
NOISE_FRAC_FLAG = 0.10    # flag top-10% (matches injection rate)
BATCH = 32768
SEEDS = (13, 42, 2026)
N_NEG = 4                 # BCE negatives per positive


def train_one(seed, edges, n_users, n_items, device, truncate, log):
    torch.manual_seed(seed)
    g = torch.Generator(device="cpu").manual_seed(seed)
    E = torch.nn.Embedding(n_users + n_items, D_DIM, device=device)
    torch.nn.init.normal_(E.weight, std=0.1)
    opt = torch.optim.Adam(E.parameters(), lr=LR, weight_decay=L2)
    e_t = torch.as_tensor(edges, dtype=torch.long, device=device)
    n_e = len(edges)
    drop_count = torch.zeros(n_e, device=device)
    loss_sum = torch.zeros(n_e, device=device)
    loss_cnt = 0
    for ep in range(1, EPOCHS + 1):
        eps = min(EPS_MAX, EPS_MAX * ep / EPS_RAMP_EPOCHS) if truncate else 0.0
        perm = torch.randperm(n_e, generator=g).to(device)
        for k in range(0, n_e, BATCH):
            idx = perm[k: k + BATCH]
            u, i = e_t[idx, 0], e_t[idx, 1] + n_users
            pos = (E.weight[u] * E.weight[i]).sum(1)
            l_pos = torch.nn.functional.softplus(-pos)  # BCE positive part
            neg_i = torch.randint(0, n_items, (len(idx) * N_NEG,), device=device) + n_users
            un = u.repeat_interleave(N_NEG)
            neg = (E.weight[un] * E.weight[neg_i]).sum(1)
            l_neg = torch.nn.functional.softplus(neg).view(len(idx), N_NEG).mean(1)
            if eps > 0:
                n_drop = int(eps * len(idx))
                if n_drop > 0:
                    thresh = torch.topk(l_pos, n_drop).values[-1]
                    keep = l_pos < thresh
                    if ep > EPOCHS - FLAG_EPOCHS:
                        dropped = idx[~keep]
                        drop_count[dropped] += 1
                    loss = (l_pos[keep] + l_neg[keep]).mean()
                else:
                    loss = (l_pos + l_neg).mean()
            else:
                loss = (l_pos + l_neg).mean()
            opt.zero_grad()
            loss.backward()
            opt.step()
        # per-edge loss snapshot over the flag window (for plain-loss contrast)
        if ep > EPOCHS - FLAG_EPOCHS:
            with torch.no_grad():
                u, i = e_t[:, 0], e_t[:, 1] + n_users
                pos = (E.weight[u] * E.weight[i]).sum(1)
                loss_sum += torch.nn.functional.softplus(-pos)
                loss_cnt += 1
    return drop_count.cpu().numpy(), (loss_sum / max(loss_cnt, 1)).cpu().numpy()


def jaccard(a, b):
    return len(a & b) / len(a | b)


def spearman(a, b):
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    ra -= ra.mean(); rb -= rb.mean()
    return float((ra * rb).sum() / np.sqrt((ra ** 2).sum() * (rb ** 2).sum()))


def main():
    OUT.mkdir(exist_ok=True)
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    t0 = time.time()
    raw = {b: load_behavior(DATA / f"{b}_train.txt") for b in ("view", "cart", "buy")}
    n_users = max(u for e in raw.values() for u, _ in e) + 1
    n_items = max(i for e in raw.values() for _, i in e) + 1
    pop = np.zeros(n_items)
    for e in raw.values():
        for _, i in e:
            pop[i] += 1

    res = {"scores": {}, "device": device}
    flags_tce, flags_loss, masks = {}, {}, {}
    for seed in SEEDS:
        rng = np.random.default_rng(seed)
        # consume rng identically to the CRI pilot ordering (view, cart) so the
        # buy injection is bit-identical to that pilot's popularity arm
        for bb in ("view", "cart"):
            inject_noise(raw[bb], n_users, n_items, "popularity", rng, pop)
        edges, mask = inject_noise(raw["buy"], n_users, n_items, "popularity", rng, pop)
        masks[seed] = mask
        print(f"seed {seed}: {len(edges)} buy edges ({mask.sum()} injected)", flush=True)
        drop_count, mean_loss = train_one(seed, edges, n_users, n_items, device, True, print)
        _, mean_loss_plain = train_one(seed, edges, n_users, n_items, device, False, print)
        k = int(NOISE_FRAC_FLAG * len(edges))
        flags_tce[seed] = set(np.argpartition(-drop_count, k)[:k].tolist())
        flags_loss[seed] = set(np.argpartition(-mean_loss_plain, k)[:k].tolist())
        res["scores"][seed] = {
            "tce_capture_precision": float(mask[list(flags_tce[seed])].mean()),
            "loss_capture_precision": float(mask[list(flags_loss[seed])].mean()),
            "tce_auc": auc(drop_count, mask),
            "loss_auc": auc(mean_loss_plain, mask),
        }
        np.savez_compressed(OUT / f"seed{seed}.npz", drop_count=drop_count,
                            mean_loss_tce=mean_loss, mean_loss_plain=mean_loss_plain, mask=mask)
        print(f"  {res['scores'][seed]}", flush=True)

    import itertools
    pairs = list(itertools.combinations(SEEDS, 2))
    res["cross_seed"] = {
        "tce_flag_jaccard": [jaccard(flags_tce[a], flags_tce[b]) for a, b in pairs],
        "loss_flag_jaccard": [jaccard(flags_loss[a], flags_loss[b]) for a, b in pairs],
        "tce_score_spearman": [
            spearman(np.load(OUT / f"seed{a}.npz")["drop_count"], np.load(OUT / f"seed{b}.npz")["drop_count"]) for a, b in pairs],
        "loss_score_spearman": [
            spearman(np.load(OUT / f"seed{a}.npz")["mean_loss_plain"], np.load(OUT / f"seed{b}.npz")["mean_loss_plain"]) for a, b in pairs],
        "random_jaccard_baseline": NOISE_FRAC_FLAG / (2 - NOISE_FRAC_FLAG),
    }
    res["wall_s"] = round(time.time() - t0, 1)
    (OUT / "flagrep_result.json").write_text(json.dumps(res, indent=2))
    print(json.dumps(res["cross_seed"], indent=2), flush=True)
    print(f"total {res['wall_s']}s", flush=True)


if __name__ == "__main__":
    main()
