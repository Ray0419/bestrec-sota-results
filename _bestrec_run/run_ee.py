# -*- coding: utf-8 -*-
"""E-E launch tooling (committed BEFORE any real run; see PREREG_EE.md).

Runs ONE (category, seed) AlphaFuse job under the FROZEN config, captures its
stdout, parses the final TEST RESULTS block, and writes a clean per-seed results
JSON. It never edits the AlphaFuse clone (parses stdout only) and never
overwrites an existing results_*.json (append/refuse). One GPU job per call;
sequence seeds across ticks.

  python _bestrec_run/run_ee.py --category Video_Games --seed 22
  python _bestrec_run/run_ee.py --category Video_Games --seed 22 --epoch 500

Output: _bestrec_run/results_EE_<category>_alphafuse_seed<seed>.json
"""
import argparse
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AF = os.path.join(ROOT, "ee_baselines", "AlphaFuse")
DATA = os.path.join(ROOT, "ee_baselines", "ours_DiT", "data", "ourdata")
EXPORT = os.path.join(ROOT, "ee_baselines", "export")

# FROZEN config (PREREG_EE.md) — the authors' recommended SASRec-backbone setup.
FROZEN = dict(model_type="AlphaFuse", language_model_type="minilm",
              ID_embs_init_type="zeros", hidden_dim="128", null_dim="64",
              lr="0.001", loss_type="infoNCE", neg_ratio="64",
              language_embs_scale="40", temperature="0.07", batch_size="256",
              num_blocks="2", num_heads="1", dropout_rate="0.1")


def _floats(line):
    return [float(x) for x in re.findall(r"[-+]?\d*\.\d+|\d+", line)]


def parse_test_block(text):
    """Parse the LAST 'TEST RESULTS' block: header line (HR@5 ...) then values."""
    lines = text.splitlines()
    idx = max((i for i, l in enumerate(lines) if "TEST RESULTS" in l), default=-1)
    if idx < 0:
        return None
    out = {}
    seg = lines[idx:]
    for i, l in enumerate(seg):
        toks = l.split()
        if toks and all(re.match(r"^(HR|NDCG|MRR)@\d+$", t) for t in toks):
            # values are on the next non-empty line
            for j in range(i + 1, len(seg)):
                if seg[j].strip():
                    vals = _floats(seg[j])
                    for h, v in zip(toks, vals):
                        out[h] = v
                    break
    return out or None


def git_sha(path):
    try:
        return subprocess.check_output(["git", "-C", path, "rev-parse", "HEAD"],
                                       text=True).strip()[:12]
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--category", required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--epoch", type=int, default=500)
    args = ap.parse_args()
    cat = args.category

    ddir = os.path.join(DATA, cat)
    if not os.path.exists(os.path.join(ddir, "data_statis.df")):
        raise SystemExit(f"dataset for {cat} not built; run "
                         f"build_alphafuse_dataset.py --category {cat} first")
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            f"results_EE_{cat}_alphafuse_seed{args.seed}.json")
    if os.path.exists(out_path):
        raise SystemExit(f"REFUSING to overwrite existing {out_path} "
                         f"(rename-preserve rule)")

    cmd = [sys.executable, "-u", "train.py", "--data", f"ourdata/{cat}",
           "--cuda", "0", "--epoch", str(args.epoch),
           "--random_seed", str(args.seed)]
    for k, v in FROZEN.items():
        cmd += [f"--{k}", v]
    os.makedirs(os.path.join(AF, "saved", "ourdata"), exist_ok=True)
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            f"results_EE_{cat}_alphafuse_seed{args.seed}.log")
    print("launching:", " ".join(cmd), "\n cwd:", AF, "\n log:", log_path)
    with open(log_path, "w", encoding="utf-8") as lf:
        proc = subprocess.run(cmd, cwd=AF, stdout=lf, stderr=subprocess.STDOUT,
                              text=True)
    text = open(log_path, encoding="utf-8").read()
    metrics = parse_test_block(text)
    if proc.returncode != 0 or metrics is None:
        raise SystemExit(f"run failed (rc={proc.returncode}) or no TEST RESULTS "
                         f"parsed; see {log_path}")

    # provenance
    man = os.path.join(EXPORT, cat, f"{cat}.manifest.json")
    manifest = json.load(open(man)) if os.path.exists(man) else {}
    rec = {
        "experiment": "E-E", "arm": "AlphaFuse", "category": cat,
        "seed": args.seed, "epoch_cap": args.epoch,
        "config_frozen": FROZEN,
        "metrics_test": metrics,
        "provenance": {
            "alphafuse_git": git_sha(AF),
            "adapter": "build_alphafuse_dataset.py (left-pad L=50, per-prefix, "
                       "minilm_emb re-index via asin2idx)",
            "split_sha16": manifest.get("split_sha16"),
            "n_users": manifest.get("n_users"),
            "n_items": manifest.get("n_items"),
        },
        "deviations": [
            "MiniLM-384 substituted for OpenAI text-embedding-3",
            "our AR2023 5-core LLOO split; never their paper numbers",
            "each method trains as designed (AlphaFuse sampled-neg infoNCE)",
            "per-prefix train expansion is our adapter's disclosed choice",
            "single environment; point estimate, no cross-env variance",
        ],
        "note": "DESCRIPTIVE closest-comparator; no superiority/SOTA claim.",
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=1)
    print("WROTE", out_path)
    print("  test NDCG@10 =", metrics.get("NDCG@10"),
          " HR@10 =", metrics.get("HR@10"), " MRR@10 =", metrics.get("MRR@10"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
