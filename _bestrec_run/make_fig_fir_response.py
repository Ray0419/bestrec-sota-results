#!/usr/bin/env python
"""Render descriptive selected-checkpoint FIR tap/frequency diagnostics.

Inputs are the eight released learned-arm checkpoints from the outcome-known
PREREG_FIR_CONTROLS campaign.  Channels are summarized within each seed first;
the displayed ordinary t intervals are then over eight seed summaries.  This
figure diagnoses the fitted operator and is not a mechanism or confirmation
test.
"""
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch


ROOT = Path(__file__).resolve().parent.parent
RUN = ROOT / "_bestrec_run"
OUT = ROOT / "figures"
SEEDS = list(range(20260901, 20260909))
T975_DF7 = 2.364624251


def interval(values: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = values.mean(axis=0)
    half = T975_DF7 * values.std(axis=0, ddof=1) / np.sqrt(values.shape[0])
    return mean, mean - half, mean + half


def main() -> int:
    OUT.mkdir(exist_ok=True)
    kernels = []
    for seed in SEEDS:
        path = RUN / (
            f"results_Musical_Instruments_FIRCTRL_learned_seed{seed}.best.pt"
        )
        checkpoint = torch.load(path, map_location="cpu", weights_only=False)
        weight = checkpoint["state_dict"]["fir_control_module.weight"]
        # Conv1d uses cross-correlation after left padding: reverse the stored
        # axis so index 0 below is contemporaneous lag 0, then lag 1, ... .
        kernels.append(weight[:, 0, :].detach().float().numpy()[:, ::-1].copy())
    kernels = np.stack(kernels, axis=0)  # seed, channel, lag

    signed_by_seed = kernels.mean(axis=1)
    abs_by_seed = np.abs(kernels).mean(axis=1)
    signed = interval(signed_by_seed)
    absolute = interval(abs_by_seed)

    omega = np.linspace(0.0, np.pi, 129)
    effective = kernels.copy()
    effective[:, :, 0] += 1.0  # residual x + conv_Delta(x)
    phase = np.exp(-1j * omega[:, None] * np.arange(effective.shape[-1])[None, :])
    response = np.abs(np.einsum("scl,fl->scf", effective, phase))
    response_by_seed = response.mean(axis=1)
    freq = interval(response_by_seed)

    csv_path = OUT / "fig_fir_response_data.csv"
    fields = ["series", "x", "mean", "ci_low", "ci_high"] + [
        f"seed_{seed}" for seed in SEEDS
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=fields)
        writer.writeheader()
        series = [
            ("signed_delta_tap", np.arange(kernels.shape[-1]), signed, signed_by_seed),
            ("absolute_delta_tap", np.arange(kernels.shape[-1]), absolute, abs_by_seed),
            ("effective_response_magnitude", omega / np.pi, freq, response_by_seed),
        ]
        for name, xs, (mean, low, high), seed_values in series:
            for i, x in enumerate(xs):
                row = {
                    "series": name,
                    "x": f"{x:.9g}",
                    "mean": f"{mean[i]:.9g}",
                    "ci_low": f"{low[i]:.9g}",
                    "ci_high": f"{high[i]:.9g}",
                }
                row.update(
                    {f"seed_{seed}": f"{seed_values[j, i]:.9g}"
                     for j, seed in enumerate(SEEDS)}
                )
                writer.writerow(row)

    plt.rcParams.update({
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "font.size": 9.5,
        "axes.titlesize": 10.5,
        "axes.labelsize": 9.5,
        "legend.fontsize": 8.5,
        "figure.dpi": 160,
    })
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.4))

    lags = np.arange(kernels.shape[-1])
    axes[0].axhline(0.0, color="#666666", lw=0.7)
    axes[0].plot(lags, signed[0], marker="o", ms=2.8, color="#1f77b4",
                 label="signed channel mean")
    axes[0].fill_between(lags, signed[1], signed[2], color="#1f77b4", alpha=0.18)
    axes[0].plot(lags, absolute[0], marker="s", ms=2.4, color="#d97706",
                 label="mean absolute tap")
    axes[0].fill_between(lags, absolute[1], absolute[2], color="#d97706", alpha=0.16)
    axes[0].set(xlabel="causal lag (0 = contemporaneous)", ylabel="learned residual tap Δ",
                title="A. Learned tap profile")
    axes[0].set_xticks(lags[::2])
    axes[0].grid(alpha=0.22)
    axes[0].legend(frameon=False)

    axes[1].axhline(1.0, color="#666666", lw=0.8, ls="--", label="identity magnitude")
    axes[1].plot(omega / np.pi, freq[0], color="#2a9d8f",
                 label="effective residual response")
    axes[1].fill_between(omega / np.pi, freq[1], freq[2],
                         color="#2a9d8f", alpha=0.2)
    axes[1].set(xlabel="normalized angular frequency (×π)",
                ylabel="mean channel magnitude",
                title=r"B. Effective response $|1 + \Delta(e^{j\omega})|$")
    axes[1].grid(alpha=0.22)
    axes[1].legend(frameon=False)

    fig.suptitle("Selected-checkpoint FIR diagnostics (8 seed blocks; descriptive)",
                 fontsize=11, fontweight="bold")
    fig.text(
        0.5, -0.01,
        "Channels are summarized within seed; bands are ordinary 95% t intervals over "
        "eight seed summaries. Outcome-known control campaign; no mechanistic inference.",
        ha="center", fontsize=7.8, color="#444444",
    )
    fig.tight_layout(rect=(0, 0.055, 1, 0.94))

    png_path = OUT / "fig_fir_response.png"
    pdf_path = OUT / "fig_fir_response.pdf"
    fig.savefig(png_path, bbox_inches="tight", metadata={"Software": "matplotlib"})
    fig.savefig(pdf_path, bbox_inches="tight",
                metadata={"Creator": "make_fig_fir_response.py",
                          "CreationDate": None, "ModDate": None})
    plt.close(fig)
    print(f"WROTE {csv_path}")
    print(f"WROTE {png_path}")
    print(f"WROTE {pdf_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
