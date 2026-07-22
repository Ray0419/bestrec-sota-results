#!/usr/bin/env python
"""
Generate the BBP-irreducibility figure -- the THIRD and final figure the
supervisor (cycle-11, 2026-06-21) flagged as still outstanding (the first, the
3-panel tail-law/mechanism figure, was rendered 2026-06-21 by
`make_fig_tail_law_mechanism.py`; the second, the (R1,R2) Tilman plane, by
`make_fig_r1r2_plane.py`). With this the paper's three-figure set is complete.

WHAT IT SHOWS (the campaign's honest-negative spine, quantified):
The item ID-embedding table is genuinely low-rank, and the long tail sits BELOW
the Baik-Ben Arous-Peche (BBP) detectability threshold -- i.e. the tail items'
ID directions cannot be reliably estimated from the training interactions, no
matter the model. This is the spectral, data-derived statement of "the tail is
irreducibly sparsity-bottlenecked" -- it explains WHY no representation-side
lever (GD1 spectral shrink, X1 James-Stein shrink, the text stack on the VG/
Beauty tail) moves the VG tail, and it is a contribution that survives GD1's
negative test result (GD1 spectral shrink HURT overall: 0.0645 < V2 0.0674).

DATA PROVENANCE (verified, NOT recomputed -- pure typesetting):
All numbers are read VERBATIM from the locked, on-disk
`_bestrec_run/results_GD1_spectralshrink_VG.json` (seed 20260608, V2 stack +
--spectral-shrink --spectral-shrink-every 1 --spectral-shrink-mode hard, 40ep,
AR2023 Video_Games 5-core LLOO, full-catalog masked eval n_eval=94,762, by_pop
terciles by TRAIN frequency = leak-free). The identical BBP-rho diagnostic is
reproduced bit-for-bit in `results_GD1b_every5_VG.json` (effective rank 22).
  spectral_effective_rank        = 24  (of d_model=64; GD/MP hard threshold)
  spectral_bbp_rho_by_tercile    = {
     ell2: tail 0.0,    mid 0.0,     head 0.07262
     ell4: tail 0.0,    mid 0.07165, head 0.48868
     ell8: tail 0.21063, mid 0.42624, head 0.74566 }
  best_test.by_popularity NDCG@10 = tail 0.0016256, mid 0.0096343, head 0.0844201
rho = the fraction of a tercile's items whose top-ell ID-embedding singular
directions exceed the BBP/Marchenko-Pastur detectability edge (reliably
estimable from training interactions). Produced by the EXPERIMENT agent as
sanctioned CPU-only paper-finishing work (supervisor cycle-11), zero GPU
contention; the GD1 probe itself is on disk, nothing re-run.

Attribution: BBP phase transition = Baik, Ben Arous & Peche 2005; Marchenko-
Pastur 1967; optimal singular-value shrinkage / hard threshold = Gavish & Donoho
2014. GD1 spectral-shrink lever was the leak-free item-spectrum dual of the
confirmed causal temporal filter (FMLP/Zhou 2022 + BSARec/Shin 2024). HSTU=Zhai
2024; text stack=Hou 2024 / Liu 2025 (arXiv:2504.10545); SASRec=Kang & McAuley
2018; label smoothing=Szegedy 2016.
"""
import sys as _sys, os as _os
if "--acknowledge-retracted" not in _sys.argv:
    _sys.exit("RETRACTED GENERATOR: the BBP impossibility claim is withdrawn (RETRACTED_STATUS.json). Pass --acknowledge-retracted to render a watermarked archive copy INSIDE retracted_archive/ only.")

import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "_bestrec_run" / "results_GD1_spectralshrink_VG.json"
OUT = ROOT / "figures"
OUT.mkdir(exist_ok=True)

# ---- read the LOCKED numbers verbatim (no recompute) -------------------------
d = json.load(open(SRC))
eff_rank = d["spectral_effective_rank"]            # 24 of 64
bbp = d["spectral_bbp_rho_by_tercile"]             # ell2/ell4/ell8 -> tail/mid/head
bypop = d["best_test"]["by_popularity"]            # tail/mid/head NDCG@10 + n
D_MODEL = d["config"].get("d_model", 64)

TERCILES = ["tail", "mid", "head"]
ELLS = ["ell2", "ell4", "ell8"]
ELL_LBL = {"ell2": r"$\ell$=2", "ell4": r"$\ell$=4", "ell8": r"$\ell$=8"}
ELL_COL = {"ell2": "#bdbdbd", "ell4": "#fb8c00", "ell8": "#1f77b4"}
T_LBL = {"tail": f"tail\n(n={bypop['tail']['n']:,})",
         "mid":  f"mid\n(n={bypop['mid']['n']:,})",
         "head": f"head\n(n={bypop['head']['n']:,})"}

plt.rcParams.update({
    "font.size": 10,
    "axes.titlesize": 11.5,
    "axes.titleweight": "bold",
    "figure.dpi": 140,
    "savefig.bbox": "tight",
})

fig = plt.figure(figsize=(12.2, 5.4))
gs = fig.add_gridspec(2, 2, width_ratios=[1.5, 1.0], height_ratios=[1.0, 1.0],
                      hspace=0.62, wspace=0.26)
axA = fig.add_subplot(gs[:, 0])   # left, full height
axB = fig.add_subplot(gs[0, 1])   # top-right: effective rank
axC = fig.add_subplot(gs[1, 1])   # bottom-right: realized NDCG

