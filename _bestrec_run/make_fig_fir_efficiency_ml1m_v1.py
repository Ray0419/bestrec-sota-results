#!/usr/bin/env python
"""Render the aggregate MovieLens 1M FIR efficiency result.

The figure and its CSV are derived only from the public aggregate adjudication.
MovieLens rows, checkpoints, endpoint files, and per-user sidecars remain private
under the ML-1M README and are neither read nor emitted here.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent.parent
RUN = ROOT / "_bestrec_run"
OUT = ROOT / "figures"
ADJ = RUN / "fir_efficiency_ml1m_v1_adjudication.json"
ARMS = ("identity", "shared", "grouped", "lowrank", "learned", "pointwise")
COLORS = {
    "identity": "#4d4d4d",
    "shared": "#1b9e77",
    "grouped": "#66a61e",
    "lowrank": "#7570b3",
    "learned": "#d95f02",
    "pointwise": "#1f78b4",
}


def main() -> int:
    adjud = json.loads(ADJ.read_text(encoding="utf-8"))
    if (adjud.get("protocol") != "PREREG_FIR_EFFICIENCY_ML1M_V1"
            or adjud.get("verdict") != "ML1M-NO-FIR-REPLICATION"
            or adjud.get("not_independent_confirmation") is not True):
        raise RuntimeError("unexpected MovieLens FIR efficiency adjudication")

    params = adjud["filter_trainable_parameters"]
    means = adjud["primary_means"]
    resources = adjud["resource_summary"]["MovieLens1M_R4"]
    rows = []
    for arm in ARMS:
        resource = resources[arm]
        rows.append({
            "arm": arm,
            "filter_trainable_params": int(params[arm]),
            "mean_ndcg10": float(means[arm]),
            "flops_per_user_median": float(resource["flops_per_user_median"]),
            "latency_ms_median": float(resource["latency_ms_median_across_seeds"]),
            "inference_peak_mib_median":
                float(resource["inference_peak_cuda_memory_bytes_median"]) / 2**20,
            "training_peak_mib_median":
                float(resource["training_peak_cuda_memory_bytes_median"]) / 2**20,
            "training_wall_time_s_median":
                float(resource["training_wall_time_s_median"]),
        })

    OUT.mkdir(exist_ok=True)
    csv_path = OUT / "fig_fir_efficiency_ml1m_v1_data.csv"
    fields = list(rows[0])
    with csv_path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "arm": row["arm"],
                "filter_trainable_params": row["filter_trainable_params"],
                "mean_ndcg10": f'{row["mean_ndcg10"]:.12f}',
                "flops_per_user_median": f'{row["flops_per_user_median"]:.1f}',
                "latency_ms_median": f'{row["latency_ms_median"]:.12f}',
                "inference_peak_mib_median":
                    f'{row["inference_peak_mib_median"]:.12f}',
                "training_peak_mib_median":
                    f'{row["training_peak_mib_median"]:.12f}',
                "training_wall_time_s_median":
                    f'{row["training_wall_time_s_median"]:.12f}',
            })

    plt.rcParams.update({
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "font.size": 8.7,
        "axes.titlesize": 9.6,
        "axes.labelsize": 8.8,
        "figure.dpi": 180,
    })
    fig, axes = plt.subplots(1, 3, figsize=(7.25, 2.85), sharey=True)
    x_fields = (
        ("filter_trainable_params", "Filter parameters", "symlog"),
        ("latency_ms_median", "Median latency (ms/user)", None),
        ("training_peak_mib_median", "Training peak CUDA memory (MiB)", None),
    )
    annotation_offsets = {
        "filter_trainable_params": {
            "shared": (3, 3), "lowrank": (3, 3), "learned": (3, 3),
        },
        "latency_ms_median": {
            "identity": (3, 5), "learned": (3, -12), "shared": (3, 3),
            "lowrank": (-37, -12), "pointwise": (3, 3), "grouped": (3, 3),
        },
        "training_peak_mib_median": {
            "identity": (3, 5), "learned": (3, -12), "shared": (3, 3),
            "lowrank": (-37, -12), "pointwise": (3, 3), "grouped": (3, 3),
        },
    }
    for ax, (field, label, scale) in zip(axes, x_fields):
        for row in rows:
            arm = row["arm"]
            ax.scatter(row[field], row["mean_ndcg10"], s=34,
                       color=COLORS[arm], edgecolor="white", linewidth=0.45,
                       zorder=3)
            ax.annotate(arm, (row[field], row["mean_ndcg10"]),
                        xytext=annotation_offsets.get(field, {}).get(arm, (3, 3)),
                        textcoords="offset points", fontsize=6.8)
        if scale:
            ax.set_xscale(scale, linthresh=1)
        ax.set_xlabel(label)
        ax.grid(alpha=0.22)
    axes[0].set_ylabel("Primary mean NDCG@10")
    axes[0].set_title("A. Accuracy vs size")
    axes[1].set_title("B. Accuracy vs latency")
    axes[2].set_title("C. Accuracy vs training memory")
    fig.suptitle(
        "MovieLens 1M R4: aggregate FIR accuracy-resource plane (8 matched seeds)",
        fontsize=10.3,
        fontweight="bold",
    )
    fig.text(
        0.5, -0.015,
        "Learned FIR did not replicate versus identity or pointwise; resource readings are descriptive on one GPU.",
        ha="center", fontsize=7.4, color="#444444",
    )
    fig.tight_layout(rect=(0, 0.07, 1, 0.91), w_pad=1.15)

    png_path = OUT / "fig_fir_efficiency_ml1m_v1.png"
    pdf_path = OUT / "fig_fir_efficiency_ml1m_v1.pdf"
    fig.savefig(png_path, bbox_inches="tight", metadata={"Software": "matplotlib"})
    fig.savefig(pdf_path, bbox_inches="tight", metadata={
        "Creator": "make_fig_fir_efficiency_ml1m_v1.py",
        "CreationDate": None,
        "ModDate": None,
    })
    plt.close(fig)
    print(f"WROTE {csv_path}")
    print(f"WROTE {png_path}")
    print(f"WROTE {pdf_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
