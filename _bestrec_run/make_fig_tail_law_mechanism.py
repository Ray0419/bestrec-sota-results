#!/usr/bin/env python
"""
Generate Figure 1: (A) TFV2 repaired-estimand tail contrasts (single estimand,
Welch 95% CIs, 8 fresh seeds/arm; source TFV2_ADJUDICATION.md; outcome-visible
campaign) and (B-C) exploratory one-fixed-draw titration/ratio panels (5-seed
summaries; descriptive; no draw uncertainty). Historical Table-1d values are
NOT plotted (the table prints them). A machine-readable provenance CSV is
emitted beside the figure. Panel B/C values are typeset from the locked tables
in the canonical paper (5.4 / 5.4.1-5.4.2).
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
    "axes.titlesize": 9,
    "axes.titleweight": "bold",
    "figure.dpi": 140,
    "savefig.bbox": "tight",
})

fig, axes = plt.subplots(3, 1, figsize=(7.0, 11.4))

# ================================================================== Panel A
# TFV2 forest (audit 2026-07-22 11:48 C1: ONE estimand per panel -- all three rows
# are TFV2 tie-safe positive-frequency-tail Welch contrasts, 8 fresh seeds/arm,
# zero-exposure separated; verbatim source: TFV2_ADJUDICATION.md. The historical
# defective-cohort Table-1d values are NOT plotted (the table prints them).
axA = axes[0]
rows = [
    # label, estimate, ci_lo, ci_hi, note
    ("MI  text$-$ID tail\n(8v8, freq-5-heavy)", 0.000420, 0.000181, 0.000660,
     "p = 0.0022  Holm-PASS"),
    ("VG  text$-$ID tail\n(8v8)", 0.000173, -0.000065, 0.000411, "p = 0.14  n.s."),
    ("MI$-$VG interaction\n(four-arm)", 0.000247, -0.000076, 0.000570,
     "p = 0.13  n.s.\nheterogeneity NOT established"),
]
yA = np.arange(len(rows))[::-1]
for (lab, est, lo, hi, note), y in zip(rows, yA):
    col = C_WIN if lo > 0 else C_NULL
    axA.errorbar(est, y, xerr=[[est - lo], [hi - est]], fmt="s", color=col,
                 ms=7, capsize=4, elinewidth=1.4)
    axA.text(hi + 0.00004, y, note, va="center", fontsize=7.2, color=col)
    axA.text(est, y - 0.30, f"{est:+.6f}", ha="center", va="top", fontsize=7.2)
axA.axvline(0, color="black", lw=0.9, ls=":")
axA.set_ylim(-0.75, 2.45)
axA.set_yticks(yA)
axA.set_yticklabels([r[0] for r in rows], fontsize=8)
axA.set_xlabel("tie-safe positive-frequency-tail  $\\Delta$NDCG@10  (Welch 95% CI)")
axA.set_title("(A) TFV2 repaired-estimand tail contrasts (one estimand; outcome-visible campaign)\n"
              "provenance: TFV2_ADJUDICATION.md; cohorts tfv2_cohorts_*.json; data CSV alongside this figure")
axA.set_xlim(-0.00035, 0.00125)
axA.grid(axis="x", alpha=0.3)

# ================================================================== Panel B
# 5.4 titration ladder: head Delta rank-trend vs density (level contrasts,
# one fixed subset draw); tail Delta trend-free. x = thinning rho (1.0 -> 0.66).
axB = axes[1]
rho     = [1.00, 0.94, 0.91, 0.88, 0.78, 0.66]
headD   = [0.00221, 0.00239, 0.00254, 0.00252, 0.00266, 0.00354]
tailDl  = [-0.000148, 0.000165, 0.000039, 0.000537, 0.000056, -0.000108]
axB.plot(rho, headD, "-o", color=C_HEAD, lw=2, ms=6,
         label="HEAD $\\Delta$ (overall rank trend $\\rho_s=-0.94$; one reversal;\none fixed subset draw): head tracks thinning")
axB.plot(rho, tailDl, "-s", color=C_TAIL, lw=2, ms=6,
         label="TAIL $\\Delta$ (trend-free, $\\rho_s=-0.14$ n.s.): tail does not")
axB.axhline(0, color="black", lw=0.8, ls=":")
# MI native tail bar (the bar no thinned rung reaches)
axB.axhline(0.000335, color=C_WIN, lw=1.3, ls="--",
            label="MI native tail $\\Delta=+0.000335$ (5/5) -- not reached by thinning")
axB.annotate("MI-equivalent\nglobal density\n($\\rho=0.66$)", xy=(0.66, -0.000108),
             xytext=(0.735, 0.00095), fontsize=7.5, ha="center",
             arrowprops=dict(arrowstyle="->", lw=0.8))
axB.set_xlabel("interaction-thinning  $\\rho$  (1.0 = full VG  $\\rightarrow$  0.66 = MI global density)")
axB.set_ylabel("$\\Delta$NDCG@10  (text $-$ ID)")
axB.set_title("(B) Interaction-density titration\n(head tracks thinning / tail does not -- level contrasts)")
axB.invert_xaxis()
axB.legend(fontsize=6.6, loc="upper left", framealpha=0.92)
axB.grid(alpha=0.3)

# ================================================================== Panel C
# 5.4.1 + 5.4.2: tail & head text/ID ratio across the four regimes (descriptive;
# one fixed draw; the user-thinning shift is suggestive only, p=.058 CI incl 0 --
# no cause is asserted).
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
             arrowprops=dict(arrowstyle="-", color=C_NULL, lw=1.2, ls="--"))
axC.text(0.5, 0.945, "interaction-thinning:\ntail FLAT (no crossing)",
         ha="center", fontsize=7, color=C_NULL)
axC.annotate("", xy=(3, 1.276), xytext=(1, 0.971),
             arrowprops=dict(arrowstyle="-", color=C_WIN, lw=1.2, ls="--"))
axC.text(1.62, 1.205, "user-thinning $\\rightarrow$ MI:\ntail moves toward MI\n(dd +0.000326; suggestive,\np=0.058, CI incl 0)",
         ha="center", fontsize=7, color=C_WIN)
axC.set_xticks(xc)
axC.set_xticklabels(regimes, fontsize=7.5)
axC.set_ylabel("text-arm / ID-arm  tail (or head) NDCG@10 ratio")
axC.set_title("(C) Two-axis descriptive contrast\n(user-thinned point shifts positive (sugg.); count-thinned does not)")
axC.set_ylim(0.93, 1.32)
axC.legend(fontsize=8, loc="upper left")
axC.grid(alpha=0.3)

fig.tight_layout(pad=1.4, h_pad=2.6, rect=(0, 0, 1, 0.945))
fig.suptitle(
    "The MI frequency-5 tail case and its two-axis descriptive contrast\n"
    "(A: TFV2, 8 independent seeds/arm, outcome-visible; B-C: one fixed subset draw,\n"
    "5-seed summaries, no draw uncertainty; heterogeneity not established, p = 0.13; AR2023 5-core LLOO, NDCG@10)",
    fontsize=10.5, y=0.995)

png = OUT / "fig_tail_law_mechanism.png"
pdf = OUT / "fig_tail_law_mechanism.pdf"
fig.savefig(png)
fig.savefig(pdf)
print("WROTE", png)
print("WROTE", pdf)

# machine-readable figure provenance (audit 2026-07-22 11:48 C1)
import hashlib
csv = OUT / "fig_tail_law_mechanism_data.csv"
code_hash = hashlib.sha256(open(__file__, "rb").read()).hexdigest()[:16]
with open(csv, "w", encoding="utf-8", newline="\n") as f:
    f.write("panel,series,label,x,estimate,ci_lo,ci_hi,n_per_arm,estimator,analysis_id\n")
    for (lab, est, lo, hi, note) in rows:
        f.write(f"A,tfv2_forest,\"{lab.replace(chr(10), ' ')}\",,"
                f"{est},{lo},{hi},8,Welch-95CI-tie-safe-tail,TFV2_ADJUDICATION.md\n")
    for r, h, t in zip(rho, headD, tailDl):
        f.write(f"B,head_delta,,{r},{h},,,5,level-contrast-one-draw,S5.4-titration\n")
        f.write(f"B,tail_delta,,{r},{t},,,5,level-contrast-one-draw,S5.4-titration\n")
    for reg, tr, hr2 in zip(regimes, tailR, headR):
        f.write(f"C,tail_ratio,\"{reg.replace(chr(10), ' ')}\",,{tr},,,5,"
                f"ratio-descriptive-one-draw,S5.4.1-5.4.2\n")
        f.write(f"C,head_ratio,\"{reg.replace(chr(10), ' ')}\",,{hr2},,,5,"
                f"ratio-descriptive-one-draw,S5.4.1-5.4.2\n")
    f.write(f"#,generator_sha256_16,{code_hash},,,,,,,\n")
print("WROTE", csv, "| generator hash", code_hash)