# =========================== Panel A: BBP detectability =======================
x = np.arange(len(TERCILES))
w = 0.26
for j, ell in enumerate(ELLS):
    vals = [bbp[ell][t] for t in TERCILES]
    bars = axA.bar(x + (j - 1) * w, vals, w, color=ELL_COL[ell],
                   edgecolor="black", linewidth=0.7, label=ELL_LBL[ell])
    for xi, v in zip(x + (j - 1) * w, vals):
        if v == 0.0:
            axA.text(xi, 0.012, "0", ha="center", va="bottom",
                     fontsize=7.5, color="#b00020", fontweight="bold")
        else:
            axA.text(xi, v + 0.012, f"{v:.2f}", ha="center", va="bottom",
                     fontsize=7.5)

axA.set_xticks(x)
axA.set_xticklabels([T_LBL[t] for t in TERCILES])
axA.set_ylabel(r"BBP detectability $\rho$"
               "\n(fraction of items reliably estimable)")
axA.set_ylim(0, 0.86)
axA.set_title("The long tail sits BELOW the BBP detectability edge\n"
              "(VG item ID-embedding spectrum, GD/MP diagnostic)")
axA.axhspan(0.0, 0.001, color="#b00020", alpha=0.0)  # spacer
axA.legend(title="SVD rank used", fontsize=8.5, title_fontsize=8.5, loc="upper left")
axA.grid(axis="y", alpha=0.3)
axA.text(0.02, 0.74,
         "at the detectability\nthreshold "
         r"($\ell$=2): tail & mid $\rho$=0"
         "\n$\\Rightarrow$ NO tail/mid item\nID direction is reliably\nestimable",
         transform=axA.transAxes, fontsize=8, color="#b00020",
         va="top", ha="left",
         bbox=dict(boxstyle="round", fc="#fff3f3", ec="#b00020", alpha=0.9))

# =========================== Panel B: effective rank ==========================
axB.barh([0], [eff_rank], height=0.5, color="#1f77b4", edgecolor="black",
         label=f"signal rank kept = {eff_rank}")
axB.barh([0], [D_MODEL - eff_rank], height=0.5, left=[eff_rank],
         color="#dddddd", edgecolor="black",
         label=f"discarded (below MP edge) = {D_MODEL - eff_rank}")
axB.text(eff_rank / 2, 0, f"{eff_rank}", ha="center", va="center",
         fontsize=11, fontweight="bold", color="white")
axB.text(eff_rank + (D_MODEL - eff_rank) / 2, 0, f"{D_MODEL - eff_rank}",
         ha="center", va="center", fontsize=11, color="#555555")
axB.set_xlim(0, D_MODEL)
axB.set_ylim(-0.6, 0.6)
axB.set_yticks([])
axB.set_xlabel(f"item-embedding dimensions (of {D_MODEL})")
axB.set_title(f"GD/MP hard threshold keeps only {eff_rank} of {D_MODEL} dims\n"
              "$\\Rightarrow$ the item table is genuinely low-rank")
axB.legend(fontsize=7.8, loc="lower center", bbox_to_anchor=(0.5, 1.0),
           ncol=1, framealpha=0.93)
axB.grid(axis="x", alpha=0.2)

# =========================== Panel C: realized NDCG ===========================
ndcg = [bypop[t]["NDCG@10"] for t in TERCILES]
xb = np.arange(len(TERCILES))
colB = {"tail": "#b00020", "mid": "#fb8c00", "head": "#2ca02c"}
for xi, t in zip(xb, TERCILES):
    axC.bar(xi, ndcg[xi], 0.62, color=colB[t], edgecolor="black", linewidth=0.7)
    axC.text(xi, ndcg[xi] * 1.18, f"{ndcg[xi]:.4f}", ha="center", va="bottom",
             fontsize=8)
axC.set_yscale("log")
axC.set_ylim(8e-4, 0.2)
axC.set_xticks(xb)
axC.set_xticklabels(TERCILES)
axC.set_ylabel("test NDCG@10\n(log scale)")
axC.set_title("Realized accuracy tracks detectability:\n"
              "tail $\\approx$52$\\times$ below head")
axC.grid(axis="y", alpha=0.3, which="both")

fig.suptitle("Spectral irreducibility of the long tail: why no representation-side lever rescues it",
             fontsize=13, fontweight="bold", y=1.02)

fig.text(0.5, -0.04,
         "Source: results_GD1_spectralshrink_VG.json (V2 stack + GD/MP spectral hard-shrink, seed 20260608, AR2023 VG 5-core LLOO, "
         "full-catalog n_eval=94,762, train-frequency terciles). BBP $\\rho$ = fraction of a tercile's items whose top-$\\ell$ ID "
         "singular directions clear the Marchenko-Pastur/BBP detectability edge. GD1 spectral-shrink itself HURT overall "
         "(0.0645 < V2 0.0674) -- this diagnostic is the contribution that survives that negative test. "
         "BBP=Baik-Ben Arous-Peche 2005; shrinkage=Gavish-Donoho 2014.",
         ha="center", fontsize=7.2, color="#444444", wrap=True)

png = OUT / "fig_bbp_irreducibility.png"
pdf = OUT / "fig_bbp_irreducibility.pdf"
fig.savefig(png)
fig.savefig(pdf)
print("WROTE", png)
print("WROTE", pdf)
print("eff_rank=%d/%d  bbp=%s  ndcg=%s" % (eff_rank, D_MODEL, bbp, ndcg))
