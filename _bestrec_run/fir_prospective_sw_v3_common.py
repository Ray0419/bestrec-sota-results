#!/usr/bin/env python3
"""Shared fail-closed boundary for prospective Software FIR V3."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
TAG = "fir-prospective-sw-v3-freeze"
PROTOCOL = "PREREG_FIR_PROSPECTIVE_SW_V3"
CATEGORY = "Software"
ARMS = ("identity", "learned")
SEEDS = tuple(range(20261301, 20261309))
KERNEL = 16
PRACTICAL = 0.0005
ALPHA = 0.05

TRAINER = HERE / "run_sasrec_sbert_software_v3_frozen.py"
BASE_TRAINER = HERE / "run_sasrec_sbert_pointwise_v1_frozen.py"
MODEL_BUILDER = HERE / "fuse_ease_eval.py"
STRUCTURAL_TEST = HERE / "test_fir_pointwise_v1.py"
DRIVER = HERE / "run_fir_prospective_sw_v3.py"
EVALUATOR = HERE / "eval_fir_prospective_sw_v3.py"
ADJUDICATOR = HERE / "adjudicate_fir_prospective_sw_v3.py"
PREREG = ROOT / "PREREG_FIR_PROSPECTIVE_SW_V3.md"
ENVIRONMENT = HERE / "fir_prospective_sw_v3_environment.json"
ATTEMPT = HERE / "fir_prospective_sw_v3_attempt.json"
READY = HERE / "fir_prospective_sw_v3_ready.json"
ENDPOINTS_COMPLETE = HERE / "fir_prospective_sw_v3_endpoints_complete.json"
STATUS = HERE / "fir_prospective_sw_v3_status.json"
LOCK = HERE / "fir_prospective_sw_v3.lock"
ADJUDICATION = HERE / "fir_prospective_sw_v3_adjudication.json"

# Every local executable/model-building dependency is compared byte-for-byte
# with the immutable Git tag before every child phase. The adjudicator includes
# itself, so it performs a Git-object-backed self-integrity check.
FROZEN_FILES = (
    "PREREG_FIR_PROSPECTIVE_SW_V3.md",
    "PREREG_FIR_PROSPECTIVE_SW_V2_PREPARATION.md",
    "FIR_PROSPECTIVE_SW_V2_INTEGRITY.md",
    "_bestrec_run/fir_prospective_sw_v3_common.py",
    "_bestrec_run/fir_prospective_sw_v3_environment.json",
    "_bestrec_run/run_sasrec_sbert_pointwise_v1_frozen.py",
    "_bestrec_run/run_sasrec_sbert.py",
    "_bestrec_run/run_sasrec_sbert_software_v3_frozen.py",
    "_bestrec_run/fuse_ease_eval.py",
    "_bestrec_run/test_fir_pointwise_v1.py",
    "_bestrec_run/run_fir_prospective_sw_v3.py",
    "_bestrec_run/eval_fir_prospective_sw_v3.py",
    "_bestrec_run/adjudicate_fir_prospective_sw_v3.py",
    "_bestrec_run/pyproject.toml",
    "_bestrec_run/uv.lock",
    "_bestrec_run/software_feasibility.json",
    "_bestrec_run/software_acquisition_manifest.json",
    "_bestrec_run/software_title_cache_manifest.json",
)

EXPECTED_INPUT_SHA256 = {
    "data_5core/5core/last_out/Software.train.csv": "731c567c20b9cc58ee1270c3e281720f1a50b6e5d24c0494fa31861f17798246",
    "data_5core/5core/last_out/Software.valid.csv": "3f42eb8e0fe8b54cc4ad854755da29f455540c4a787eaa2744f36864944733c3",
    "data_5core/5core/last_out/Software.test.csv": "9e520fff20359a0fc130c8df7c4898f448aa140a90dffd82a64a60192574f863",
    "cache_5core/sbert_titles_Software.npy": "2a1d09dea26c9c619a6d52ba2082c58ac23c03a04a7f02be30f5e9441098aa38",
    "cache_5core/asin2idx_Software.json": "62e6a129e39dcead62922e096d6a36eef2527668a7bb8791822127440d36c7ae",
}

EXPECTED_REFERENCE_SHA256 = {
    "_bestrec_run/results_MI_V2_ls02_filter16_seed20260608.json": "a230d17cd4e1683ac0e07e64702587950baf89374083521850c96daeede1ab72",
    "_bestrec_run/software_feasibility.json": "54d8c6ae086a51ba784f038c438761105634f988ea85ba3c2b65e63f9b8b960d",
    "_bestrec_run/software_acquisition_manifest.json": "e234452c682b81c21e81efbdb689831ba19971031b6247c261086215f4da2255",
    "_bestrec_run/software_title_cache_manifest.json": "022aafce6a98e12e43009d4613df4796a2b0850f0326f33ae927e76548fb7b63",
}

# Literal normalized configuration: no result file is consulted at runtime.
BASE_ARGS = (
    "--augment-factor", "1",
    "--batch-size", "256",
    "--chunked-full-softmax",
    "--cl-mask-prob", "0.3",
    "--cl-tau", "1.0",
    "--cl-weight", "0.0",
    "--d-model", "64",
    "--dropout", "0.5",
    "--ema-decay", "0.0",
    "--encoder", "hstu",
    "--epochs", "20",
    "--eval-every", "1",
    "--eval-subsample", "0",
    "--expert-heads", "0",
    "--item-chunk", "32768",
    "--label-smoothing", "0.2",
    "--lr", "0.001",
    "--lr-schedule", "warmup_cosine",
    "--max-seq-len", "50",
    "--mlp-dropout", "0.2",
    "--mlp-hidden", "300",
    "--n-heads", "2",
    "--n-layers", "4",
    "--niche-share-beta", "0.0",
    "--pos-rab",
    "--proto-tau", "0.05",
    "--sampled-negs", "0",
    "--score-temp", "0.05",
    "--text-distill-weight", "0.0",
    "--text-prototypes", "512",
    "--text-sim-bias",
    "--time-bias",
    "--time-decay-bases", "8",
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def json_sha(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def git_bytes(*args: str) -> bytes:
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True)
    if result.returncode:
        raise RuntimeError(
            f"git {' '.join(args)} failed: "
            f"{result.stderr.decode(errors='replace').strip()}")
    return result.stdout


def git_text(*args: str) -> str:
    return git_bytes(*args).decode("utf-8").strip()


def tagged_head() -> str:
    return git_text("rev-parse", f"{TAG}^{{}}")


def assert_tagged_tree() -> str:
    head = git_text("rev-parse", "HEAD")
    frozen = tagged_head()
    if head != frozen:
        raise RuntimeError(f"execution HEAD {head} is not frozen tag target {frozen}")
    if git_text("status", "--porcelain", "--untracked-files=no"):
        raise RuntimeError("tracked execution tree is dirty")
    for rel in FROZEN_FILES:
        path = ROOT / rel
        if not path.is_file():
            raise RuntimeError(f"missing frozen file: {rel}")
        if path.read_bytes() != git_bytes("show", f"{TAG}:{rel}"):
            raise RuntimeError(f"worktree differs from frozen Git object: {rel}")
    return head


def environment_snapshot() -> dict:
    import numpy as np
    import scipy
    import torch

    return {
        "python": ".".join(map(str, sys.version_info[:3])),
        "implementation": sys.implementation.name,
        "torch": torch.__version__,
        "torch_cuda": torch.version.cuda,
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "cuda_available": bool(torch.cuda.is_available()),
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
    }


def assert_environment() -> dict:
    expected = json.loads(ENVIRONMENT.read_text(encoding="utf-8"))
    actual = environment_snapshot()
    if actual != expected["runtime"]:
        raise RuntimeError(f"runtime environment mismatch: {actual} != {expected['runtime']}")
    for rel, digest in expected["lock_sha256"].items():
        if sha256(ROOT / rel) != digest:
            raise RuntimeError(f"environment lock mismatch: {rel}")
    return actual


def assert_inputs() -> None:
    for rel, expected in {**EXPECTED_INPUT_SHA256,
                          **EXPECTED_REFERENCE_SHA256}.items():
        path = ROOT / rel
        if not path.is_file() or sha256(path) != expected:
            raise RuntimeError(f"frozen input/reference mismatch: {rel}")


def path_for(arm: str, seed: int) -> Path:
    return HERE / f"results_{CATEGORY}_FIRPROSPV3_{arm}_seed{seed}.json"


def ordered_jobs() -> list[tuple[str, int]]:
    jobs: list[tuple[str, int]] = []
    for index, seed in enumerate(SEEDS):
        order = ARMS if index % 2 == 0 else tuple(reversed(ARMS))
        jobs.extend((arm, seed) for arm in order)
    return jobs


def expected_trainer_argv(arm: str, seed: int, out: Path | None = None) -> list[str]:
    if arm not in ARMS or seed not in SEEDS:
        raise RuntimeError("arm/seed is outside frozen V3")
    target = (out or path_for(arm, seed)).resolve()
    return [CATEGORY, *BASE_ARGS,
            "--fir-control", arm,
            "--fir-control-kernel", str(KERNEL),
            "--no-test-eval", "--save-ckpt",
            "--seed", str(seed), "--out", str(target),
            "--prospective-protocol", PROTOCOL,
            "--execution-git-tag", TAG]


def train_cmd(arm: str, seed: int) -> list[str]:
    return [sys.executable, str(TRAINER), *expected_trainer_argv(arm, seed)]


def atomic_json_x(path: Path, payload: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("x", encoding="utf-8", newline="\n") as fh:
        json.dump(payload, fh, indent=2, allow_nan=False)
        fh.write("\n")
    os.replace(tmp, path)


def load_attempt() -> tuple[dict, str]:
    if not ATTEMPT.is_file():
        raise RuntimeError("immutable V3 attempt seal is missing")
    payload = json.loads(ATTEMPT.read_text(encoding="utf-8"))
    if (payload.get("protocol") != PROTOCOL
            or payload.get("execution_git_head") != tagged_head()
            or payload.get("jobs") != [[arm, seed] for arm, seed in ordered_jobs()]):
        raise RuntimeError("attempt seal mismatch")
    return payload, sha256(ATTEMPT)


def load_ready() -> tuple[dict, str]:
    if not READY.is_file():
        raise RuntimeError("immutable V3 READY seal is missing")
    payload = json.loads(READY.read_text(encoding="utf-8"))
    if payload.get("protocol") != PROTOCOL or payload.get("attempt_sha256") != sha256(ATTEMPT):
        raise RuntimeError("READY seal mismatch")
    return payload, sha256(READY)
