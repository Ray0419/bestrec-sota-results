# BEST-Rec v4 — Installation and Reproduction Guide

This guide walks through setting up the environment, downloading the data, running every experiment in the paper, and regenerating every figure and table.

Everything is reproducible from a clean machine in three phases:

1. **Install** — system dependencies + Python environment (~10 min, one-time).
2. **Data** — download four Amazon Reviews 2023 jsonl files and run preprocessing (~20 min, one-time).
3. **Experiments** — run the five experiment scripts and regenerate figures/PDF (~40 min total for all four datasets).

For the publication-grade SOTA attempt, use the confirmatory runner instead of the exploratory pipeline:

```powershell
uv --project _bestrec_run run python _bestrec_run/run_all_confirmatory.py --profile sota-confirmatory --datasets beauty,fashion,instruments,books --seeds 20260521,20260522,20260523,20260524,20260525 --candidate-scope full_catalog --no-books-cap
uv --project _bestrec_run run python _bestrec_run/validate_artifacts.py --strict-publication
```

This command writes only to `_bestrec_confirmatory/<run_id>/`, uses full-catalog cold-item ranking, requires uncapped Books warm-LOO, and fails with an internal report if the strict SOTA gates are not met.

---

## 0. Hardware and OS Requirements

- **OS:** tested on Windows 11 (paths in scripts use forward-slash `C:/Users/...` style which works on Windows under Python). Linux/macOS works with a path edit (see §0.1).
- **CPU:** any modern x86-64 (the closed-form solver is single-threaded BLAS; ~9 s for the largest dataset).
- **RAM:** 16 GB minimum, 64 GB recommended for the Books dataset (the dense 13K × 13K B matrix is ~1.4 GB and several copies live in memory simultaneously during ablations).
- **GPU (optional):** only used by SBERT title encoding (one-time, ~10 s on CPU for Books) and by the LightGCN baseline. No GPU required for BEST-Rec v4 itself.
- **Disk:** ~70 GB for raw Amazon Reviews jsonl files (Books alone is ~50 GB), ~3 GB for the preprocessed cache.

### 0.1 Path configuration

All scripts read `ROOT = "C:/Users/rayxc/Documents/R"` from the top of each file. To run on another machine:

```bash
# from the project root, change every ROOT constant in one shot:
grep -rl 'C:/Users/rayxc/Documents/R' _bestrec_run/ _paper_gen/ \
  | xargs sed -i 's|C:/Users/rayxc/Documents/R|/your/path/here|g'
```

(On Windows PowerShell, use `(Get-ChildItem -Recurse -Include *.py) | ForEach-Object { (Get-Content $_) -replace 'C:/Users/rayxc/Documents/R','D:/your/path' | Set-Content $_ }`.)

---

## 1. Install

### 1.1 Install `uv` (the Python package manager)

`uv` is a fast, reproducible Python package manager. We use it because the project pins every transitive dependency (including PyTorch CUDA 12.8) in `_bestrec_run/uv.lock`.

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Linux/macOS:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

After install, verify:
```bash
uv --version    # should print uv 0.x.y
```

### 1.2 Sync the Python environment

From the project root:

```bash
cd _bestrec_run
uv sync
```

