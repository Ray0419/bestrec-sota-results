#!/usr/bin/env python
"""
Generate the dedicated (R1, R2) connectivity-vs-count "Tilman plane" scatter --
the second of the two figures the supervisor (cycle-11, 2026-06-21) flagged as
still outstanding (the first, the 3-panel tail-law/mechanism figure, was rendered
2026-06-21 by `make_fig_tail_law_mechanism.py`; the BBP-irreducibility figure
remains outstanding and is NOT produced here).

This typesets the matched-R1 double dissociation (PAPER_DRAFT.md sections 5.4.1 +
5.4.2) in its native 2-D form. The two resource axes:
  R1 = interactions / item  (interaction COUNT / global density)
  R2 = users / item         (collaborative CONNECTIVITY)
The plane makes the load-bearing causal point visual: thinning VG along R1 to MI's
exact density (interaction-mode rho=0.66) keeps the tail a NULL, but thinning VG
along R2 to MI's connectivity (user-mode rho_user=0.66) at the SAME R1 flips the
tail POSITIVE -- so the binding tail resource is connectivity (R2), not count (R1).

ALL coordinates and verdicts are hard-coded from the LOCKED, 3x-supervisor-audited
tables in PAPER_DRAFT.md (5.3 Table 1d; 5.4.1 ratio table lines 322-326; 5.4.2
user-mode table; dataset sizes line 170). NOTHING is recomputed -- this is
typesetting of already-locked, leak-free, best-by-val paired text-ID results
(AR2023 5-core LLOO, full-catalog masked eval, n_eval=94,762, tail_n=10,900 frozen
on the VG runs). Produced by the EXPERIMENT agent as sanctioned CPU-only
paper-finishing work (supervisor cycle-11), zero GPU contention.

Attribution: HSTU=Zhai 2024; causal spectral filter adapted leak-free from
FMLP/Zhou 2022 + BSARec/Shin 2024; text stack (SBERT features / text-sim bias /
TAPE prototypes)=Hou 2024 / Liu 2025 (arXiv:2504.10545); SASRec=Kang & McAuley
2018; label smoothing=Szegedy 2016. The (R1,R2) resource-plane framing is an
analogical borrowing from Tilman's resource-ratio theory in ecology (cited as a
framing device, not a claimed method); Beauty interactions/item = 5.17M / 207,649
items = 24.9 (PAPER_DRAFT.md line 170).
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "figures"
OUT.mkdir(exist_ok=True)

C_WIN = "#2ca02c"   # tail text-WIN
C_NULL = "#7f7f7f"  # tail null
C_USR = "#1f77b4"   # user-thin (connectivity) intervention arrow
C_INT = "#d62728"   # interaction-thin (count) intervention arrow

plt.rcParams.update({
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
    "figure.dpi": 140,
    "savefig.bbox": "tight",
})

# point = (label, R1 interactions/item, R2 users/item, tail ratio, tail Delta,
#          pos-seed string, verdict-colour, marker)
PTS = [
    ("VG full\n(natural)",            24.5, 3.70, 0.971, -0.000148, "2/5", C_NULL, "s"),
    ("Beauty native\n(natural)",      24.9, 3.51, None,  -0.000018, "0/2", C_NULL, "s"),
    ("VG int-thin\n$\\rho$=0.66",     16.2, 3.40, 0.971, -0.000108, "1/5", C_NULL, "o"),
    ("VG user-thin\n$\\rho_u$=0.66",  16.1, 2.44, 1.046, +0.000178, "5/5", C_WIN,  "o"),
    ("MI native\n(natural)",          16.2, 2.34, 1.276, +0.000335, "5/5", C_WIN,  "D"),
]

fig, ax = plt.subplots(figsize=(8.2, 6.4))

# ---- shaded connectivity bands (R2 axis is the binding tail resource) --------
ax.axhspan(2.0, 2.55, color=C_WIN, alpha=0.07, zorder=0)
ax.axhspan(3.30, 3.95, color=C_NULL, alpha=0.07, zorder=0)
ax.text(27.6, 2.40, "low connectivity\n(R2 $\\lesssim$ 2.5)\n$\\Rightarrow$ text WINS tail",
        ha="right", va="center", fontsize=8.5, color=C_WIN, fontweight="bold")
ax.text(27.6, 3.62, "high connectivity\n(R2 $\\gtrsim$ 3.5)\n$\\Rightarrow$ tail NULL",
        ha="right", va="center", fontsize=8.5, color=C_NULL, fontweight="bold")

# ---- the matched-R1 vertical: same count (R1~16.2), different connectivity ----
ax.plot([16.15, 16.15], [2.44, 3.40], color="black", lw=1.0, ls=":", zorder=1)

# interaction-thinning arrow: VG full -> VG int-thin (drops R1, holds R2) = NULL
ax.annotate("", xy=(16.2, 3.40), xytext=(24.5, 3.70),
            arrowprops=dict(arrowstyle="-|>", color=C_INT, lw=2.2,
                            connectionstyle="arc3,rad=0.08"), zorder=2)
ax.text(20.3, 3.74, "interaction-thinning\n(R1 $\\downarrow$, R2 held)\ntail stays NULL",
        ha="center", va="bottom", fontsize=8, color=C_INT)

# user-thinning arrow: VG full -> VG user-thin (drops R2 at matched R1) = WIN
ax.annotate("", xy=(16.1, 2.44), xytext=(24.5, 3.70),
            arrowprops=dict(arrowstyle="-|>", color=C_USR, lw=2.2,
                            connectionstyle="arc3,rad=-0.18"), zorder=2)
ax.text(21.6, 2.78, "user-thinning\n(R2 $\\downarrow$ at matched R1)\ntail FLIPS positive\n(dd +0.000326, t=3.47,\nCI excl 0)",
        ha="center", va="center", fontsize=8, color=C_USR)

# ---- scatter points ----------------------------------------------------------
for lbl, r1, r2, ratio, dlt, pf, col, mk in PTS:
    ax.scatter([r1], [r2], s=230, c=col, marker=mk, edgecolors="black",
               linewidths=1.2, zorder=5)
    ratio_s = f"ratio {ratio:.3f}" if ratio is not None else "ratio n/a"
    dy = 0.10 if r2 < 3.0 else -0.10
    va = "bottom" if dy > 0 else "top"
    ax.annotate(f"{lbl}\n$\\Delta$={dlt:+.6f} ({pf})\n{ratio_s}",
                xy=(r1, r2), xytext=(r1, r2 + dy),
                ha="center", va=va, fontsize=7.6)

ax.set_xlabel("R1 = interactions / item  (count / global density)  $\\rightarrow$ denser")
ax.set_ylabel("R2 = users / item  (collaborative connectivity)  $\\rightarrow$ more connected")
ax.set_title("The (R1, R2) resource plane: connectivity (R2), not count (R1),\n"
             "binds the long-tail text advantage")
ax.set_xlim(13.5, 28.0)
ax.set_ylim(2.05, 3.95)
ax.grid(alpha=0.3)

# legend proxies
from matplotlib.lines import Line2D
leg = [
    Line2D([0], [0], marker="o", color="w", markerfacecolor=C_WIN,
           markeredgecolor="black", markersize=11, label="tail text-WIN (CI excl 0 / sign 5/5)"),
    Line2D([0], [0], marker="o", color="w", markerfacecolor=C_NULL,
           markeredgecolor="black", markersize=11, label="tail NULL (powered)"),
    Line2D([0], [0], color=C_INT, lw=2.2, label="interaction-thin (R1$\\downarrow$): tail-inert"),
    Line2D([0], [0], color=C_USR, lw=2.2, label="user-thin (R2$\\downarrow$): tail-binding"),
]
ax.legend(handles=leg, fontsize=8, loc="lower left", framealpha=0.93)

fig.text(0.5, -0.02,
         "AR2023 5-core LLOO, full-catalog NDCG@10; VG runs 5-seed best-by-val "
         "(n_eval=94,762, tail_n=10,900 frozen), Beauty 2-3 seed. The two VG "
         "thinned points share R1$\\approx$16.2 (matched count) but differ in R2; "
         "only the R2-thinned point crosses to a tail win, beside MI.",
         ha="center", fontsize=7.6, color="#444444")

png = OUT / "fig_r1r2_plane.png"
pdf = OUT / "fig_r1r2_plane.pdf"
fig.savefig(png)
fig.savefig(pdf)
print("WROTE", png)
print("WROTE", pdf)
