#!/usr/bin/env python
"""Render the outcome-known Software V3 paired-seed result.

The figure is generated only from the committed adjudication record.  It is a
transparent visualization of the eight registered matched-seed observations,
not an additional analysis or an upgrade of the manuscript evidence class.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent.parent
RUN = ROOT / "_bestrec_run"
OUT = ROOT / "figures"
ADJ = RUN / "fir_prospective_sw_v3_adjudication.json"


def main() -> int:
    adjud = json.loads(ADJ.read_text(encoding="utf-8"))
    if adjud.get("protocol") != "PREREG_FIR_PROSPECTIVE_SW_V3":
        raise RuntimeError("unexpected Software V3 protocol")
    seeds = np.asarray(adjud["seeds"], dtype=int)
    identity = np.asarray(adjud["values"]["identity"], dtype=float)
    learned = np.asarray(adjud["values"]["learned"], dtype=float)
    delta = learned - identity
    recorded = np.asarray(adjud["primary_contrast"]["per_seed"], dtype=float)
    if not np.array_equal(delta, recorded):
        raise RuntimeError("paired differences drift from adjudication record")
    mean = float(adjud["primary_contrast"]["mean"])
    low, high = map(float, adjud["primary_contrast"]["ci95"])
    threshold = float(adjud["practical_threshold"])

    OUT.mkdir(exist_ok=True)
    csv_path = OUT / "fig_software_v3_pairs_data.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(
            fp,
            fieldnames=["seed", "identity_ndcg10", "learned_ndcg10", "delta_ndcg10"],
        )
        writer.writeheader()
        for seed, ident, learn, diff in zip(seeds, identity, learned, delta):
            writer.writerow({
                "seed": int(seed),
                "identity_ndcg10": f"{ident:.12f}",
                "learned_ndcg10": f"{learn:.12f}",
                "delta_ndcg10": f"{diff:.12f}",
            })

    plt.rcParams.update({
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "font.size": 9.2,
        "axes.titlesize": 10.2,
        "axes.labelsize": 9.2,
        "figure.dpi": 180,
    })
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.35))

    # Panel A: exact matched observations.
    for ident, learn in zip(identity, learned):
        axes[0].plot([0, 1], [ident, learn], color="#7f8c8d", alpha=0.65, lw=0.9)
        axes[0].scatter(0, ident, color="#2166ac", s=24, zorder=3)
        axes[0].scatter(1, learn, color="#b2182b", s=24, zorder=3)
    axes[0].set_xticks([0, 1], ["Identity", "Learned FIR"])
    axes[0].set_ylabel("sealed TEST NDCG@10")
    axes[0].set_title("A. Matched seed blocks")
    axes[0].grid(axis="y", alpha=0.22)

    # Panel B: every paired difference plus the registered mean interval.
    y = np.arange(1, len(seeds) + 1)
    axes[1].axvline(0.0, color="#555555", lw=0.9, label="zero")
    axes[1].axvline(threshold, color="#d97706", lw=1.0, ls="--",
                    label="+0.000500 reporting threshold")
    axes[1].scatter(delta, y, color="#542788", s=28, zorder=3,
                    label="paired seed difference")
    mean_y = len(seeds) + 1.15
    axes[1].errorbar(mean, mean_y, xerr=[[mean - low], [high - mean]],
                     fmt="D", color="#1b7837", capsize=3.5, ms=5.2,
                     label="mean and ordinary 95% paired-t CI")
    axes[1].set_yticks(list(y) + [mean_y],
                       [str(s)[-2:] for s in seeds] + ["Mean"])
    axes[1].set_xlabel("learned FIR - identity NDCG@10")
    axes[1].set_ylabel("seed suffix")
    axes[1].set_title("B. Registered paired differences")
    axes[1].grid(axis="x", alpha=0.22)
    axes[1].legend(frameon=False, fontsize=7.4, loc="upper left")

    fig.suptitle(
        "Software V3: outcome-known same-team robustness (8 matched seeds)",
        fontsize=10.8,
        fontweight="bold",
    )
    fig.text(
        0.5,
        -0.005,
        "All points are registered sealed endpoints. Evidence class: exploratory; not independent confirmation.",
        ha="center",
        fontsize=7.8,
        color="#444444",
    )
    fig.tight_layout(rect=(0, 0.06, 1, 0.94))

    png_path = OUT / "fig_software_v3_pairs.png"
    pdf_path = OUT / "fig_software_v3_pairs.pdf"
    fig.savefig(png_path, bbox_inches="tight", metadata={"Software": "matplotlib"})
    fig.savefig(
        pdf_path,
        bbox_inches="tight",
        metadata={
            "Creator": "make_fig_software_v3_pairs.py",
            "CreationDate": None,
            "ModDate": None,
        },
    )
    plt.close(fig)
    print(f"WROTE {csv_path}")
    print(f"WROTE {png_path}")
    print(f"WROTE {pdf_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
