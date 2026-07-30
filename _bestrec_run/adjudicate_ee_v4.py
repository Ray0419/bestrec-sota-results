#!/usr/bin/env python3
"""First authorized endpoint reader and adjudicator for PREREG_EE_V4."""

from __future__ import annotations

import json
import sys

import numpy as np

import adjudicate_ee_v3 as shared
import ee_v4_common as common


# Reuse the already-tested endpoint/schema arithmetic against the V4 namespace.
shared.common = common


def fail(message: str) -> None:
    raise RuntimeError(message)


def main() -> int:
    if common.ADJUDICATION.exists():
        fail("refusing to overwrite existing E-E V4 adjudication")
    status = common.load_json(common.STATUS)
    expected_status = {
        "protocol": common.PROTOCOL,
        "state": "endpoints_complete_adjudicating",
        "repository_commit": common.repository_head(),
        "training_complete": len(common.SEEDS),
        "assessment_complete": len(common.SEEDS),
        "total": len(common.SEEDS),
        "training_concurrency": 2,
        "errors": [],
    }
    for key, value in expected_status.items():
        if status.get(key) != value:
            fail(f"campaign status is not adjudication-ready: {key}")
    if set(status) != set(expected_status) | {"updated_utc"}:
        fail("campaign status schema drift")
    ready = common.load_json(common.READY)
    if ready != common.ready_payload():
        fail("READY record drift before first endpoint read")
    ready_sha = common.sha256(common.READY)

    endpoints: dict[int, dict[str, object]] = {}
    ledger: list[dict[str, object]] = []
    arm = common.ARMS[0]
    for _, seed in common.expected_pairs():
        endpoint, _ = shared.load_endpoint(arm, seed, ready, ready_sha)
        endpoints[seed] = endpoint
        ledger.append({
            "arm": arm,
            "seed": seed,
            "endpoint_file": common.endpoint_path(arm, seed).name,
            "endpoint_sha256": common.sha256(common.endpoint_path(arm, seed)),
            "sidecar_file": common.endpoint_users_path(arm, seed).name,
            "sidecar_sha256": common.sha256(common.endpoint_users_path(arm, seed)),
        })

    summary: dict[str, object] = {}
    for metric in ("NDCG@10", "HR@10", "MRR"):
        summary[metric] = shared.mean_sd_ci([
            float(endpoints[seed]["metrics"][metric]) for seed in common.SEEDS])

    if (not common.EEV3_ADJUDICATION.is_file()
            or common.sha256(common.EEV3_ADJUDICATION)
            != common.EEV3_ADJUDICATION_SHA256):
        fail("public E-E V3 adjudication identity drift")
    prior = common.load_json(common.EEV3_ADJUDICATION)
    try:
        alpha_zero = [float(x) for x in
                      prior["arm_seed_summaries"]["alphafuse_package"]["NDCG@10"]["vector"]]
        sasrec_zero = [float(x) for x in
                       prior["arm_seed_summaries"]["sasrec_id"]["NDCG@10"]["vector"]]
        reference = [float(x) for x in prior["existing_paper_reference"]["NDCG@10"]["vector"]]
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError("public E-E V3 aggregate schema drift") from exc
    if len(alpha_zero) != 8 or len(sasrec_zero) != 8 or len(reference) != 6:
        fail("public E-E V3 aggregate vector length drift")
    normal = summary["NDCG@10"]["vector"]
    alpha_minus_normal = shared.welch(alpha_zero, normal)
    normal_minus_zero = shared.welch(normal, sasrec_zero)
    normal_minus_reference = shared.welch(normal, reference)
    direction = alpha_minus_normal["direction"]
    verdict = {
        "ABOVE": "EEV4-ALPHAFUSE-ABOVE-NORMAL-SASREC",
        "BELOW": "EEV4-ALPHAFUSE-BELOW-NORMAL-SASREC",
        "OVERLAP": "EEV4-ALPHAFUSE-NORMAL-SASREC-OVERLAP",
    }[direction]

    resources: dict[str, object] = {}
    training = {seed: common.load_json(common.training_path(arm, seed))
                for seed in common.SEEDS}
    fields = {
        "total_params": [training[s]["total_params"] for s in common.SEEDS],
        "trainable_params": [training[s]["trainable_params"] for s in common.SEEDS],
        "training_wall_seconds": [training[s]["training_wall_seconds"] for s in common.SEEDS],
        "selected_epoch": [endpoints[s]["selected_epoch"] for s in common.SEEDS],
        "eval_seconds": [endpoints[s]["metrics"]["eval_seconds"] for s in common.SEEDS],
        "users_per_second": [endpoints[s]["metrics"]["users_per_second"] for s in common.SEEDS],
        "cuda_peak_allocated_bytes": [
            endpoints[s]["metrics"]["cuda_peak_allocated_bytes"] for s in common.SEEDS],
        "profiler_accounted_flops_per_user": [
            endpoints[s]["metrics"]["profiler_accounted_flops_per_user"]
            for s in common.SEEDS],
    }
    for key, values in fields.items():
        resources[key] = {
            "vector": values,
            "median": float(np.median(np.asarray(values, dtype=np.float64))),
        }

    output = {
        "protocol": common.PROTOCOL,
        "classification": (
            "PROSPECTIVELY_FROZEN_OUTCOME_KNOWN_SAME_INVESTIGATOR_"
            "COMPARATOR_FAIRNESS_SENSITIVITY"
        ),
        "countable_as_normal_init_sensitivity": True,
        "independent_confirmation": False,
        "general_sota_claim_allowed": False,
        "verdict": verdict,
        "repository_commit": ready["repository_commit"],
        "upstream_commit": common.UPSTREAM_COMMIT,
        "arm": arm,
        "initialization": "upstream CLI default Normal(0,1)",
        "seeds": list(common.SEEDS),
        "ready_sha256": ready_sha,
        "endpoint_ledger": ledger,
        "arm_seed_summary": summary,
        "contrasts": {
            "v3_alphafuse_zero_minus_v4_sasrec_normal": alpha_minus_normal,
            "v4_sasrec_normal_minus_v3_sasrec_zero": normal_minus_zero,
            "v4_sasrec_normal_minus_existing_paper_reference": normal_minus_reference,
        },
        "prior_public_adjudication": {
            "file": common.EEV3_ADJUDICATION.name,
            "sha256": common.EEV3_ADJUDICATION_SHA256,
            "alphafuse_zero_ndcg10": shared.mean_sd_ci(alpha_zero),
            "sasrec_zero_ndcg10": shared.mean_sd_ci(sasrec_zero),
            "existing_reference_ndcg10": shared.mean_sd_ci(reference),
        },
        "resources": resources,
        "resource_scope": (
            "two-process concurrent training waves make wall time unsuitable for hardware-"
            "efficiency claims; profiler FLOPs are operator-accounted lower bounds"
        ),
        "claim_boundary": (
            "Prospectively frozen but outcome-known same-investigator cross-campaign "
            "sensitivity using the upstream-default-normal-init AlphaFuse-repository "
            "SASRec class. Phase/date and initialization are confounded; architecture, "
            "capacity, and parameter allocation remain unequal. This does not isolate "
            "initialization, establish SOTA, or provide independent confirmation."
        ),
        "completed_utc": common.utc_now(),
    }
    common.exclusive_json(common.ADJUDICATION, output)
    print(json.dumps({
        "verdict": verdict,
        "v3_alphafuse_zero_minus_v4_sasrec_normal": alpha_minus_normal,
        "v4_sasrec_normal_minus_v3_sasrec_zero": normal_minus_zero,
        "v4_sasrec_normal_minus_existing_paper_reference": normal_minus_reference,
        "adjudication_sha256": common.sha256(common.ADJUDICATION),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"E-E V4 ADJUDICATION FAILURE: {exc}", file=sys.stderr, flush=True)
        raise
