"""Generate frozen ablation configs for strict LC2C-LTR repair checks.

The script writes derived configs only inside the SOTA lab. It does not edit the
base research/confirmatory run and it does not bless any ablation for
publication. Each generated config must still be run and finalized normally.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LAB_DIR = Path(__file__).resolve().parent
DEFAULT_BASE = LAB_DIR / "runs" / "research_strict_v2_all_official_dn_rankblend05_101_103" / "frozen_candidate_config.json"
DEFAULT_OUT = LAB_DIR / "ablation_configs"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def without_methods(methods: list[str], banned: set[str]) -> list[str]:
    return [m for m in methods if m not in banned]


def make_payload(base: dict[str, Any], ablation_id: str, purpose: str, ltr_patch: dict[str, Any]) -> dict[str, Any]:
    payload = deepcopy(base)
    ltr = payload["ltr_config"]
    ltr.update(ltr_patch)
    payload["schema_version"] = 1
    payload["candidate"] = "lc2c_retrieval_ltr"
    payload["ablation"] = {
        "ablation_id": ablation_id,
        "generated_utc": utc_now(),
        "purpose": purpose,
        "publication_role": "diagnostic_ablation_only",
    }
    return payload


def build_ablation_payloads(base: dict[str, Any]) -> dict[str, dict[str, Any]]:
    base_ltr = deepcopy(base["ltr_config"])
    no_dn_features = without_methods(list(base_ltr["feature_methods"]), {"official_dropoutnet", "faithful_dropoutnet"})
    no_dn_anchors = without_methods(
        [base_ltr["rerank_anchor_method"], *list(base_ltr.get("rerank_anchor_methods", []))],
        {"official_dropoutnet", "faithful_dropoutnet"},
    )
    if not no_dn_anchors:
        no_dn_anchors = ["content_direct"]

    return {
        "mask_seen_topm_true": make_payload(
            base,
            "mask_seen_topm_true",
            "Checks whether excluding train-history items during top-M rerank pool selection changes the reported win.",
            {"mask_seen_in_topm": True},
        ),
        "no_dropoutnet_feature_or_anchor": make_payload(
            base,
            "no_dropoutnet_feature_or_anchor",
            "Measures whether LC2C-LTR still adds signal without any DropoutNet-derived feature or rerank anchor.",
            {
                "feature_methods": no_dn_features,
                "rerank_anchor_method": no_dn_anchors[0],
                "rerank_anchor_methods": no_dn_anchors[1:],
                "validation_baseline_method": "content_direct",
                "fallback_method": "content_direct",
            },
        ),
        "dropoutnet_feature_content_anchor": make_payload(
            base,
            "dropoutnet_feature_content_anchor",
            "Keeps DropoutNet as an LTR feature but removes it as the retrieval-stage anchor.",
            {
                "rerank_anchor_method": "content_direct",
                "rerank_anchor_methods": [],
                "fallback_method": "official_dropoutnet",
                "validation_baseline_method": "official_dropoutnet",
            },
        ),
        "dropoutnet_anchor_only_control": make_payload(
            base,
            "dropoutnet_anchor_only_control",
            "Controls for the DropoutNet anchor by setting rank-blend prediction weight to zero.",
            {
                "feature_methods": ["official_dropoutnet"],
                "rerank_anchor_method": "official_dropoutnet",
                "rerank_anchor_methods": [],
                "rerank_output_mode": "rank_blend",
                "rerank_prediction_weight": 0.0,
                "validation_baseline_method": "official_dropoutnet",
                "fallback_method": "official_dropoutnet",
            },
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-config", default=str(DEFAULT_BASE))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    base_path = Path(args.base_config).resolve()
    out_dir = Path(args.out_dir).resolve()
    base = read_json(base_path)
    if base.get("protocol", {}).get("protocol_id") != "cold_sota_strict_v2":
        raise SystemExit(f"Base config is not strict-v2: {base_path}")
    if base.get("candidate") != "lc2c_retrieval_ltr":
        raise SystemExit(f"Base config is not lc2c_retrieval_ltr: {base_path}")

    generated = {}
    for name, payload in build_ablation_payloads(base).items():
        path = out_dir / f"{name}.json"
        write_json(path, payload)
        generated[name] = {
            "path": str(path),
            "sha256": sha256_file(path),
            "ltr_config": payload["ltr_config"],
            "purpose": payload["ablation"]["purpose"],
        }

    manifest = {
        "schema_version": 1,
        "generated_utc": utc_now(),
        "base_config": str(base_path),
        "base_config_sha256": sha256_file(base_path),
        "generated_configs": generated,
        "reviewer_rule": "Ablations are diagnostics. They cannot authorize publication unless rerun under the same strict full-catalog protocol and summarized by finalize.py.",
    }
    write_json(out_dir / "ablation_config_manifest.json", manifest)
    print(f"Wrote {len(generated)} ablation configs to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
