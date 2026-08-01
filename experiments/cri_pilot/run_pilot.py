#!/usr/bin/env python
"""CRI Pilot V1 — cross-relation influence disagreement, feasibility.

Pre-registration: PREREG_CRI_PILOT_V1.md (frozen 2026-08-01). This script
implements exactly the declared design; any deviation must be logged as an
erratum in the prereg.

Per (noise_type, seed): inject noise into each behavior graph, train
(a) a shared-base-embedding multi-behavior LightGCN and (b) a pooled
union-graph LightGCN control, snapshot at declared checkpoint epochs, and
accumulate per-edge scores:

  D          1 - mean_{b'!=b} cos(g_b(e), U_{b'}(u))   [the RQ statistic]
  SI_b       sum_ckpt ||g_b(e)||^2                     [per-relation magnitude ablation]
  SI_pooled  sum_ckpt ||g(e)||^2 from pooled control   [Koh-Liang homogeneous control]
  Loss       mean_ckpt BPR loss of e                   [cheap ADT-style competitor]

Gradients are closed-form BPR gradients w.r.t. the post-propagation user
embedding (declared representation-space simplification):
  L = -log sigma(s_ui - s_uj),  dL/dz_u = sigma(-(s_ui - s_uj)) * (z_j - z_i)

Outputs per run: results/<noise>_<seed>.json (AUCs, timings) and
results/<noise>_<seed>_scores.npz (per-edge scores + noise mask, for the
cross-seed Spearman gate G2 computed by adjudicate.py).
"""

import argparse
import json
import time
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
BEHAVIORS = ["view", "cart", "buy"]
TARGET = "buy"
D_DIM = 64
N_LAYERS = 2
LR = 1e-3
L2 = 1e-4
EPOCHS = 40
CKPTS = (10, 20, 30, 40)
NOISE_FRAC = 0.10
BATCH = 32768  # not prereg-frozen; chosen so the full pilot fits gate G1 (<4h)


def load_behavior(path: Path) -> list[tuple[int, int]]:
    edges = []
    for line in path.read_text().splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        u = int(parts[0])
        edges.extend((u, int(i)) for i in parts[1:])
    return edges


def inject_noise(edges, n_users, n_items, noise_type, rng, item_pop):
    """Add NOISE_FRAC * |E| fake edges. Users sampled by their degree in this
    behavior; items uniform (N1) or popularity-proportional (N2). Returns
    (all_edges, mask) with mask=1 on injected edges."""
    existing = set(edges)
    users = np.array([u for u, _ in edges])
    n_add = int(len(edges) * NOISE_FRAC)
    if noise_type == "uniform":
        p_item = None
    else:  # popularity
        p_item = item_pop / item_pop.sum()
    fake = []
    while len(fake) < n_add:
        u = users[rng.integers(len(users))]
        i = rng.integers(n_items) if p_item is None else rng.choice(n_items, p=p_item)
        if (u, int(i)) not in existing:
            existing.add((u, int(i)))
            fake.append((u, int(i)))
    all_edges = edges + fake
    mask = np.zeros(len(all_edges), dtype=np.int8)
    mask[len(edges):] = 1
    return all_edges, mask


class LightGCN(torch.nn.Module):
    """Shared base embedding; per-graph mean-of-powers propagation."""

    def __init__(self, n_users, n_items, graphs, device):
        super().__init__()
        self.n_users, self.n_items = n_users, n_items
        self.emb = torch.nn.Embedding(n_users + n_items, D_DIM)
        torch.nn.init.normal_(self.emb.weight, std=0.1)
        # Precompute normalized edge index + weight per graph (sym-normalized
        # bipartite adjacency over the stacked (user; item) node set).
        self.props = {}
        for name, edges in graphs.items():
            e = torch.as_tensor(edges, dtype=torch.long)
            src = torch.cat([e[:, 0], e[:, 1] + n_users])
            dst = torch.cat([e[:, 1] + n_users, e[:, 0]])
            deg = torch.zeros(n_users + n_items)
            deg.index_add_(0, src, torch.ones(len(src)))
            w = (deg[src].clamp(min=1) ** -0.5) * (deg[dst].clamp(min=1) ** -0.5)
            self.props[name] = (src.to(device), dst.to(device), w.to(device))
        self.to(device)

    def propagate(self, name):
        src, dst, w = self.props[name]
        x = self.emb.weight
        out = x
        h = x
        for _ in range(N_LAYERS):
            nxt = torch.zeros_like(h)
            nxt.index_add_(0, dst, h[src] * w.unsqueeze(1))
            h = nxt
            out = out + h
        z = out / (N_LAYERS + 1)
        return z[: self.n_users], z[self.n_users:]


