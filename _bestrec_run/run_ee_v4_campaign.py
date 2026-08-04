#!/usr/bin/env python3
"""Fail-closed driver for the frozen PREREG_EE_V4 sensitivity campaign."""

from __future__ import annotations

import argparse
import subprocess
import sys

import ee_v4_common as common


FROZEN_FILES = (
    "PREREG_EE_V4.md",
    "_bestrec_run/ee_v3_common.py",
    "_bestrec_run/adjudicate_ee_v3.py",
    "_bestrec_run/ee_v3_adjudication.json",
    "_bestrec_run/ee_v4_common.py",
    "_bestrec_run/test_ee_v4.py",
    "_bestrec_run/run_ee_v4.py",
    "_bestrec_run/eval_ee_v4.py",
    "_bestrec_run/adjudicate_ee_v4.py",
    "_bestrec_run/run_ee_v4_campaign.py",
)


def run(script: str, *args: str) -> None:
    command = [sys.executable, str(common.HERE / script), *args]
    completed = subprocess.run(command, cwd=common.ROOT, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"subprocess failed ({completed.returncode}): {' '.join(command)}")


def frozen_sources_ok() -> None:
    for rel in FROZEN_FILES:
        tracked = subprocess.run(
            ["git", "ls-files", "--error-unmatch", rel], cwd=common.ROOT,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        clean = subprocess.run(
            ["git", "diff", "--quiet", "HEAD", "--", rel], cwd=common.ROOT,
            check=False)
        if tracked.returncode != 0 or clean.returncode != 0:
            raise RuntimeError(f"E-E V4 source is not committed/frozen at HEAD: {rel}")


def status_value(state: str, trained: int, evaluated: int,
                 errors: list[str]) -> dict[str, object]:
    return {
        "protocol": common.PROTOCOL,
        "state": state,
        "repository_commit": common.repository_head(),
        "training_complete": trained,
        "assessment_complete": evaluated,
        "total": len(common.expected_pairs()),
        "training_concurrency": 2,
        "errors": errors,
        "updated_utc": common.utc_now(),
    }


def counts_by_presence() -> tuple[int, int]:
    trained = sum(common.training_path(a, s).is_file()
                  and common.best_path(a, s).is_file()
                  for a, s in common.expected_pairs())
    evaluated = sum(common.endpoint_path(a, s).is_file()
                    and common.endpoint_users_path(a, s).is_file()
                    and common.endpoint_seal_path(a, s).is_file()
                    for a, s in common.expected_pairs())
    return int(trained), int(evaluated)


def exact_private_names_ok() -> None:
    common.PRIVATE.mkdir(parents=True, exist_ok=True)
    allowed = {common.READY.name}
    for arm, seed in common.expected_pairs():
        allowed.update({
            common.started_path(arm, seed).name,
            common.latest_path(arm, seed).name,
            common.best_path(arm, seed).name,
            common.training_path(arm, seed).name,
            common.endpoint_seal_path(arm, seed).name,
            common.endpoint_users_path(arm, seed).name,
            common.endpoint_path(arm, seed).name,
        })
    unexpected = sorted(p.name for p in common.PRIVATE.iterdir() if p.name not in allowed)
    if unexpected:
        raise RuntimeError(f"unexpected E-E V4 private artifacts: {unexpected}")


def preflight(*, new_campaign: bool) -> None:
    frozen_sources_ok()
    common.verify_upstream()
    common.verify_data(include_test=False)
    exact_private_names_ok()
    if (not common.EEV3_ADJUDICATION.is_file()
            or common.sha256(common.EEV3_ADJUDICATION)
            != common.EEV3_ADJUDICATION_SHA256):
        raise RuntimeError("frozen public E-E V3 adjudication identity mismatch")
    if common.ADJUDICATION.exists():
        if new_campaign:
            raise RuntimeError("E-E V4 public adjudication exists without campaign status")
        prior_status = common.load_json(common.STATUS)
        if (prior_status.get("state") not in {
                "endpoints_complete_adjudicating", "complete", "failed"}
                or counts_by_presence() != (len(common.SEEDS), len(common.SEEDS))):
            raise RuntimeError("E-E V4 adjudication exists outside a completed endpoint family")
    if new_campaign:
        if common.STATUS.exists() or common.READY.exists():
            raise RuntimeError("new E-E V4 campaign has prior status/READY artifact")
        for arm, seed in common.expected_pairs():
            prior = [p.name for p in (
                common.started_path(arm, seed), common.latest_path(arm, seed),
                common.best_path(arm, seed), common.training_path(arm, seed),
                common.endpoint_seal_path(arm, seed), common.endpoint_users_path(arm, seed),
                common.endpoint_path(arm, seed)) if p.exists()]
            if prior:
                raise RuntimeError(f"fresh seed {arm}/{seed} has prior artifacts: {prior}")
    run("test_ee_v4.py")


def validate_resume_status() -> None:
    status = common.load_json(common.STATUS)
    if (status.get("protocol") != common.PROTOCOL
            or status.get("repository_commit") != common.repository_head()
            or status.get("total") != len(common.expected_pairs())
            or status.get("training_concurrency") != 2
            or status.get("state") not in {"training", "evaluating", "failed",
                                           "endpoints_complete_adjudicating", "complete"}):
        raise RuntimeError("E-E V4 resume status drift")


def train_wave(seeds: tuple[int, ...]) -> None:
    arm = common.ARMS[0]
    processes: list[tuple[int, subprocess.Popen[bytes]]] = []
    for seed in seeds:
        terminal = common.training_path(arm, seed)
        if terminal.exists():
            common.validate_training_bundle(arm, seed)
            continue
        command = [sys.executable, str(common.HERE / "run_ee_v4.py"),
                   "--arm", arm, "--seed", str(seed)]
        processes.append((seed, subprocess.Popen(command, cwd=common.ROOT)))
    failures = []
    for seed, process in processes:
        code = process.wait()
        if code != 0:
            failures.append(f"seed {seed} exited {code}")
    if failures:
        raise RuntimeError("concurrent training wave failed: " + "; ".join(failures))
    for seed in seeds:
        common.validate_training_bundle(arm, seed)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    new_campaign = not common.STATUS.exists()
    preflight(new_campaign=new_campaign)
    if args.preflight_only:
        print("PREREG_EE_V4 committed-source preflight: PASS")
        return 0
    if not new_campaign:
        validate_resume_status()
        if common.ADJUDICATION.is_file():
            trained, evaluated = counts_by_presence()
            final = status_value("complete", trained, evaluated, [])
            final["adjudication_sha256"] = common.sha256(common.ADJUDICATION)
            common.atomic_json(common.STATUS, final)
            print("PREREG_EE_V4 CAMPAIGN ALREADY ADJUDICATED; STATUS FINALIZED")
            return 0

    trained, evaluated = counts_by_presence()
    common.atomic_json(common.STATUS, status_value("training", trained, evaluated, []))
    try:
        for wave in common.TRAIN_WAVES:
            train_wave(wave)
            trained, evaluated = counts_by_presence()
            common.atomic_json(
                common.STATUS, status_value("training", trained, evaluated, []))

        expected_ready = common.ready_payload()
        if common.READY.exists():
            if common.load_json(common.READY) != expected_ready:
                raise RuntimeError("existing family READY record drift")
        else:
            common.exclusive_json(common.READY, expected_ready)
        common.atomic_json(common.STATUS, status_value(
            "evaluating", len(common.SEEDS), evaluated, []))

        arm = common.ARMS[0]
        for seed in common.SEEDS:
            artifacts = (common.endpoint_seal_path(arm, seed),
                         common.endpoint_users_path(arm, seed),
                         common.endpoint_path(arm, seed))
            present = [p.exists() for p in artifacts]
            if any(present) and not all(present):
                raise RuntimeError(
                    f"incomplete sealed TEST attempt; no rerun allowed: {arm}/{seed}")
            if not all(present):
                run("eval_ee_v4.py", "--arm", arm, "--seed", str(seed))
            trained, evaluated = counts_by_presence()
            common.atomic_json(
                common.STATUS, status_value("evaluating", trained, evaluated, []))

        trained, evaluated = counts_by_presence()
        total = len(common.SEEDS)
        if (trained, evaluated) != (total, total):
            raise RuntimeError(f"family completion count mismatch: {(trained, evaluated)}")
        common.atomic_json(common.STATUS, status_value(
            "endpoints_complete_adjudicating", total, total, []))
        run("adjudicate_ee_v4.py")
        if not common.ADJUDICATION.is_file():
            raise RuntimeError("adjudicator returned without a public adjudication")
        final = status_value("complete", total, total, [])
        final["adjudication_sha256"] = common.sha256(common.ADJUDICATION)
        common.atomic_json(common.STATUS, final)
        print("PREREG_EE_V4 CAMPAIGN COMPLETE AND ADJUDICATED")
        return 0
    except Exception as exc:
        trained, evaluated = counts_by_presence()
        common.atomic_json(
            common.STATUS, status_value("failed", trained, evaluated, [str(exc)]))
        raise


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"E-E V4 CAMPAIGN FAILURE: {exc}", file=sys.stderr, flush=True)
        raise
