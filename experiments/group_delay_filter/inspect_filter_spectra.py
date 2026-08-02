#!/usr/bin/env python3
"""Write canonical temporal-filter spectra without loading recommendation data."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import torch


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--threshold", type=float, default=0.905)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    state = torch.load(args.checkpoint, map_location="cpu", weights_only=True)
    layers = []
    for name, value in sorted(state.items()):
        if not name.endswith(".complex_weight") or value.shape[-1] != 2:
            continue
        matrix = torch.view_as_complex(value.squeeze(0).contiguous()).to(torch.complex128)
        matrix = matrix.clone()
        matrix[0] = matrix[0].real
        matrix[-1] = matrix[-1].real
        singular_values = torch.linalg.svdvals(matrix)
        energy = singular_values.square()
        retained = float(energy[0] / energy.sum())
        layers.append({
            "parameter": name,
            "shape": list(matrix.shape),
            "canonicalization": "DC and Nyquist responses constrained to real values",
            "rank1_retained_energy": retained,
            "selected": retained >= args.threshold,
            "singular_values": singular_values.tolist(),
        })
    if not layers:
        raise SystemExit("checkpoint has no complex temporal filters")

    artifact = {
        "protocol": "CANONICAL_FILTER_SPECTRA_V1",
        "checkpoint": str(args.checkpoint.resolve()),
        "checkpoint_sha256": sha256(args.checkpoint),
        "inspector_sha256": sha256(Path(__file__)),
        "rank1_energy_threshold": args.threshold,
        "test_access": "none",
        "layers": layers,
        "selected_layers": [row["parameter"] for row in layers if row["selected"]],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2) + "\n", encoding="ascii")
    print(json.dumps({
        "energies": [row["rank1_retained_energy"] for row in layers],
        "selected_layers": artifact["selected_layers"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
