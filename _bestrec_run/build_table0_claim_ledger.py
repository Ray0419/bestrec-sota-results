#!/usr/bin/env python
"""Generate and verify manuscript Table 0 from the active artifact graph.

The prose attribution boundary remains an authored literature judgment, while
every quantitative FIR statement is formatted from an active, successfully
recomputed graph cell.  The strict rebuild runs ``--check`` so Table 0 cannot
silently drift back to manual numerical transcription.
"""
from __future__ import annotations

import argparse
import difflib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PAPER = ROOT / "PAPER_SUBMISSION.md"
MANIFEST = ROOT / "_bestrec_run" / "hstu_results_manifest.json"
START = "<!-- BEGIN GENERATED TABLE 0: build_table0_claim_ledger.py -->"
END = "<!-- END GENERATED TABLE 0 -->"


def signed(value: float, digits: int = 6) -> str:
    return f"{value:+.{digits}f}"


def build() -> str:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    cells = {cell["cell_id"]: cell for cell in manifest["cells"]}
    required = {
        "firv3.primary.welch": "exploratory",
        "fircanon.is.paired": "exploratory",
        "fircanon.cd.paired": "exploratory",
        "firctrl.b.shared": "exploratory",
        "firpoint.learned_pointwise": "exploratory",
        "firprosp.swv3.learned_identity": "exploratory",
        "fireff.ml1m.aggregate": "exploratory",
    }
    for cell_id, evidence_class in required.items():
        cell = cells.get(cell_id)
        if (cell is None or cell.get("status") != "OK"
                or cell.get("evidence_class") != evidence_class):
            raise RuntimeError(f"Table 0 source cell is not active/OK: {cell_id}")

    mi = cells["firv3.primary.welch"]["recomputed"]["diff"]
    industrial = cells["fircanon.is.paired"]["recomputed"]["mean"]
    cds = cells["fircanon.cd.paired"]["recomputed"]["mean"]
    shared = cells["firctrl.b.shared"]["recomputed"]
    pointwise = cells["firpoint.learned_pointwise"]["recomputed"]
    software = cells["firprosp.swv3.learned_identity"]["recomputed"]
    ml1m = cells["fireff.ml1m.aggregate"]["recomputed"]

    return "\n".join([
        START,
        "",
        "**Table 0: Claim boundary — reused basis, specific change, and supported evidence.**",
        "",
        "| Component and reused basis | Specific change | Evidence and boundary |",
        "|---|---|---|",
        "| **HSTU base** — Zhai et al. (2024): pointwise `silu(QKᵀ + rab) V`, per-block normalization, and relative biases | Pure-PyTorch implementation; two spurious normalizations removed | Core-block parity only at a mirrored aligned configuration; no pinned end-to-end reproduction (§3.2, §5.6, §6.3). Prior-work implementation. |",
        "| **BLaIR/SBERT text** — Hou et al. (2024), Reimers & Gurevych (2019), Wang et al. (2020) | Frozen off-the-shelf text features and Hou et al.'s MLP adaptor; no method change | Table 1a encoder comparison. Prior work. |",
        "| **Label smoothing/time bias** — Szegedy et al. (2016); TiSASRec; HSTU (Zhai et al., 2024) | Integrated with this backbone and full-catalog chunked softmax | +0.0013 and +0.0027 single flags (Table 1). Prior work. |",
        "| **Sequence/frequency filters** — FMLP-Rec, BSARec, FreqRec, WEARec; causal convolutions include Caser, NextItNet, C3SASR, and AdaMCT | None inserted as-is: the first two filters are bidirectional in their original forms and FreqRec/WEARec are larger systems | Motivation and novelty boundary only (§3.7b). Filtering, frequency modeling, and causal convolution are prior art. |",
        ("| **Causal FIR adaptation (ours)** — the filtering/convolution line above "
         "| Minimal leak-free, gradient-active, identity-initialized left-causal depthwise residual before an HSTU-style all-position stack "
         f"| Outcome-known FIR−identity estimates: MI {signed(mi)}, IS {signed(industrial)}, CDs {signed(cds)}. "
         f"Software robustness: {signed(software['mean'])} [{signed(software['ci_lo'])},{signed(software['ci_hi'])}]. "
         f"Learned beats the equal-parameter current-only placebo by {signed(pointwise['mean'])} "
         f"but does not separate from shared FIR ({signed(shared['mean'])} [{signed(shared['ci_lo'])},{signed(shared['ci_hi'])}]). "
         f"Prospective MovieLens: learned minus identity {signed(ml1m['learned_identity_mean'])} "
         f"[{signed(ml1m['learned_identity_ci_lo'])},{signed(ml1m['learned_identity_ci_hi'])}] "
         f"and learned minus pointwise {signed(ml1m['learned_pointwise_mean'])} "
         f"[{signed(ml1m['learned_pointwise_ci_lo'])},{signed(ml1m['learned_pointwise_ci_hi'])}]; "
         "neither gate passed, so parsimonious-arm NI is conditional only. "
         "**Incremental modular contribution; no general FIR benefit or independent confirmation.** |"),
        "| **TAPE (ours)** — TIGER, VQ-Rec, ProtoMF; prototype/semantic-ID motivation | Frozen soft assignments gate a zero-initialized additive prototype table | +0.0009 single flag; +0.0004 four-seed check. Supporting ablation (§5.1). |",
        "| **Tail/thinning analysis (ours)** — standard popularity strata, MELT, DropoutNet, CLCRec | Per-dataset text−ID tail contrast and matched-R1 interaction/user thinning | MI +0.000420 (outcome-visible); VG null; cross-dataset p=.13; user-mode p=.058. Secondary empirical boundary (§5.3–§5.4). |",
        END,
    ])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.write == args.check:
        parser.error("choose exactly one of --write or --check")

    text = PAPER.read_text(encoding="utf-8")
    if START not in text or END not in text:
        raise RuntimeError("Table 0 generated-region markers are missing")
    before, remainder = text.split(START, 1)
    current_inner, after = remainder.split(END, 1)
    current = START + current_inner + END
    expected = build()
    if args.write:
        PAPER.write_text(before + expected + after, encoding="utf-8", newline="")
        print("TABLE 0 WRITE: OK")
        return 0
    if current != expected:
        print("TABLE 0 VERIFY: FAIL")
        print("".join(difflib.unified_diff(
            current.splitlines(True), expected.splitlines(True),
            fromfile="PAPER_SUBMISSION.md", tofile="generated Table 0")))
        return 2
    print("TABLE 0 VERIFY: PASS (all quantitative FIR fields graph-sourced)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
