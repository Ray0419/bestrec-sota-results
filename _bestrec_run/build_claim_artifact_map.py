#!/usr/bin/env python
"""Build and verify the manuscript's claim-to-artifact map.

The map is deliberately generated from the strict cell manifest rather than
maintained as an unaudited prose ledger.  `--verify` fails if the committed map
drifts, if a mapped cell family disappears, if a mapped source is missing, or if
any mapped paper cell is not active/traceable.
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CELL_MANIFEST = ROOT / "_bestrec_run" / "hstu_results_manifest.json"
RELEASE_MANIFEST = ROOT / "RELEASE_MANIFEST.json"
OUT = ROOT / "CLAIM_ARTIFACT_MAP.md"


CLAIMS = [
    {
        "id": "C1",
        "claim": "Canonical FIR on Musical_Instruments",
        "boundary": "Outcome-visible internal learned-minus-identity estimate; Welch primary analysis, not independent confirmation.",
        "tables": ["fir_v3"],
        "files": ["PREREG_FIR_V3.md", "_bestrec_run/adjudicate_fir_v3.py",
                  "_bestrec_run/fir_v3_adjudication.json"],
    },
    {
        "id": "C2",
        "claim": "Canonical FIR breadth on Industrial_and_Scientific and CDs_and_Vinyl",
        "boundary": "Historical package breadth plus matched-initialization, zero-category-tuning canonical robustness and outcome-visible independent-arm TFV2 estimates; not transfer confirmation.",
        "tables": ["fir_breadth", "fir_canonical_breadth", "tfv2"],
        "files": ["PREREG_FIR_CANONICAL_BREADTH.md",
                  "_bestrec_run/adjudicate_fir_canonical_breadth.py",
                  "_bestrec_run/fir_canonical_breadth_adjudication.json"],
    },
    {
        "id": "C3",
        "claim": "Active-control and non-temporal-placebo mechanism boundary",
        "boundary": "Temporally active residuals improve identity; learned taps do not separate from the shared causal filter, but learned FIR beats an equal-parameter current-position-only compound placebo in an outcome-known MI study. This discriminates learned FIR from that tested placebo; it does not isolate temporal access, per-channel necessity, or external generalization.",
        "tables": ["fir_controls", "fir_pointwise"],
        "files": ["PREREG_FIR_CONTROLS.md", "PREREG_FIR_CONTROLS_ERRATA.md",
                  "_bestrec_run/adjudicate_fir_controls.py",
                  "_bestrec_run/fir_controls_adjudication.json",
                  "PREREG_FIR_POINTWISE_V1.md",
                  "_bestrec_run/adjudicate_fir_pointwise_v1.py",
                  "_bestrec_run/fir_pointwise_v1_adjudication.json",
                  "_bestrec_run/test_fir_causality.py"],
    },
    {
        "id": "C4",
        "claim": "Musical_Instruments published-point threshold comparison",
        "boundary": "Per-category point-estimate comparison under the reproduced protocol; no paired or distributional superiority.",
        "tables": ["tableV2conf"],
        "files": ["SOTA_CONFIRM_PREREG_V2.md", "SOTA_CONFIRM_PREREG_V2_ERRATA.md",
                  "SOTA_CONFIRM_V2_RESULTS.md",
                  "_bestrec_run/summarize_sota_confirm_v2.py"],
    },
    {
        "id": "C5",
        "claim": "Office_Products V3 published/local-reference threshold comparison",
        "boundary": "Only the frozen V3 per-category point-estimate wording counts; Office V1 remains permanently VOID/descriptive.",
        "tables": ["office_v3", "office_confirmation"],
        "files": ["PREREG_OFFICE_V3.md", "OFFICE_V3_RESULTS.md",
                  "_bestrec_run/adjudicate_office_v3.py",
                  "SOTA_CONFIRM_PREREG_OFFICE.md",
                  "_bestrec_run/office_prereg_tools.py"],
    },
    {
        "id": "C6",
        "claim": "Frequency-5-heavy text-tail case",
        "boundary": "Dataset-specific repaired-estimand result; no cold-start capability or cross-dataset heterogeneity claim.",
        "tables": ["table1d"],
        "files": ["PREREG_TAIL_FIR_V2.md", "_bestrec_run/adjudicate_tfv2.py",
                  "figures/fig_tail_law_mechanism_data.csv"],
    },
    {
        "id": "C7",
        "claim": "Interaction/user thinning and resource-plane diagnostics",
        "boundary": "Bundled synthetic interventions and level contrasts; not identification of the real-world data-generating process.",
        "tables": ["table1e", "table541", "table542"],
        "files": ["figures/fig_r1r2_plane.pdf",
                  "_bestrec_run/make_table_5_4_titration.py"],
    },
    {
        "id": "C8",
        "claim": "Negative-result and screening map",
        "boundary": "Mostly single-seed search record; observations are not powered exclusions or equivalence results.",
        "tables": ["table2"],
        "files": ["_bestrec_run/emit_latex_tables.py"],
    },
    {
        "id": "C9",
        "claim": "Core HSTU/FIR ablations and text-stack support",
        "boundary": "Internal ablations at their stated seed counts; TAPE is supporting and sub-additive, not a headline architecture claim.",
        "tables": ["table1", "table1a", "table1c"],
        "files": ["_bestrec_run/run_sasrec_sbert.py"],
    },
    {
        "id": "C10",
        "claim": "Comparator regeneration and HSTU implementation parity",
        "boundary": "Core-block equality at one aligned configuration plus environment-caveated single-run regenerations; no pinned end-to-end equivalence.",
        "tables": ["table1b", "theirs_on_ours"],
        "files": ["HSTU_PARITY_REPORT.md", "PINNED_ENV_PARITY_REPORT.md",
                  "THEIRS_ON_OURS_REPORT.md", "_bestrec_run/test_hstu_parity.py",
                  "_bestrec_run/test_pinned_env_parity.py"],
    },
    {
        "id": "C11",
        "claim": "Frozen Software FIR robustness result",
        "boundary": "Pre-declared matched-initialization learned-minus-identity practical-effect result, classified outcome-known/exploratory because prior V2 validation-output non-visibility is not independently established; local same-user custody, same investigator, same code lineage, and same Amazon family, so not independent confirmation or cross-domain replication.",
        "tables": ["fir_prospective_sw_v3"],
        "files": ["PREREG_FIR_PROSPECTIVE_SW_V3.md",
                  "_bestrec_run/fir_prospective_sw_v3_common.py",
                  "_bestrec_run/run_fir_prospective_sw_v3.py",
                  "_bestrec_run/eval_fir_prospective_sw_v3.py",
                  "_bestrec_run/adjudicate_fir_prospective_sw_v3.py",
                  "_bestrec_run/fir_prospective_sw_v3_adjudication.json",
                  "FIR_PROSPECTIVE_SW_V3_REPLAY_ERRATUM.md"],
    },
    {
        "id": "C12",
        "claim": "Prospective MovieLens 1M FIR replication and conditional parsimony",
        "boundary": "Learned FIR did not replicate versus identity or pointwise. Shared/grouped/low-rank noninferiority versus learned is conditional numerical compression only because the learned-FIR effect gate failed. Prospectively frozen same-investigator non-Amazon evidence, not independent confirmation, equivalence to identity, deployment utility, or population generalization; the public graph cannot replay private ML-1M record-level endpoints.",
        "tables": ["fir_efficiency_ml1m_v1"],
        "files": ["PREREG_FIR_EFFICIENCY_ML1M_V1.md",
                  "_bestrec_run/acquire_movielens_fir_efficiency_v1.py",
                  "_bestrec_run/run_fir_efficiency_ml1m_v1.py",
                  "_bestrec_run/eval_fir_efficiency_ml1m_v1.py",
                  "_bestrec_run/adjudicate_fir_efficiency_ml1m_v1.py",
                  "_bestrec_run/fir_efficiency_ml1m_v1_adjudication.json",
                  "_bestrec_run/make_fig_fir_efficiency_ml1m_v1.py",
                  "figures/fig_fir_efficiency_ml1m_v1_data.csv",
                  "figures/fig_fir_efficiency_ml1m_v1.pdf",
                  "_bestrec_run/make_fig_movielens_cohort_flow.py",
                  "figures/fig_movielens_cohort_flow_data.csv",
                  "figures/fig_movielens_cohort_flow.pdf"],
    },
    {
        "id": "C13",
        "claim": "Official WEARec current-baseline execution under the paper evaluator",
        "boundary": "WEARec scored below the existing six-seed full-model reference under the paper's shared split, complete-history mask, full-catalog evaluator, cutoff, and tie rule. This is an official-model/equal-evaluation feasibility baseline by the same investigators on an outcome-known split, not independent confirmation, SOTA, a paired experiment, equal architecture/loss/schedule, or equal tuning budgets; the public graph replays released NDCG aggregate arithmetic, not private endpoint extraction or HR/MRR raw-vector arithmetic.",
        "tables": ["wearec_v1"],
        "files": ["PREREG_WEAREC_BASELINE_V1.md",
                  "_bestrec_run/acquire_wearec_baseline_v1.py",
                  "_bestrec_run/prepare_wearec_baseline_v1.py",
                  "_bestrec_run/wearec_baseline_v1_common.py",
                  "_bestrec_run/test_wearec_baseline_v1.py",
                  "_bestrec_run/run_wearec_baseline_v1.py",
                  "_bestrec_run/eval_wearec_baseline_v1.py",
                  "_bestrec_run/run_wearec_campaign_v1.py",
                  "_bestrec_run/adjudicate_wearec_baseline_v1.py",
                  "_bestrec_run/wearec_baseline_v1_catalog_manifest.json",
                  "_bestrec_run/wearec_baseline_v1_selection.json",
                  "_bestrec_run/wearec_baseline_v1_adjudication.json"],
    },
    {
        "id": "C14",
        "claim": "Frozen AlphaFuse-style text+ID whole-package current comparator",
        "boundary": "The AlphaFuse-style MiniLM package scored above a zero-initialized upstream-class SASRec ID control but below the existing six-seed full-model reference. This is prospectively frozen, outcome-known, same-investigator whole-package evidence under shared data/evaluation and one frozen training configuration. MiniLM replaces the published AlphaFuse text vectors; architecture, text availability, initialization, trainable capacity, parameter allocation, and tuning history are not equalized, and the parser-default Normal(0,1) setting was not tested. Official recipes may override initialization by dataset, so the parser setting is not a universal upstream default. The result is not a published-table reproduction, paired experiment, null-space-fusion isolation, independent confirmation, or SOTA. The public graph recomputes released aggregate arithmetic and checks ledger shape, hash-string syntax, and uniqueness; it does not read or hash the private endpoints/sidecars or replay record-level bootstraps.",
        "tables": ["ee_v3"],
        "files": ["PREREG_EE_V3.md",
                  "_bestrec_run/prepare_ee_v3.py",
                  "_bestrec_run/ee_v3_input_manifest.json",
                  "_bestrec_run/ee_v3_common.py",
                  "_bestrec_run/test_ee_v3.py",
                  "_bestrec_run/run_ee_v3.py",
                  "_bestrec_run/eval_ee_v3.py",
                  "_bestrec_run/run_ee_v3_campaign.py",
                  "_bestrec_run/adjudicate_ee_v3.py",
                  "_bestrec_run/ee_v3_adjudication.json"],
    },
    {
        "id": "C15",
        "claim": "FIR evidence-map visualization",
        "boundary": "Visual index of eight already adjudicated contrasts. Source estimators and evidence classes remain separate; no pooling, common multiplicity family, independent confirmation, or generalization claim is created by the figure.",
        "tables": ["fir_evidence_summary"],
        "files": ["_bestrec_run/make_fig_fir_evidence_summary.py",
                  "figures/fig_fir_evidence_summary_data.csv",
                  "figures/fig_fir_evidence_summary.pdf",
                  "_bestrec_run/fir_v3_adjudication.json",
                  "_bestrec_run/fir_canonical_breadth_adjudication.json",
                  "_bestrec_run/fir_controls_adjudication.json",
                  "_bestrec_run/fir_pointwise_v1_adjudication.json",
                  "_bestrec_run/fir_prospective_sw_v3_adjudication.json",
                  "_bestrec_run/fir_efficiency_ml1m_v1_adjudication.json"],
    },
    {
        "id": "C16",
        "claim": "Parser-default Normal(0,1) SASRec-ID comparator sensitivity",
        "boundary": "Eight fresh parser-default Normal(0,1) SASRec-ID runs produced NDCG@10 0.043065 [0.042645,0.043486]. The earlier V3 AlphaFuse-style package remains above this control by +0.005207 [+0.004779,+0.005635], while normal initialization improves SASRec-ID over the earlier zero-initialized control by +0.004042 [+0.003089,+0.004995]. This is prospectively frozen but outcome-known same-investigator cross-campaign comparator-fairness sensitivity. Phase/date and initialization are confounded; architecture, capacity, and parameter allocation remain unequal. It is not independent confirmation, causal isolation, an equal-budget factorial, or SOTA. The public graph recomputes released aggregate arithmetic and checks the private endpoint/sidecar ledger without reading private files.",
        "tables": ["ee_v4"],
        "files": ["PREREG_EE_V4.md",
                  "_bestrec_run/ee_v4_common.py",
                  "_bestrec_run/test_ee_v4.py",
                  "_bestrec_run/run_ee_v4.py",
                  "_bestrec_run/eval_ee_v4.py",
                  "_bestrec_run/run_ee_v4_campaign.py",
                  "_bestrec_run/adjudicate_ee_v4.py",
                  "_bestrec_run/ee_v4_adjudication.json"],
    },
]

EXPECTED_EVIDENCE = {
    "fir_v3": {"exploratory"},
    "fir_breadth": {"exploratory"},
    "fir_canonical_breadth": {"exploratory"},
    "fir_controls": {"exploratory"},
    "fir_pointwise": {"exploratory"},
    "fir_evidence_summary": {"exploratory"},
    "fir_prospective_sw_v3": {"exploratory"},
    "fir_efficiency_ml1m_v1": {"exploratory"},
    "wearec_v1": {"exploratory"},
    "ee_v3": {"exploratory"},
    "ee_v4": {"exploratory"},
    "tableV2conf": {"confirmatory"},
    "office_v3": {"confirmatory"},
    "office_confirmation": {"exploratory"},
    "table1d": {"exploratory"},
    "table1e": {"exploratory"},
    "table541": {"exploratory"},
    "table542": {"exploratory"},
    "table2": {"confirmatory", "exploratory"},
    "table1": {"exploratory"},
    "table1a": {"exploratory"},
    "table1c": {"exploratory"},
    "table1b": {"exploratory"},
    "theirs_on_ours": {"exploratory"},
    "tfv2": {"exploratory"},
}


def rel_link(path: str) -> str:
    return f"[`{path}`]({path.replace(' ', '%20')})"


def build() -> str:
    data = json.loads(CELL_MANIFEST.read_text(encoding="utf-8"))
    release = json.loads(RELEASE_MANIFEST.read_text(encoding="utf-8"))
    cells = data["cells"]
    by_table = collections.defaultdict(list)
    for cell in cells:
        by_table[cell["table_id"]].append(cell)

    errors = []
    rows = []
    mapped_counts = collections.Counter()
    for spec in CLAIMS:
        mapped = []
        for table in spec["tables"]:
            family = by_table.get(table, [])
            if not family:
                errors.append(f"{spec['id']}: missing table family {table}")
                continue
            active = [c for c in family if c["status"] == "OK"]
            if not active:
                errors.append(f"{spec['id']}: table family {table} has no active cells")
            for cell in active:
                if cell.get("paper_check_class") not in {"exact", "within_rounding"}:
                    errors.append(
                        f"{spec['id']}: {cell['cell_id']} is not paper-traceable "
                        f"({cell.get('paper_check_class')})"
                    )
            observed_evidence = {c.get("evidence_class") for c in active}
            expected_evidence = EXPECTED_EVIDENCE.get(table)
            if expected_evidence is not None and observed_evidence != expected_evidence:
                errors.append(
                    f"{spec['id']}: {table} evidence taxonomy {sorted(observed_evidence)} "
                    f"!= expected {sorted(expected_evidence)}"
                )
            mapped.extend(c["cell_id"] for c in active)
        for path in spec["files"]:
            if not (ROOT / path).exists():
                errors.append(f"{spec['id']}: missing mapped artifact {path}")
        rows.append((spec, mapped))
        mapped_counts.update(mapped)

    active_ids = {c["cell_id"] for c in cells if c["status"] == "OK"}
    mapped_ids = set(mapped_counts)
    missing = sorted(active_ids - mapped_ids)
    extras = sorted(mapped_ids - active_ids)
    duplicates = sorted(cid for cid, count in mapped_counts.items() if count != 1)
    if missing:
        errors.append("active cells absent from claim map: " + ", ".join(missing))
    if extras:
        errors.append("claim map references non-active cells: " + ", ".join(extras))
    if duplicates:
        errors.append("active cells not mapped exactly once: " + ", ".join(duplicates))

    if errors:
        raise SystemExit("claim-map validation failed:\n  - " + "\n  - ".join(errors))

    status_counts = collections.Counter(c["status"] for c in cells)
    check_counts = collections.Counter(c.get("paper_check_class", "") for c in cells)
    lines = [
        "# Claim-to-artifact map",
        "",
        "This file is generated by `_bestrec_run/build_claim_artifact_map.py` from "
        "the strict artifact graph. It maps each retained scientific claim to its "
        "paper-bound cells, frozen protocol/adjudicator where applicable, and "
        "supporting artifacts. It is a traceability map, not an upgrade of any "
        "evidence class.",
        "",
        f"Graph snapshot: **{status_counts['OK']} active cells**, "
        f"**{status_counts['REMOVED_FROM_PAPER']} retired**, "
        f"**{status_counts['EXTERNAL_PUBLISHED']} external literature cells**; "
        f"active paper checks = **{check_counts['exact']} exact + "
        f"{check_counts['within_rounding']} within rounding**, zero mismatch/untraceable. "
        f"Release manifest date: **{release.get('date', 'unknown')}**.",
        f"Completeness invariant: **{len(active_ids)}/{len(active_ids)} active cells mapped "
        "exactly once**.",
        "",
        "## Retained claim map",
        "",
        "| ID | Retained claim | Exact boundary | Graph cells | Protocol / adjudicator / supporting artifacts |",
        "|---|---|---|---|---|",
    ]
    for spec, mapped in rows:
        cells_text = "<br>".join(f"`{x}`" for x in mapped)
        files_text = "<br>".join(rel_link(x) for x in spec["files"])
        lines.append(
            f"| {spec['id']} | {spec['claim']} | {spec['boundary']} | "
            f"{cells_text} | {files_text} |"
        )

    lines.extend([
        "",
        "## Artifact-family inventory",
        "",
        "| Graph family | Active | Retired | External | Evidence classes among active cells |",
        "|---|---:|---:|---:|---|",
    ])
    for table in sorted(by_table):
        family = by_table[table]
        statuses = collections.Counter(c["status"] for c in family)
        evidence = collections.Counter(
            c.get("evidence_class", "unspecified") for c in family if c["status"] == "OK"
        )
        evidence_text = ", ".join(f"{k}: {v}" for k, v in sorted(evidence.items())) or "—"
        lines.append(
            f"| `{table}` | {statuses['OK']} | {statuses['REMOVED_FROM_PAPER']} | "
            f"{statuses['EXTERNAL_PUBLISHED']} | {evidence_text} |"
        )

    lines.extend([
        "",
        "## Reproduction paths",
        "",
        "1. **Hydrated checkout:** run `python _bestrec_run/rebuild_hstu_submission.py --strict`. "
        "This checks core-block parity, causal filter paths, the paper-cell graph, release "
        "manifest, and every governed adjudicator.",
        "2. **Fresh public clone:** run `python bootstrap_public_clone.py`, then the same strict "
        "rebuild. Bootstrap downloads every release-only asset and verifies its raw SHA-256 "
        "before the strict graph is evaluated.",
        "",
        "The two paths verify the same numerical boundary. Neither supplies missing author/legal "
        "metadata, converts outcome-visible studies into confirmation, or mints the final DOI deposit.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    text = build()
    if args.write:
        OUT.write_text(text, encoding="utf-8", newline="\n")
        print(f"CLAIM MAP WRITE: {OUT}")
        return 0
    if not OUT.exists():
        print(f"CLAIM MAP VERIFY: FAIL (missing {OUT})")
        return 2
    actual = OUT.read_text(encoding="utf-8")
    if actual != text:
        print("CLAIM MAP VERIFY: FAIL (generated content drift; run --write)")
        return 2
    print("CLAIM MAP VERIFY: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
