# Reproducibility Environment

## Outcome-run interpreter

`C:\Users\rayxc\Documents\R\_bestrec_run\.venv\Scripts\python.exe`

The outcome run invokes this interpreter directly with `python.exe -u`; it does not use `uv run`.

## Verified packages

| Component | Version |
|---|---:|
| Python | 3.12.13 |
| NumPy | 2.4.4 |
| pandas | 3.0.3 |
| SciPy | 1.17.1 |
| scikit-learn | 1.8.0 |
| PyTorch | 2.11.0+cu128 (CPU execution) |
| sentence-transformers | 5.4.1 |
| FAISS CPU | 1.15.0 |

`sentence-transformers/all-MiniLM-L6-v2` was verified from the local Hugging Face cache with offline loading; its output dimension is 384 and normalized test output had squared norm 1.0.

## Deterministic CPU contract

Before importing NumPy, SciPy, scikit-learn, Torch, or FAISS, the launcher sets:

```text
OMP_NUM_THREADS=1
MKL_NUM_THREADS=1
OPENBLAS_NUM_THREADS=1
NUMEXPR_NUM_THREADS=1
VECLIB_MAXIMUM_THREADS=1
BLIS_NUM_THREADS=1
CUDA_VISIBLE_DEVICES=-1
HF_HUB_OFFLINE=1
PYTHONHASHSEED=<registered seed>
```

The runner additionally calls `torch.set_num_threads(1)`, `torch.set_num_interop_threads(1)`, and `faiss.omp_set_num_threads(1)`. Data loaders use zero workers.

## Dataset source

MovieLens 100K is downloaded only from the official GroupLens endpoint and cached under `data/`. The runner records the downloaded archive checksum and extracted input checksums. GroupLens describes the stable benchmark as 100,000 ratings from 943 users on 1,682 movies and supplies timestamps, titles, and 19 genre indicators: https://grouplens.org/datasets/movielens/100k/

## Isolation and completion

Each attempt receives a unique run directory. The runner acquires an experiment-specific exclusive lock, installs asynchronous exception hooks, appends errors to a ledger, and writes a completion marker only after result artifacts and hashes exist. It never overwrites another attempt's outputs.