def train_model(model, graphs_edges, n_items, epochs, ckpt_epochs, rng, device, log):
    opt = torch.optim.Adam(model.parameters(), lr=LR, weight_decay=L2)
    tensors = {
        b: torch.as_tensor(e, dtype=torch.long, device=device)
        for b, e in graphs_edges.items()
    }
    snapshots = []
    for ep in range(1, epochs + 1):
        t0 = time.time()
        total = 0.0
        for b, e in tensors.items():
            perm = torch.randperm(len(e), device=device)
            for k in range(0, len(e), BATCH):
                idx = perm[k: k + BATCH]
                u, i = e[idx, 0], e[idx, 1]
                j = torch.randint(0, n_items, (len(idx),), device=device)
                zu, zi = model.propagate(b)
                s_pos = (zu[u] * zi[i]).sum(1)
                s_neg = (zu[u] * zi[j]).sum(1)
                loss = torch.nn.functional.softplus(s_neg - s_pos).mean()
                opt.zero_grad()
                loss.backward()
                opt.step()
                total += loss.item() * len(idx)
        log(f"    epoch {ep:3d} loss {total / sum(len(e) for e in tensors.values()):.4f} ({time.time() - t0:.1f}s)")
        if ep in ckpt_epochs:
            snapshots.append(model.emb.weight.detach().clone())
    return snapshots


def edge_grads(zu, zi, edges_t, neg_t):
    """Closed-form BPR gradient w.r.t. z_u, plus per-edge loss."""
    u, i = edges_t[:, 0], edges_t[:, 1]
    s_pos = (zu[u] * zi[i]).sum(1)
    s_neg = (zu[u] * zi[neg_t]).sum(1)
    sig = torch.sigmoid(s_neg - s_pos)  # sigma(-(s_pos - s_neg))
    g = sig.unsqueeze(1) * (zi[neg_t] - zi[i])
    loss = torch.nn.functional.softplus(s_neg - s_pos)
    return g, loss


def propagate_from(weight, props, n_users):
    src, dst, w = props
    out = weight
    h = weight
    for _ in range(N_LAYERS):
        nxt = torch.zeros_like(h)
        nxt.index_add_(0, dst, h[src] * w.unsqueeze(1))
        h = nxt
        out = out + h
    z = out / (N_LAYERS + 1)
    return z[:n_users], z[n_users:]


