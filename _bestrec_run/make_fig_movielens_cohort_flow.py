"""Render the frozen MovieLens cohort construction from public aggregates."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch


ROOT = Path(__file__).resolve().parent.parent
RUN = ROOT / "_bestrec_run"
OUT = ROOT / "figures"
ADJ = RUN / "fir_efficiency_ml1m_v1_adjudication.json"
VIEWS = ("MovieLens1M_R4", "MovieLens1M_ALL")


def main() -> int:
    adjud = json.loads(ADJ.read_text(encoding="utf-8"))
    if (adjud.get("protocol") != "PREREG_FIR_EFFICIENCY_ML1M_V1"
            or adjud.get("verdict") != "ML1M-NO-FIR-REPLICATION"
            or adjud.get("not_independent_confirmation") is not True):
        raise RuntimeError("unexpected MovieLens adjudication")
    provenance = adjud["data_provenance"]
    views = provenance["views"]
    rows = []
    for name in VIEWS:
        record = views[name]
        rows.append({
            "view": name,
            "minimum_rating": int(record["minimum_rating"]),
            "time_fraction": float(record["time_fraction"]),
            "cutoff_timestamp_s": int(record["cutoff_timestamp_s"]),
            "filtered_events": int(record["n_filtered_events"]),
            "candidate_users": int(record["n_candidate_users"]),
            "retained_users": int(record["n_users"]),
            "train_catalog_items": int(record["n_train_catalog_items"]),
            "train_rows": int(record["n_rows"]["train"]),
            "valid_rows": int(record["n_rows"]["valid"]),
            "test_rows": int(record["n_rows"]["test"]),
        })

    OUT.mkdir(exist_ok=True)
    csv_path = OUT / "fig_movielens_cohort_flow_data.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    plt.rcParams.update({
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "font.size": 8.2,
        "figure.dpi": 180,
    })
    fig, ax = plt.subplots(figsize=(9.5, 3.4))
    ax.set_xlim(0, 12.2)
    ax.set_ylim(0, 5.25)
    ax.axis("off")

    def box(x: float, y: float, w: float, h: float, text: str,
            face: str, edge: str, fontsize: float = 7.7) -> None:
        patch = FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.025,rounding_size=0.07",
            facecolor=face, edgecolor=edge, linewidth=1.0,
        )
        ax.add_patch(patch)
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
                fontsize=fontsize, linespacing=1.25)

    def arrow(x1: float, y1: float, x2: float, y2: float, color: str) -> None:
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops={"arrowstyle": "-|>", "lw": 1.05,
                                "color": color, "shrinkA": 2, "shrinkB": 2})

    source_face, source_edge = "#f2f2f2", "#5b5b5b"
    box(0.05, 2.0, 1.75, 1.35,
        "Official ML-1M\n1,000,209 ratings\n6,040 users",
        source_face, source_edge, 8.0)

    lanes = [
        (rows[0], 3.35, "Primary: rating >= 4", "#eaf2fb", "#2166ac"),
        (rows[1], 1.05, "Sensitivity: all ratings", "#f4edf7", "#762a83"),
    ]
    for row, y, lane_title, face, edge in lanes:
        ax.text(2.0, y + 1.17, lane_title, color=edge, fontweight="bold",
                fontsize=8.7)
        box(2.0, y, 1.65, 0.95,
            f'View filter\n{row["filtered_events"]:,} events', face, edge)
        box(4.0, y, 2.05, 0.95,
            (f'90% global-time boundary\n{row["candidate_users"]:,} candidates\n'
             '>=6 pre | >=1 post'), face, edge, 6.9)
        box(6.4, y, 2.15, 0.95,
            (f'Fixed-point user/catalog\nfilter\n{row["retained_users"]:,} users | '
             f'{row["train_catalog_items"]:,} items'), face, edge, 6.9)
        box(8.9, y, 3.15, 0.95,
            (f'Final rows\n{row["train_rows"]:,} TRAIN\n'
             f'{row["valid_rows"]:,} VALID | {row["test_rows"]:,} TEST'),
            face, edge, 6.9)
        yc = y + 0.475
        arrow(1.8, 2.675, 2.0, yc, edge)
        arrow(3.65, yc, 4.0, yc, edge)
        arrow(6.05, yc, 6.4, yc, edge)
        arrow(8.55, yc, 8.9, yc, edge)

    ax.set_title(
        "MovieLens 1M cohort construction under the frozen global-time protocol",
        fontsize=10.6, fontweight="bold", pad=8,
    )
    ax.text(
        6.1, 0.18,
        "The primary cohort is conditional on eligible pre-cutoff history and a training-observed item catalog; it is not a random sample of all users or movies.",
        ha="center", va="bottom", fontsize=7.25, color="#444444",
    )
    fig.tight_layout(rect=(0.005, 0.07, 0.995, 0.96))

    png_path = OUT / "fig_movielens_cohort_flow.png"
    pdf_path = OUT / "fig_movielens_cohort_flow.pdf"
    fig.savefig(png_path, bbox_inches="tight", metadata={"Software": "matplotlib"})
    fig.savefig(pdf_path, bbox_inches="tight", metadata={
        "Creator": "make_fig_movielens_cohort_flow.py",
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
