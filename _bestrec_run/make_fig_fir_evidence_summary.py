"""Render a bounded summary of the released FIR contrast evidence.

This figure is a visual index of already adjudicated contrasts. It does not
pool estimates, define a new multiplicity family, or upgrade any evidence
class. In particular, the Amazon campaigns are outcome-known internal work,
whereas MovieLens is a prospectively frozen same-investigator transfer test.
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


def load(name: str) -> dict:
    return json.loads((RUN / name).read_text(encoding="utf-8"))


def add_row(rows: list[dict], *, group: str, label: str, estimate: float,
            interval: list[float], source_file: str, source_key: str,
            evidence_scope: str, color: str, marker: str) -> None:
    low, high = map(float, interval)
    estimate = float(estimate)
    if not low <= estimate <= high:
        raise RuntimeError(f"estimate outside interval for {label}")
    rows.append({
        "group": group,
        "label": label,
        "estimate": estimate,
        "ci_low": low,
        "ci_high": high,
        "source_file": source_file,
        "source_key": source_key,
        "evidence_scope": evidence_scope,
        "color": color,
        "marker": marker,
    })


def main() -> int:
    mi = load("fir_v3_adjudication.json")
    breadth = load("fir_canonical_breadth_adjudication.json")
    controls = load("fir_controls_adjudication.json")
    pointwise = load("fir_pointwise_v1_adjudication.json")
    software = load("fir_prospective_sw_v3_adjudication.json")
    ml1m = load("fir_efficiency_ml1m_v1_adjudication.json")

    if mi.get("verdict") != "W-POS":
        raise RuntimeError("unexpected MI V3 adjudication")
    if breadth.get("verdict") != "CANON-BREADTH-POS":
        raise RuntimeError("unexpected canonical breadth adjudication")
    if (controls.get("protocol") != "PREREG_FIR_CONTROLS"
            or controls.get("verdict") != "CTRL-ACTIVE-CONTROL-SUPPORTED"):
        raise RuntimeError("unexpected active-control adjudication")
    if (pointwise.get("protocol") != "PREREG_FIR_POINTWISE_V1"
            or pointwise.get("verdict") != "POINTWISE-FIR-DISCRIMINATED"):
        raise RuntimeError("unexpected pointwise adjudication")
    if (software.get("protocol") != "PREREG_FIR_PROSPECTIVE_SW_V3"
            or software.get("verdict") != "SW-V3-PRACTICAL-POS"):
        raise RuntimeError("unexpected Software V3 adjudication")
    if (ml1m.get("protocol") != "PREREG_FIR_EFFICIENCY_ML1M_V1"
            or ml1m.get("verdict") != "ML1M-NO-FIR-REPLICATION"
            or ml1m.get("not_independent_confirmation") is not True):
        raise RuntimeError("unexpected MovieLens adjudication")

    primary = next(
        row for row in mi["contrasts"] if row["contrast"] == "A1-A0 (PRIMARY)"
    )
    rows: list[dict] = []
    amazon = "Outcome-known internal Amazon"
    add_row(
        rows, group=amazon, label="MI: learned - identity",
        estimate=primary["est"], interval=primary["ci"],
        source_file="fir_v3_adjudication.json",
        source_key="contrasts/A1-A0 (PRIMARY)",
        evidence_scope="outcome-known internal; Welch interval",
        color="#2166ac", marker="o",
    )
    for category, label in (
        ("Industrial_and_Scientific", "Industrial: learned - identity"),
        ("CDs_and_Vinyl", "CDs: learned - identity"),
    ):
        row = breadth["per_category"][category]
        add_row(
            rows, group=amazon, label=label,
            estimate=row["paired_mean"], interval=row["paired_ci"],
            source_file="fir_canonical_breadth_adjudication.json",
            source_key=f"per_category/{category}",
            evidence_scope="outcome-known internal; paired-t interval",
            color="#2166ac", marker="o",
        )
    row = software["primary_contrast"]
    add_row(
        rows, group=amazon, label="Software: learned - identity",
        estimate=row["mean"], interval=row["ci95"],
        source_file="fir_prospective_sw_v3_adjudication.json",
        source_key="primary_contrast",
        evidence_scope="outcome-known same-team robustness; paired-t interval",
        color="#2166ac", marker="o",
    )

    controls_group = "Matched MI control boundaries"
    row = pointwise["contrasts"]["learned-pointwise"]
    add_row(
        rows, group=controls_group, label="Learned - pointwise FIR",
        estimate=row["mean"], interval=row["ci95"],
        source_file="fir_pointwise_v1_adjudication.json",
        source_key="contrasts/learned-pointwise",
        evidence_scope="outcome-known internal; paired-t interval",
        color="#d97706", marker="D",
    )
    row = controls["family_b"]["learned-shared"]
    add_row(
        rows, group=controls_group, label="Learned - shared filter",
        estimate=row["mean"], interval=row["ci95"],
        source_file="fir_controls_adjudication.json",
        source_key="family_b/learned-shared",
        evidence_scope="outcome-known internal; paired-t interval",
        color="#d97706", marker="D",
    )

    transfer = "Prospectively frozen MovieLens transfer"
    for key, label in (
        ("learned-identity", "Learned - identity"),
        ("learned-pointwise", "Learned - pointwise FIR"),
    ):
        row = ml1m["replication"][key]
        add_row(
            rows, group=transfer, label=label,
            estimate=row["mean"], interval=row["ci"],
            source_file="fir_efficiency_ml1m_v1_adjudication.json",
            source_key=f"replication/{key}",
            evidence_scope=(
                "prospectively frozen same-investigator; paired-t interval"
            ),
            color="#762a83", marker="s",
        )

    OUT.mkdir(exist_ok=True)
    csv_path = OUT / "fig_fir_evidence_summary_data.csv"
    fields = [
        "group", "label", "estimate", "ci_low", "ci_high", "source_file",
        "source_key", "evidence_scope",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                key: f"{row[key]:.12f}" if key in {
                    "estimate", "ci_low", "ci_high"
                } else row[key]
                for key in fields
            })

    plt.rcParams.update({
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "font.size": 8.6,
        "axes.labelsize": 9.0,
        "figure.dpi": 180,
    })
    fig, ax = plt.subplots(figsize=(7.25, 4.45))
    y_positions = [10, 9, 8, 7, 5, 4, 2, 1]
    for y, row in zip(y_positions, rows):
        ax.errorbar(
            row["estimate"], y,
            xerr=[[row["estimate"] - row["ci_low"]],
                  [row["ci_high"] - row["estimate"]]],
            fmt=row["marker"], color=row["color"], ecolor=row["color"],
            markersize=5.2, capsize=3.0, elinewidth=1.25, zorder=3,
        )
        ax.text(
            1.015, y, f'{row["estimate"]:+.6f}',
            transform=ax.get_yaxis_transform(), ha="left", va="center",
            fontsize=7.4, color="#333333", clip_on=False,
        )

    ax.axvline(0, color="#4d4d4d", linewidth=1.0, zorder=1)
    ax.axhspan(6.45, 10.55, color="#2166ac", alpha=0.045, zorder=0)
    ax.axhspan(3.45, 5.55, color="#d97706", alpha=0.055, zorder=0)
    ax.axhspan(0.45, 2.55, color="#762a83", alpha=0.045, zorder=0)
    ax.set_yticks(y_positions, [row["label"] for row in rows])
    ax.set_ylim(0.35, 11.05)
    ax.set_xlim(-0.00065, 0.00675)
    ax.set_xlabel("Contrast in NDCG@10 (point estimate and reported 95% CI)")
    ax.grid(axis="x", alpha=0.22)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.text(-0.00062, 10.72, amazon, color="#174f8a", fontweight="bold")
    ax.text(-0.00062, 5.72, controls_group, color="#a65300", fontweight="bold")
    ax.text(-0.00062, 2.72, transfer, color="#5b1f64", fontweight="bold")
    ax.set_title(
        "FIR evidence map: scope and boundary conditions",
        fontsize=10.5, fontweight="bold", pad=20,
    )
    fig.text(
        0.5, 0.008,
        "Visual index only: intervals retain their source estimators and are not a common family or pooled analysis.",
        ha="center", fontsize=7.5, color="#444444",
    )
    fig.tight_layout(rect=(0.08, 0.055, 0.91, 0.95))

    png_path = OUT / "fig_fir_evidence_summary.png"
    pdf_path = OUT / "fig_fir_evidence_summary.pdf"
    fig.savefig(png_path, bbox_inches="tight", metadata={"Software": "matplotlib"})
    fig.savefig(pdf_path, bbox_inches="tight", metadata={
        "Creator": "make_fig_fir_evidence_summary.py",
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
