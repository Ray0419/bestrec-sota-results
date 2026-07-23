# -*- coding: utf-8 -*-
"""Execute one shard on a pod, with the OPS ledger and hashed result packing.

  python cloud/run_shard.py cloud/shards/eb_shard0.json

Per job: skip-if-exists steps; append-only JSONL events with environment
capture (hostname, GPU, torch/CUDA, commit, dirty-diff sha). At the end,
packs every produced artifact (+ .finaleval/.npz sidecars; checkpoints are
hashed but NOT packed) into cloud/returns/<shard>_<host>.tar.gz with a
SHA256SUMS file. Pull that one file back and verify."""
import glob
import hashlib
import json
import os
import socket
import subprocess
import sys
import tarfile
import time
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable


def env_info():
    info = {"hostname": socket.gethostname(), "python": sys.version.split()[0]}
    try:
        import torch
        info["torch"] = torch.__version__
        info["cuda"] = torch.version.cuda
        info["gpu"] = (torch.cuda.get_device_name(0)
                       if torch.cuda.is_available() else None)
    except Exception as e:
        info["torch_error"] = str(e)
    try:
        info["commit"] = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
            text=True).stdout.strip()
        diff = subprocess.run(["git", "diff"], cwd=ROOT, capture_output=True,
                              text=True).stdout
        info["dirty_diff_sha256"] = hashlib.sha256(
            diff.encode("utf-8", "replace")).hexdigest()
    except Exception:
        pass
    return info


def main():
    shard_path = sys.argv[1]
    shard = json.load(open(shard_path, encoding="utf-8"))
    sid = shard["shard"]
    host = socket.gethostname()
    led_dir = os.path.join(ROOT, "_bestrec_run", "attempts")
    os.makedirs(led_dir, exist_ok=True)
    ledger = os.path.join(led_dir, f"cloud_shard{sid}_{host}.jsonl")

    def emit(e):
        with open(ledger, "a", encoding="utf-8") as f:
            f.write(json.dumps(
                {"ts": datetime.now(timezone.utc).isoformat(), **e}) + "\n")

    emit({"event": "shard_launch", "shard": sid, "env": env_info(),
          "jobs": [j["id"] for j in shard["jobs"]]})
    produced, failed = [], 0
    for j in shard["jobs"]:
        for st in j["steps"]:
            tgt = os.path.join(ROOT, st["exists"])
            if os.path.exists(tgt):
                emit({"event": "skip", "job": j["id"], "phase": st["phase"]})
                continue
            cmd = [PY if c == "python" else c for c in st["cmd"]]
            emit({"event": "launch", "job": j["id"], "phase": st["phase"],
                  "cmd": " ".join(st["cmd"])})
            t0 = time.time()
            r = subprocess.run(cmd, cwd=ROOT)
            ok = r.returncode == 0
            emit({"event": "done" if ok else "fail", "job": j["id"],
                  "phase": st["phase"], "rc": r.returncode,
                  "dur_s": round(time.time() - t0, 1)})
            if not ok:
                failed += 1
                break
        art = os.path.join(ROOT, j["artifact"])
        if os.path.exists(art):
            produced.append(j["artifact"])
            fe = j["artifact"][:-5] + ".finaleval.json"
            if os.path.exists(os.path.join(ROOT, fe)):
                produced.append(fe)
                npz = fe[:-5] + ".perusers.npz"
                if os.path.exists(os.path.join(ROOT, npz)):
                    produced.append(npz)
            ck = j["artifact"][:-5] + ".best.pt"
            if os.path.exists(os.path.join(ROOT, ck)):
                emit({"event": "ckpt_hash", "job": j["id"],
                      "sha256": hashlib.sha256(
                          open(os.path.join(ROOT, ck), "rb").read())
                      .hexdigest()})

    ret_dir = os.path.join(ROOT, "cloud", "returns")
    os.makedirs(ret_dir, exist_ok=True)
    produced.append(os.path.relpath(ledger, ROOT).replace("\\", "/"))
    sums = []
    for rel in produced:
        p = os.path.join(ROOT, rel)
        sums.append(f"{hashlib.sha256(open(p, 'rb').read()).hexdigest()}  "
                    f"{rel}")
    sums_rel = f"cloud/returns/SHA256SUMS_shard{sid}_{host}.txt"
    with open(os.path.join(ROOT, sums_rel), "w", encoding="utf-8") as f:
        f.write("\n".join(sums) + "\n")
    tar_path = os.path.join(ret_dir, f"eb_shard{sid}_{host}.tar.gz")
    with tarfile.open(tar_path, "w:gz") as t:
        for rel in produced + [sums_rel]:
            t.add(os.path.join(ROOT, rel), arcname=rel)
    emit({"event": "shard_end", "failed": failed,
          "packed": len(produced), "tar": os.path.basename(tar_path)})
    print(f"SHARD {sid} DONE: {len(produced)} artifacts, {failed} failures "
          f"-> {tar_path}", flush=True)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