def auc(scores, mask):
    """Mann-Whitney AUC of scores ranking mask==1 above mask==0."""
    order = np.argsort(scores, kind="mergesort")
    ranks = np.empty(len(scores))
    ranks[order] = np.arange(1, len(scores) + 1)
    # midranks for ties
    s_sorted = scores[order]
    kk = 0
    while kk < len(s_sorted):
        jj = kk
        while jj + 1 < len(s_sorted) and s_sorted[jj + 1] == s_sorted[kk]:
            jj += 1
        if jj > kk:
            ranks[order[kk: jj + 1]] = (kk + 1 + jj + 1) / 2.0
        kk = jj + 1
    n1 = int(mask.sum())
    n0 = len(mask) - n1
    if n1 == 0 or n0 == 0:
        return float("nan")
    return float((ranks[mask == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def run_one(noise_type, seed, data_dir, out_dir, epochs, ckpt_epochs, device, log):
    t_start = time.time()
    rng = np.random.default_rng(seed)
    torch.manual_seed(seed)

    raw = {b: load_behavior(data_dir / f"{b}_train.txt") for b in BEHAVIORS}
    n_users = max(u for e in raw.values() for u, _ in e) + 1
    n_items = max(i for e in raw.values() for _, i in e) + 1
    pop = np.zeros(n_items)
    for e in raw.values():
        for _, i in e:
            pop[i] += 1

    graphs, masks = {}, {}
    for b in BEHAVIORS:
        graphs[b], masks[b] = inject_noise(raw[b], n_users, n_items, noise_type, rng, pop)
    log(f"  edges+noise: " + ", ".join(f"{b}={len(graphs[b])}" for b in BEHAVIORS))

    # fixed scoring negatives per edge (declared: deterministic per seed)
    neg = {b: torch.as_tensor(rng.integers(0, n_items, len(graphs[b])), dtype=torch.long, device=device) for b in BEHAVIORS}
    edges_t = {b: torch.as_tensor(graphs[b], dtype=torch.long, device=device) for b in BEHAVIORS}

    # --- multi-behavior model ---
    log("  training multi-behavior model")
    mb = LightGCN(n_users, n_items, graphs, device)
    snaps_mb = train_model(mb, graphs, n_items, epochs, ckpt_epochs, rng, device, log)

    # --- pooled control (union graph, single relation) ---
    log("  training pooled control")
    union = sorted(set(e for b in BEHAVIORS for e in graphs[b]))
    union_idx = {e: k for k, e in enumerate(union)}
    pooled = LightGCN(n_users, n_items, {"all": union}, device)
    snaps_p = train_model(pooled, {"all": union}, n_items, epochs, ckpt_epochs, rng, device, log)
    union_t = torch.as_tensor(union, dtype=torch.long, device=device)
    neg_union = torch.as_tensor(rng.integers(0, n_items, len(union)), dtype=torch.long, device=device)

    # --- score accumulation over checkpoints ---
    D = {b: np.zeros(len(graphs[b])) for b in BEHAVIORS}
    SI_b = {b: np.zeros(len(graphs[b])) for b in BEHAVIORS}
    LOSS = {b: np.zeros(len(graphs[b])) for b in BEHAVIORS}
    SI_pool_union = np.zeros(len(union))
    D_defined = {b: np.zeros(len(graphs[b]), dtype=bool) for b in BEHAVIORS}

    for w_mb, w_p in zip(snaps_mb, snaps_p):
        zs = {b: propagate_from(w_mb, mb.props[b], n_users) for b in BEHAVIORS}
        g, losses = {}, {}
        for b in BEHAVIORS:
            g[b], losses[b] = edge_grads(*zs[b], edges_t[b], neg[b])
            SI_b[b] += (g[b] ** 2).sum(1).cpu().numpy()
            LOSS[b] += (losses[b] / len(ckpt_epochs)).cpu().numpy()
        # per-user mean gradient field per behavior, normalized
        U = {}
        for b in BEHAVIORS:
            acc = torch.zeros(n_users, D_DIM, device=device)
            cnt = torch.zeros(n_users, device=device)
            acc.index_add_(0, edges_t[b][:, 0], g[b])
            cnt.index_add_(0, edges_t[b][:, 0], torch.ones(len(g[b]), device=device))
            U[b] = torch.nn.functional.normalize(acc / cnt.clamp(min=1).unsqueeze(1), dim=1)
            U[b][cnt == 0] = 0.0
        for b in BEHAVIORS:
            gn = torch.nn.functional.normalize(g[b], dim=1)
            u_idx = edges_t[b][:, 0]
            cos_sum = torch.zeros(len(g[b]), device=device)
            n_other = torch.zeros(len(g[b]), device=device)
            for b2 in BEHAVIORS:
                if b2 == b:
                    continue
                ub2 = U[b2][u_idx]
                has = (ub2.abs().sum(1) > 0).float()
                cos_sum += (gn * ub2).sum(1) * has
                n_other += has
            defined = n_other > 0
            d = torch.ones(len(g[b]), device=device)  # neutral where undefined
            d[defined] = 1.0 - cos_sum[defined] / n_other[defined]
            D[b] += d.cpu().numpy()
            D_defined[b] |= defined.cpu().numpy()
        zu_p, zi_p = propagate_from(w_p, pooled.props["all"], n_users)
        g_p, _ = edge_grads(zu_p, zi_p, union_t, neg_union)
        SI_pool_union += (g_p ** 2).sum(1).cpu().numpy()

    # map pooled scores back to per-behavior edge lists
    SI_pool = {
        b: np.array([SI_pool_union[union_idx[e]] for e in graphs[b]]) for b in BEHAVIORS
    }

    res = {"noise": noise_type, "seed": seed, "epochs": epochs,
           "n_users": int(n_users), "n_items": int(n_items),
           "d_undefined_frac": {b: float(1 - D_defined[b].mean()) for b in BEHAVIORS},
           "auc": {}, "wall_s": None}
    for b in BEHAVIORS:
        m = masks[b]
        res["auc"][b] = {
            "D": auc(D[b], m),
            "SI_b": auc(SI_b[b], m),
            "SI_pooled": auc(SI_pool[b], m),
            "Loss": auc(LOSS[b], m),
        }
    res["wall_s"] = round(time.time() - t_start, 1)

    tag = f"{noise_type}_{seed}"
    np.savez_compressed(out_dir / f"{tag}_scores.npz",
                        **{f"D_{b}": D[b] for b in BEHAVIORS},
                        **{f"mask_{b}": masks[b] for b in BEHAVIORS},
                        **{f"SIp_{b}": SI_pool[b] for b in BEHAVIORS},
                        **{f"SIb_{b}": SI_b[b] for b in BEHAVIORS},
                        **{f"Loss_{b}": LOSS[b] for b in BEHAVIORS})
    (out_dir / f"{tag}.json").write_text(json.dumps(res, indent=2))
    log(f"  done in {res['wall_s']}s AUCs: {json.dumps(res['auc'])}")
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true", help="2 epochs, 1 config")
    ap.add_argument("--data", default=str(HERE / "data"))
    ap.add_argument("--out", default=str(HERE / "results"))
    args = ap.parse_args()

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    logf = open(out_dir / ("smoke.log" if args.smoke else "pilot.log"), "a")

    def log(msg):
        print(msg, flush=True)
        logf.write(msg + "\n")
        logf.flush()

    log(f"== CRI pilot {'SMOKE' if args.smoke else 'FULL'} device={device} {time.strftime('%F %T')}")
    if args.smoke:
        configs = [("uniform", 13)]
        epochs, ckpts = 2, (1, 2)
    else:
        configs = [(n, s) for n in ("uniform", "popularity") for s in (13, 42, 2026)]
        epochs, ckpts = EPOCHS, CKPTS

    for noise_type, seed in configs:
        log(f"== run noise={noise_type} seed={seed}")
        run_one(noise_type, seed, Path(args.data), out_dir, epochs, ckpts, device, log)
    log("== all runs complete")


if __name__ == "__main__":
    main()
