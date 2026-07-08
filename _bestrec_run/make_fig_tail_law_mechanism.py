#!/usr/bin/env python
"""
Generate the v3.4-spine headline figure: the dataset-conditional long-tail law
and its two-axis causal decomposition (interaction-density vs collaborative
connectivity).

ALL numbers are hard-coded from the LOCKED, 3x-supervisor-audited tables in
PAPER_DRAFT.md (sections 5.3 Table 1d, 5.4 titration ladder, 5.4.1 + 5.4.2
double-dissociation tail/head text/ID ratio tables). NOTHING is recomputed here
-- this is typesetting of already-locked, leak-free, best-by-val paired text-ID
results (AR2023 5-core LLOO, full-catalog masked eval, n_eval=94,762,
tail_n=10,900 frozen). Produced by the EXPERIMENT agent as sanctioned CPU-only
paper-finishing work (supervisor cycle-11, 2026-06-21), zero GPU contention.

Attribution of the underlying method: HSTU=Zhai 2024; causal spectral filter
adapted leak-free from FMLP/Zhou 2022 + BSARec/Shin 2024; text stack (SBERT
features / text-sim bias / TAPE prototypes)=Hou 2024 / Liu 2025
(arXiv:2504.10545); SASRec=Kang & McAuley 2018; label smoothing=Szegedy 2016.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "figures"
OUT.mkdir(exist_ok=True)

# ------------------------------------------------------------------ palette
C_TEXT = "#1f77b4"   # text-augmented
C_ID   = "#d62728"   # ID-only
C_WIN  = "#2ca02c"
C_NULL = "#7f7f7f"
C_HEAD = "#ff7f0e"
C_TAIL = "#1f77b4"

plt.rcParams.update({
    "font.size": 10,
    "axes.titlesize": 11,
    "axes.titleweight": "bold",
    "figure.dpi": 140,
    "savefig.bbox": "tight",
})

fig, axes = plt.subplots(1, 3, figsize=(15, 4.6))

# ================================================================== Panel A
# 5.3 Table 1d: text - ID tail-tercile NDCG@10 contrast (paired, per-seed).
axA = axes[0]
ds      = ["Musical_Instr.\n(sparse)", "Video_Games\n(dense)", "Beauty_&_PC\n(dense)"]
tailD   = [ 0.000335, -0.000148, -0.000018]
tailErr = [ 0.000195,  0.000179,  0.000000]   # MI/VG 5-seed sd; Beauty 2-3 seed (no band)
posfrac = ["5/5", "2/5", "0/2"]
verdict = ["text WINS\nthe tail", "powered\nNULL", "NULL"]
cols    = [C_WIN, C_NULL, C_NULL]
x = np.arange(len(ds))
axA.bar(x, tailD, yerr=tailErr, color=cols, edgecolor="black", linewidth=0.8,
        capsize=5, width=0.6, error_kw=dict(elinewidth=1.2))
axA.axhline(0, color="black", linewidth=0.9)
# MI CI annotation (excludes 0)
axA.annotate("95% CI\n[+0.00009, +0.00058]\nexcludes 0",
             xy=(0, 0.000335), xytext=(0, 0.00060),
             ha="center", fontsize=7.5, color=C_WIN,
             arrowprops=dict(arrowstyle="-", color=C_WIN, lw=0.8))
for xi, (d, p, v) in enumerate(zip(tailD, posfrac, verdict)):
    yoff = 0.00004 if d >= 0 else -0.00010
    axA.text(xi, d + yoff + (0.00004 if d >= 0 else -0.00006),
             f"{d:+.6f}\n{p} seeds +", ha="center",
             va="bottom" if d >= 0 else "top", fontsize=7.5)
axA.set_xticks(x)
axA.set_xticklabels(ds, fontsize=8.5)
axA.set_ylabel("tail-tercile  $\\Delta$NDCG@10  (text $-$ ID)")
axA.set_title("(A) The dataset-conditional tail law\n(sparse catalog: text wins the tail)")
axA.set_ylim(-0.00055, 0.00085)
axA.grid(axis="y", alpha=0.3)

# ================================================================== Panel B
# 5.4 titration ladder: head Delta monotone vs density (CONFIRMED cause);
# tail Delta trend-free (REFUTED cause). x = thinning rho (1.0 -> 0.66).
axB = axes[1]
rho     = [1.00, 0.94, 0.91, 0.88, 0.78, 0.66]
headD   = [0.00221, 0.00239, 0.00254, 0.00252, 0.00266, 0.00354]
tailDl  = [-0.000148, 0.000165, 0.000039, 0.000537, 0.000056, -0.000108]
axB.plot(rho, headD, "-o", color=C_HEAD, lw=2, ms=6,
         label="HEAD $\\Delta$ (monotone, $\\rho_s=-0.94$): density CONFIRMED cause")
axB.plot(rho, tailDl, "-s", color=C_TAIL, lw=2, ms=6,
         label="TAIL $\\Delta$ (trend-free, $\\rho_s=-0.14$ n.s.): density REFUTED cause")
axB.axhline(0, color="black", lw=0.8, ls=":")
# MI native tail bar (the bar no thinned rung reaches)
axB.axhline(0.000335, color=C_WIN, lw=1.3, ls="--",
            label="MI native tail $\\Delta=+0.000335$ (5/5) -- not reached by thinning")
axB.annotate("MI-equivalent\nglobal density\n($\\rho=0.66$)", xy=(0.66, -0.000108),
             xytext=(0.70, -0.00060), fontsize=7.5, ha="center",
             arrowprops=dict(arrowstyle="->", lw=0.8))
axB.set_xlabel("interaction-thinning  $\\rho$  (1.0 = full VG  $\\rightarrow$  0.66 = MI global density)")
axB.set_ylabel("$\\Delta$NDCG@10  (text $-$ ID)")
axB.set_title("(B) Interaction-density titration\n(head cause / tail refuted -- a double result)")
axB.invert_xaxis()
axB.legend(fontsize=6.6, loc="upper left", framealpha=0.92)
axB.grid(alpha=0.3)

# ================================================================== Panel C
# 5.4.1 + 5.4.2: tail & head text/ID ratio across the four mechanism regimes.
# interaction-thinning leaves the tail ratio FLAT (0.971->0.971); user-thinning
# (= lower connectivity, full histories kept) LIFTS it 0.971->1.046 toward MI's
# 1.276 => connectivity is a confirmed PARTIAL tail cause.
axC = axes[2]
regimes = ["VG full\n(ipi 24.5,\nu/i 3.70)",
           "VG int-thin\n$\\rho$=0.66\n(16.2, ~3.4)",
           "VG user-thin\n$\\rho_u$=0.66\n(16.1, 2.44)",
           "MI native\n(16.2, 2.34)"]
tailR = [0.971, 0.971, 1.046, 1.276]
headR = [1.026, 1.049, 1.039, 1.101]
xc = np.arange(len(regimes))
axC.plot(xc, tailR, "-s", color=C_TAIL, lw=2, ms=8, label="TAIL text/ID ratio")
axC.plot(xc, headR, "-o", color=C_HEAD, lw=2, ms=7, label="HEAD text/ID ratio")
axC.axhline(1.0, color="black", lw=0.9, ls=":")
for xi, r in zip(xc, tailR):
    axC.text(xi, r + 0.012, f"{r:.3f}", ha="center", fontsize=8, color=C_TAIL,
             fontweight="bold")
# annotate the two mechanism arrows
axC.annotate("", xy=(1, 0.971), xytext=(0, 0.971),
             arrowprops=dict(arrowstyle="-|>", color=C_NULL, lw=2))
axC.text(0.5, 0.945, "interaction-thinning:\ntail FLAT (density refuted)",
         ha="center", fontsize=7, color=C_NULL)
axC.annotate("", xy=(3, 1.276), xytext=(1, 0.971),
             arrowprops=dict(arrowstyle="-|>", color=C_WIN, lw=2))
axC.text(2.15, 1.18, "user-thinning $\\rightarrow$ MI:\nconnectivity LIFTS tail\n(dd +0.000326, t=3.47,\nCI excl 0)",
         ha="center", fontsize=7, color=C_WIN)
axC.set_xticks(xc)
axC.set_xticklabels(regimes, fontsize=7.5)
axC.set_ylabel("text-arm / ID-arm  tail (or head) NDCG@10 ratio")
axC.set_title("(C) Two-axis decomposition\n(connectivity binds the tail, not count)")
axC.set_ylim(0.93, 1.32)
axC.legend(fontsize=8, loc="upper left")
axC.grid(alpha=0.3)

fig.suptitle(
    "Dataset-conditional long-tail law and its two-axis causal decomposition "
    "(AR2023 5-core LLOO, full-catalog, NDCG@10; all values 5-seed best-by-val "
    "except Beauty 2-3 seed)",
    fontsize=10.5, y=1.04)

png = OUT / "fig_tail_law_mechanism.png"
pdf = OUT / "fig_tail_law_mechanism.pdf"
fig.savefig(png)
fig.savefig(pdf)
print("WROTE", png)
print("WROTE", pdf)
