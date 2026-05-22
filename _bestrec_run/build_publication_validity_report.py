"""Generate a publication validity report for current BEST-Rec artifacts."""

from __future__ import annotations

from artifact_utils import DATASET_LABELS, DATASETS, ROOT, RUN_DIR, append_manifest_run, metric_fmt, read_json


OUT = ROOT / "PUBLICATION_VALIDITY_REPORT.md"


def main() -> None:
    valid = read_json(RUN_DIR / "results_lc2cpp_validated.json")
    sig = read_json(RUN_DIR / "significance_lc2cpp_validated.json")
    tables = read_json(RUN_DIR / "tables.json")

    lines = [
        "# Publication Validity Report",
        "",
        "## Bottom Line",
        "",
        "The validation-selected LC2C++ variant is publication-valid for the existing secondary",
        "`cold_fold_only` protocol, but it is **not** valid as a SOTA claim because the required",
        "full-catalog cold-item evaluation and modern baseline set are still incomplete.",
        "",
        "The validated-margin LC2C++ result is significantly better than LC2C V2 on all four",
        "datasets after Holm correction for the current cold_fold_only artifacts.",
        "",
        "Important audit note: this candidate was developed after exploratory runs in this",
        "workspace. For a clean publication submission, freeze this algorithm and rerun the",
        "documented pipeline on fresh seeds/splits before presenting it as final confirmatory",
        "evidence.",
        "",
        "## Validation-Selected LC2C++ vs LC2C V2",
        "",
        "| Dataset | LC2C V2 | LC2C++ validated-margin | Delta | p raw | Holm marker |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for ds in DATASETS:
        methods = valid["datasets"][ds]["methods"]
        base = methods["lc2c_v2"]["NDCG@10"]
        new = methods.get("lc2cpp_validated_margin", methods["lc2cpp_validated"])["NDCG@10"]
        comp = sig["comparisons"][ds]
        lines.append(
            f"| {DATASET_LABELS[ds]} | {metric_fmt(base, 6)} | {metric_fmt(new, 6)} | "
            f"{metric_fmt(new - base, 6)} | {comp['p_raw_str']} | {comp['marker']} |"
        )
    lines += [
        "",
        "## Allowed Claims",
        "",
        "- LC2C++ validated-margin improves the cold-fold-only NDCG@10 point estimate on all four datasets.",
        "- The improvement is Holm-significant on Beauty, Fashion, Instruments, and Books in the current artifacts.",
        "- LC2C V2 and LC2C++ validated remain significantly stronger than content-direct and the simplified DropoutNet-style baseline where those markers are recorded.",
        "",
        "## Disallowed Claims",
        "",
        "- Do not present the current result as a fresh confirmatory test; the algorithm was developed through exploratory iterations in this workspace.",
        "- Do not claim SOTA.",
        "- Do not use the fixed 0.95 z-fusion weight as a publication-valid result; it was found by exploratory test-set grid search.",
        "- Do not present cold_fold_only ranking as the primary full-catalog cold-item metric.",
        "",
        "## Remaining SOTA Blockers",
        "",
    ]
    for item in tables.get("limitations", []):
        lines.append(f"- {item}")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    append_manifest_run(
        command=["python", "build_publication_validity_report.py"],
        inputs=[RUN_DIR / "results_lc2cpp_validated.json", RUN_DIR / "significance_lc2cpp_validated.json", RUN_DIR / "tables.json"],
        outputs=[OUT],
        datasets=DATASETS,
        note="Generated publication validity report for validation-selected LC2C++.",
    )
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