This will:
- Install Python 3.12 (downloaded automatically by uv if not present),
- Create a virtual environment in `_bestrec_run/.venv/`,
- Install every pinned dependency from `uv.lock`:
  - `torch` (CUDA 12.8 build from PyTorch's index),
  - `numpy`, `scipy`, `scikit-learn`,
  - `sentence-transformers` (HuggingFace, pulls in `transformers` + `tokenizers`),
  - `tqdm`, `matplotlib`, `pdfplumber`, `reportlab`.

Expected size: ~5 GB on disk (PyTorch with CUDA wheels are ~2 GB).
Expected time: 3–8 minutes on a fast connection.

### 1.3 Verify the environment

```bash
uv run python -c "import torch, numpy, scipy, sklearn, sentence_transformers, tqdm, matplotlib, reportlab; print('OK')"
```

If you have a CUDA GPU and want to verify CUDA is detected:
```bash
uv run python -c "import torch; print('CUDA:', torch.cuda.is_available(), 'device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'cpu-only')"
```

---

## 2. Data

### 2.1 Download Amazon Reviews 2023

Download four interaction files and four metadata files from the official release:
<https://amazon-reviews-2023.github.io/>

Place them under `data/` with the directory layout below (the filenames must match exactly — they are hard-coded in `_bestrec_run/preprocess_v2.py`):

```
R/
└── data/
    ├── beauty/
    │   ├── All_Beauty.jsonl                  (~750 MB)
    │   └── meta_All_Beauty.jsonl             (~350 MB)
    ├── fashion/
    │   ├── Amazon_Fashion.jsonl              (~3 GB)
    │   └── meta_Amazon_Fashion.jsonl         (~2 GB)
    ├── instruments/
    │   ├── Musical_Instruments.jsonl         (~3 GB)
    │   └── meta_Musical_Instruments.jsonl    (~600 MB)
    └── books/
        ├── Books.jsonl                       (~30 GB)
        └── meta_Books.jsonl                  (~12 GB)
```

If you only want to reproduce a subset of the experiments, you can omit larger categories. Beauty + Fashion alone is ~6 GB and runs in under 10 minutes end-to-end.

### 2.2 Run preprocessing (deduplication + k-core + SBERT encoding)

From `_bestrec_run/`:

```bash
uv run python preprocess_v2.py beauty
uv run python preprocess_v2.py fashion
uv run python preprocess_v2.py instruments
uv run python preprocess_v2.py books      # this one takes ~10 min
```

Each invocation:
1. Streams the raw jsonl, deduplicates `(user_id, parent_asin)` keeping the latest rating by timestamp.
2. Applies k-core filtering (k = 5 / 4 / 10 / 20 for beauty / fashion / instruments / books).
3. Re-indexes users and items into contiguous integer IDs.
4. Computes SBERT embeddings (`all-MiniLM-L6-v2`) for every retained item title.
5. Writes a pickle to `cache/<dataset>/preprocessed_v2.pkl` and SBERT embeddings to `cache/<dataset>/sbert_titles.npy`.

After preprocessing, you should see:

```
cache/
├── beauty/       preprocessed_v2.pkl   sbert_titles.npy
├── fashion/      preprocessed_v2.pkl   sbert_titles.npy
├── instruments/  preprocessed_v2.pkl   sbert_titles.npy
└── books/        preprocessed_v2.pkl   sbert_titles.npy
```

These caches are loaded by every experiment script; you only run preprocessing once.

---

## 3. Experiments

Every experiment script writes a JSON results file into `_bestrec_run/`. From `_bestrec_run/`:

### 3.1 Warm Leave-One-Out (Sections 5.1, 5.2)

**Round-5 reproduction path: standalone script, no notebook.** The root notebook is retired from the official package; the archived copy is historical only. The closed-form warm-LOO methods (Popularity, EASE-pure, Higher-Order EASE, EASE+SBERT) are reproduced by a standalone script that also saves canonical per-record audit JSONs:

```bash
cd _bestrec_run
uv run python run_warm_loo.py beauty fashion instruments books
# writes:
#   results_warm_loo.json                          (5-fold summary)
#   results_warm_loo_perfold_<dataset>.json x 4    (dataset, fold, seed, method, user, target, ndcg, hr, rr)
```

These per-fold JSONs are the inputs to the per-user paired Wilcoxon computation in `compute_significance.py` (Table 5.2), so the warm-LOO Wilcoxon path is end-to-end reproducible from released artifacts. The deep baselines (MultiVAE, iALS, LightGCN) still require the repaired SOTA audit before any SOTA claim is allowed.

For Tables 5.1 and 5.2, the canonical sources are `results_FINAL.json`, `significance.json`, and `tables.json`, regenerated via:

```bash
cd _bestrec_run
uv run python compute_significance.py
uv run python consolidate_final.py            # rebuilds results_FINAL.json from current generated artifacts only
uv run python build_tables.py                 # writes tables.json and significance.json
```

The archived notebook is not required to reproduce any paper table or figure.

### 3.2 Cold-item GroupKFold + LC2C (Section 5.5)

```bash
uv run python run_cold_item_v2.py beauty fashion instruments books
```

Produces `results_cold_item_v2.json` with eight methods: `random`, `content_direct`, `content_rating_weighted`, `content_topk`, `lc2c` (V1, SVD+ridge, the legacy LC2C variant), **`lc2c_v2`** (V2, direct ridge with no SVD — the headline LC2C method reported in Table 5.4 of the paper), `cf_hybrid` (V2 + content-direct rank-fusion), and **`dropoutnet`** (a *simplified DropoutNet-style* baseline inspired by Volkovs et al., 2017 — SVD-warm-CF + content fallback; item-tower-only; single-config, single-seed; *not* a faithful reproduction of the original architecture; see paper Table 5.4 caption for the full deviation list). Also writes `results_cold_item_v2_perpair_<dataset>.json` with `(fold_id, user_id, item_id, ndcg)` records for every test pair, used by `compute_significance.py` for per-USER paired Wilcoxon (Table 5.4b) and the user-clustered bootstrap CI.

### 3.4 LC2C component ablation (Section 5.5.1, 5.5.2)

```bash
uv run python run_lc2c_ablation.py beauty fashion instruments books
```

Produces `results_ablation_lc2c.json` with V0/V1/V2/V3 + V1 latent-dim sweep (k = 16, 64, 256). This is the source for Figures 5.5 and 5.6.

### 3.5 Hyperparameter sensitivity (Section 5.4)

```bash
uv run python run_hp_sweep.py beauty fashion instruments books
```

Produces `results_hp_sweep.json` with the 7 × 6 (λ, β) heatmap data for Figure 5.3.

### 3.6 Content embedding ablation (Section 5.6)

```bash
uv run python run_ablation_embeddings.py beauty fashion instruments
```

(Books is omitted; see paper §5.6 caveat.) Produces `results_ablation_embeddings.json` with no-content / random / TF-IDF+SVD / SBERT (Table 5.5, Figure 5.7).

### 3.7 Qualitative case study (Section 5.8 / Table 5.7)

```bash
uv run python case_study.py --dataset books --n-users 8 --n-cands 5
```

Runs LC2C V1 and V2 on the actual Books fold-0 cold-item split, walks through eight held-out users (the eight where V2 most strictly outperforms V1), and prints per-user warm-history samples, target titles, hard-distractor titles, and the content-direct / V1 / V2 ranks. Output is also written to `case_study_output.json` for inclusion in the paper. Use `--dataset {beauty,fashion,instruments,books}` to switch datasets, `--n-users N` to control the number of cases reported, and `--n-cands N` for the candidate-set size.

### 3.8 Canonical Full Sweep

If you want to reproduce the entire paper from scratch:

```bash
uv run python _bestrec_run/run_all.py --profile full --datasets beauty,fashion,instruments,books --seeds 42,43,44,45,46 --allow-internal-report
```

The `--allow-internal-report` flag is currently required because the repaired SOTA audit is intentionally strict: faithful DropoutNet, CLCRec/MELT, BLaIR-style retrieval, tuned LightGCN/MultiVAE, sparse iALS, full-catalog cold-item ranking, and the LC2C++ win condition are not yet complete. Without that flag, `validate_artifacts.py` fails the build rather than allowing a weakened SOTA claim.

---

## 4. Figures and PDF

### 4.1 Regenerate all paper figures

```bash
cd _bestrec_run
uv run python make_figures.py
```

`make_figures.py` is the canonical figure-builder. It reads warm baselines from the single canonical `results_FINAL.json` source and generated cold/ablation JSONs. The legacy `make_figures_v3.py` is not invoked by the canonical reproduction path.

This writes PNG + PDF figures into `_bestrec_run/figures/`. There is also a copy in the project-root `figures/` directory used by the paper builder.

To copy fresh figures into the unified root-level `figures/` folder (used by the paper PDF):

```bash
cp _bestrec_run/figures/*.png figures/
cp _bestrec_run/figures/*.pdf figures/
```

### 4.2 Regenerate the architecture diagram (Figure 3.1)

```bash
uv run python _paper_gen/make_arch_v3.py
```

Writes `figures/fig_architecture_overview.{png,pdf}`.

### 4.3 Build the full paper PDF

```bash
uv run python _paper_gen/build_paper_full.py
```

Writes `BEST_Rec_v4_Full_Paper.pdf` (40 pages, ~1.5 MB) at the project root.

---

## 5. Common issues

### "ModuleNotFoundError: No module named 'pypdf'"
The verification helper used in `_paper_gen/build_paper_full.py` doesn't need `pypdf`, but if you want to inspect the generated PDF programmatically:
```bash
cd _bestrec_run
uv pip install pypdf
```

### "RuntimeError: CUDA out of memory" on LightGCN (Books)
The repaired LightGCN audit should be run through the scripted SOTA baseline harness. If the legacy implementation OOMs, reduce the batch size in the script configuration or run on CPU by setting `CUDA_VISIBLE_DEVICES=` before launching the script.

### "FileNotFoundError: data/beauty/All_Beauty.jsonl"
The Amazon Reviews 2023 raw files are not redistributed in this repository. Download them from <https://amazon-reviews-2023.github.io/> and place them as described in §2.1.

### "iALS on Books: OOM"
Expected (this is the OOM† footnote in Table 5.2). Skipped intentionally with a 64 GB memory budget. Either run on a machine with ≥128 GB RAM or accept the OOM entry as in the paper.

### Reproducibility seed
All runs use `SEED = 42` (defined in `v5_utils.py`). Two runs of the same script on the same machine produce bit-identical results. Different machines may produce results that differ in the last 2–3 decimal digits because of BLAS implementation differences in the Cholesky factorization; the published numbers were produced on Intel MKL.

### Single-dataset quick start
The fastest way to verify the cold-item pipeline works end-to-end is on Beauty (~5 minutes total):

```bash
cd _bestrec_run
uv run python preprocess_v2.py beauty
uv run python run_cold_item_v2.py beauty
uv run python compute_significance.py
uv run python consolidate_final.py
uv run python build_tables.py
uv run python make_figures.py
```

For the warm-LOO numbers (Tables 5.1 and 5.2), run `uv run python run_warm_loo.py beauty` before consolidation.

---

## 6. Where each result in the paper comes from

| Paper element | Source script | Source JSON |
|---|---|---|
| Table 4.1 (dataset stats) | `preprocess_v2.py` | (printed to stdout) |
| Table 4.2 (test-set sizes) | `build_tables.py` | `tables.json` from actual record counts |
| Table 5.1 + 5.2 (warm-LOO) | `run_warm_loo.py` -> `compute_significance.py` -> `consolidate_final.py` -> `build_tables.py` | `results_warm_loo.json`, `results_FINAL.json`, `significance.json`, `tables.json` |
| SOTA audit status | `build_tables.py` | `tables.json::sota_audit` |
| Table 5.2 Holm markers (warm-LOO) | `compute_significance.py` | `significance.json` |
| Table 5.4 + Figure 5.4 (cold-item, with simplified DropoutNet-style) | `run_cold_item_v2.py` | `results_cold_item_v2.json` |
| Table 5.4b (per-USER cold-item Wilcoxon + user-clustered bootstrap CI) | `compute_significance.py` reads `results_cold_item_v2_perpair_<dataset>.json` | `significance_cold_item_corrected.json` |
| Table 5.5 + Figure 5.7 (embedding ablation) | `run_ablation_embeddings.py` | `results_ablation_embeddings.json` |
| Table 5.6 (compute cost) | (manually recorded from each script's stdout) | — |
| Table 5.7 (qualitative case study) | `case_study.py --dataset books` | `case_study_output.json` |
| Figure 3.1 (architecture) | `_paper_gen/make_arch_v3.py` | — |
| Figure 5.1 (warm methods × datasets) | `make_figures.py` | `results_FINAL.json` (canonical) |
| Figure 5.2 (vs. LightGCN, round-4 regenerated) | `make_figures.py` | `results_FINAL.json` (canonical, single source) |
| Figure 5.3 (HP sensitivity heatmap) | `make_figures.py` | `results_hp_sweep.json` |
| Figure 5.5 (LC2C component ablation) | `make_figures.py` | `results_ablation_lc2c.json` |
| Figure 5.6 (LC2C latent dim) | `make_figures.py` | `results_ablation_lc2c.json` |

---

## 7. Citation

If you use BEST-Rec v4 in your own work, please cite:

```bibtex
@misc{bestrec_v4_2026,
  title = {BEST-Rec v4: SBERT-Augmented EASE with Learned Content-to-CF Mapping for Cold-Item Recommendation},
  author = {<author names>},
  year = {2026},
  note = {Working paper},
}
```
