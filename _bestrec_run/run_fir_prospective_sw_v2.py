#!/usr/bin/env python3
"""Clean-commit sequestered driver for prospective Software FIR V2."""

from __future__ import annotations

import hashlib
import csv
import json
import os
import subprocess
import sys
import time
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PY = sys.executable
TRAINER = HERE / "run_sasrec_sbert_software_v2_frozen.py"
EVALUATOR = HERE / "eval_fir_prospective_sw_v2.py"
STRUCTURAL_TEST = HERE / "test_fir_pointwise_v1.py"
REF = HERE / "results_MI_V2_ls02_filter16_seed20260608.json"
CATEGORY = "Software"
PROTOCOL = "PREREG_FIR_PROSPECTIVE_SW_V2"
ARMS = ("identity", "learned")
SEEDS = tuple(range(20261201, 20261209))
KERNEL = 16
STATUS = HERE / "fir_prospective_sw_v2_status.json"
EXPECTED_INPUT_SHA256 = {
    "data_5core/5core/last_out/Software.train.csv": "731c567c20b9cc58ee1270c3e281720f1a50b6e5d24c0494fa31861f17798246",
    "data_5core/5core/last_out/Software.valid.csv": "3f42eb8e0fe8b54cc4ad854755da29f455540c4a787eaa2744f36864944733c3",
    "data_5core/5core/last_out/Software.test.csv": "9e520fff20359a0fc130c8df7c4898f448aa140a90dffd82a64a60192574f863",
    "cache_5core/sbert_titles_Software.npy": "2a1d09dea26c9c619a6d52ba2082c58ac23c03a04a7f02be30f5e9441098aa38",
    "cache_5core/asin2idx_Software.json": "62e6a129e39dcead62922e096d6a36eef2527668a7bb8791822127440d36c7ae",
}
EXCLUDE = {
    "category", "seed", "out", "causal_filter", "filter_kernel",
    "filter_fixed_avg", "filter_no_gate", "fir_v3", "fir_v3_kernel",
    "fir_v3_wd", "fir_control", "fir_control_kernel", "no_test_eval",
    "save_ckpt",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def git_output(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def assert_custody(expected_head: str | None = None) -> str:
    head = git_output("rev-parse", "HEAD")
    if expected_head is not None and head != expected_head:
        raise RuntimeError(f"execution Git HEAD changed: {head} != {expected_head}")
    dirty = git_output("status", "--porcelain", "--untracked-files=no")
    if dirty:
        raise RuntimeError("tracked execution tree is dirty")
    return head


def base_args() -> list[str]:
    cfg = json.loads(REF.read_text(encoding="utf-8"))["config"]
    argv: list[str] = []
    for key in sorted(cfg):
        if key in EXCLUDE:
            continue
        value = cfg[key]
        if value is None or value is False:
            continue
        flag = "--" + key.replace("_", "-")
        argv += [flag] if value is True else [flag, str(value)]
    return argv


def path_for(arm: str, seed: int) -> Path:
    return HERE / f"results_{CATEGORY}_FIRPROSPV2_{arm}_seed{seed}.json"


def train_cmd(arm: str, seed: int, head: str) -> list[str]:
    return [PY, str(TRAINER), CATEGORY] + base_args() + [
        "--fir-control", arm,
        "--fir-control-kernel", str(KERNEL),
        "--no-test-eval", "--save-ckpt",
        "--seed", str(seed), "--out", str(path_for(arm, seed)),
        "--prospective-protocol", PROTOCOL,
        "--execution-git-head", head,
    ]


def all_training_ready() -> bool:
    return all(path_for(arm, seed).is_file()
               and path_for(arm, seed).with_suffix(".best.pt").is_file()
               for seed in SEEDS for arm in ARMS)


def validate_training_json(path: Path, arm: str, seed: int, head: str) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cfg = payload.get("config", {})
    custody = payload.get("prospective_custody", {})
    if (cfg.get("category") != CATEGORY or cfg.get("seed") != seed
            or cfg.get("fir_control") != arm or cfg.get("fir_control_kernel") != KERNEL
            or not cfg.get("no_test_eval") or not cfg.get("save_ckpt")
            or payload.get("best_test") is not None
            or any("test" in epoch for epoch in payload.get("history", []))
            or custody.get("protocol") != PROTOCOL
            or custody.get("execution_git_head") != head):
        raise RuntimeError(f"training artifact violates frozen boundary: {path.name}")


def preflight() -> str:
    head = assert_custody()
    for path in (TRAINER, EVALUATOR, STRUCTURAL_TEST, REF):
        if not path.is_file():
            raise RuntimeError(f"missing protocol file: {path}")
    for rel, expected in EXPECTED_INPUT_SHA256.items():
        path = ROOT / rel
        if not path.is_file() or sha256(path) != expected:
            raise RuntimeError(f"frozen input mismatch: {rel}")
    items: set[str] = set()
    for split in ("train", "valid", "test"):
        with (ROOT / "data_5core" / "5core" / "last_out" /
              f"Software.{split}.csv").open("r", encoding="utf-8", newline="") as fh:
            items.update(row["parent_asin"] for row in csv.DictReader(fh))
    item_map = json.loads((ROOT / "cache_5core" /
                           "asin2idx_Software.json").read_text(encoding="utf-8"))
    if item_map != {item: index for index, item in enumerate(sorted(items))}:
        raise RuntimeError("frozen Software item map is not the sorted split union")
    test = subprocess.run([PY, str(STRUCTURAL_TEST)], cwd=ROOT)
    if test.returncode:
        raise RuntimeError("structural test failed")
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    helptext = subprocess.run(
        [PY, str(TRAINER), "--help"], capture_output=True, text=True,
        env=env, encoding="utf-8", cwd=ROOT).stdout or ""
    bad = sorted({flag for flag in train_cmd(ARMS[0], SEEDS[0], head)
                  if flag.startswith("--") and flag not in helptext
                  and flag not in {"--prospective-protocol", "--execution-git-head"}})
    if bad:
        raise RuntimeError(f"unknown frozen trainer flags: {bad}")
    if STATUS.exists():
        old = json.loads(STATUS.read_text(encoding="utf-8"))
        if old.get("execution_git_head") != head:
            raise RuntimeError("existing status belongs to a different Git HEAD")
    print(f"PREFLIGHT OK: {len(ARMS)} arms x {len(SEEDS)} seeds; HEAD={head}")
    print("first command:\n ", " ".join(train_cmd(ARMS[0], SEEDS[0], head)))
    return head


def write_status(state: str, counters: dict[str, int], t0: float, head: str) -> None:
    payload = {
        "protocol": PROTOCOL,
        "state": state,
        **counters,
        "total": len(ARMS) * len(SEEDS),
        "elapsed_min": round((time.time() - t0) / 60, 1),
        "execution_git_head": head,
        "input_sha256": EXPECTED_INPUT_SHA256,
    }
    tmp = STATUS.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")
    os.replace(tmp, STATUS)


def main() -> int:
    head = preflight()
    if "--preflight" in sys.argv:
        return 0
    t0 = time.time()
    counters = {"trained": 0, "skipped_train": 0, "evaluated": 0, "skipped_eval": 0}
    total = len(ARMS) * len(SEEDS)
    for seed in SEEDS:
        for arm in ARMS:
            assert_custody(head)
            out = path_for(arm, seed)
            ckpt = out.with_suffix(".best.pt")
            if out.exists():
                if not ckpt.exists():
                    raise RuntimeError(f"run JSON without checkpoint: {out}")
                validate_training_json(out, arm, seed, head)
                counters["skipped_train"] += 1
                print(f"[train skip {counters['trained'] + counters['skipped_train']}/{total}] {out.name}", flush=True)
            else:
                print(f"[train {counters['trained'] + counters['skipped_train'] + 1}/{total}] {out.name}", flush=True)
                child = subprocess.run(train_cmd(arm, seed, head), cwd=ROOT)
                if child.returncode:
                    write_status("train_failed", counters, t0, head)
                    return child.returncode
                validate_training_json(out, arm, seed, head)
                counters["trained"] += 1
            write_status("training", counters, t0, head)

    if not all_training_ready():
        raise RuntimeError("not all training artifacts exist before TEST phase")
    for seed in SEEDS:
        for arm in ARMS:
            assert_custody(head)
            out = path_for(arm, seed)
            validate_training_json(out, arm, seed, head)
            final = out.with_suffix(".finaleval.json")
            seal = out.with_suffix(".finaleval.started.json")
            if final.exists():
                counters["skipped_eval"] += 1
                print(f"[eval skip {counters['evaluated'] + counters['skipped_eval']}/{total}] {final.name}", flush=True)
            elif seal.exists():
                write_status("eval_seal_incomplete", counters, t0, head)
                raise RuntimeError(f"incomplete one-shot seal: {seal}")
            else:
                print(f"[eval {counters['evaluated'] + counters['skipped_eval'] + 1}/{total}] {out.name}", flush=True)
                child = subprocess.run([PY, str(EVALUATOR), str(out)], cwd=ROOT)
                if child.returncode:
                    write_status("eval_failed", counters, t0, head)
                    return child.returncode
                counters["evaluated"] += 1
            write_status("evaluating", counters, t0, head)
    write_status("complete", counters, t0, head)
    print(f"{PROTOCOL} COMPLETE: {counters}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"INTEGRITY FAIL: {exc}", file=sys.stderr)
        raise SystemExit(2)
