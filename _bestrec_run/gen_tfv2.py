# -*- coding: utf-8 -*-
"""TFV2 campaign command generator (maintainer directive 2026-07-20: fold-in of the
audit P0 reruns). Reads the ORIGINAL runs' embedded config dicts and mechanically
re-emits full CLI commands with fresh, never-inspected seeds — no hand transcription.

Design (frozen in PREREG_TAIL_FIR_V2.md):
  independent-arm campaigns (option (b) of audit 2026-07-19 19:56: arms are
  pre-specified as independent; no pairing claim), 8 seeds per arm, per-user
  sidecars are produced automatically by the driver (<out>.users.jsonl.gz).

Self-verification: the smoke run's emitted config must equal the template config on
every key except {seed, epochs, out, eval_every}; otherwise the flag mapping is wrong
and the campaign must not launch.
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PY = os.path.join(HERE, ".venv", "Scripts", "python.exe")
DRIVER = os.path.join(HERE, "run_sasrec_sbert.py")

PLAN = [
    ("MI",  "text",     "results_MI_TAIL_V2_text_seed20260608.json",              [20260801 + i for i in range(8)]),
    ("MI",  "idonly",   "results_MI_TAIL_idonly_seed20260608.json",               [20260811 + i for i in range(8)]),
    ("IS",  "filter",   "results_FIRB_Industrial_and_Scientific_filter_seed20260713.json",   [20260821 + i for i in range(8)]),
    ("IS",  "nofilter", "results_FIRB_Industrial_and_Scientific_nofilter_seed20260713.json", [20260831 + i for i in range(8)]),
    ("CDs", "filter",   "results_FIRB_CDs_and_Vinyl_filter_seed20260713.json",    [20260861 + i for i in range(8)]),
    ("CDs", "nofilter", "results_FIRB_CDs_and_Vinyl_nofilter_seed20260713.json",  [20260871 + i for i in range(8)]),
    ("VG",  "text",     "results_TAIL_V2_text_VG.json",                           [20260841 + i for i in range(8)]),
    ("VG",  "idonly",   "results_TAIL_idonly_VG.json",                            [20260851 + i for i in range(8)]),
]

SKIP_KEYS = {"seed", "out", "category"}  # category is the positional argument

def flags_from_config(cfg):
    parts = []
    for k, v in cfg.items():
        if k in SKIP_KEYS or v is None or v == "" or v == [] or v == {}:
            continue  # empty values are argparse defaults; emitting them breaks flags (E1)
        flag = "--" + k.replace("_", "-")
        if isinstance(v, bool):
            if v:
                parts.append(flag)
        else:
            parts.append(f"{flag} {v}")
    return parts

def main():
    lines = []
    for short, arm, tmpl, seeds in PLAN:
        cfg = json.load(open(os.path.join(HERE, tmpl), encoding="utf-8"))["config"]
        base = flags_from_config(cfg)
        for s in seeds:
            out = f"_bestrec_run/results_TFV2_{short}_{arm}_seed{s}.json"
            cmd = (f'"{PY}" "{DRIVER}" {cfg["category"]} ' + " ".join(base)
                   + f" --seed {s} --out {out}")
            lines.append(cmd)
    txt = "\n".join(lines) + "\n"
    dst = os.path.join(HERE, "tfv2_commands.txt")
    with open(dst, "w", encoding="utf-8", newline="\n") as f:
        f.write(txt)
    h = hashlib.sha256(txt.encode()).hexdigest()
    print(f"wrote {dst}: {len(lines)} commands; sha256 {h}")
    # smoke command (config-parity validation only; 1 epoch; gitignored smoke_ name)
    cfg = json.load(open(os.path.join(HERE, PLAN[0][2]), encoding="utf-8"))["config"]
    smoke_cfg = dict(cfg)
    smoke_cfg["epochs"] = 1
    smoke = (f'"{PY}" "{DRIVER}" {smoke_cfg["category"]} ' + " ".join(flags_from_config(smoke_cfg))
             + " --seed 999001 --out _bestrec_run/smoke_TFV2_paritycheck.json")
    with open(os.path.join(HERE, "tfv2_smoke_cmd.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(smoke + "\n")
    print("smoke command written (epochs=1, seed 999001)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
