# -*- coding: utf-8 -*-
"""SCOPE TEST: is the cold-row suppression mechanism specific to full-catalog
softmax, or does it survive sampled/in-batch negative training?

Under full-catalog softmax every cold item is a negative at EVERY step, so its
row is actively pushed down (measured: norm 0.32 vs 0.55 warm, aligned on a
shared suppression axis). Under sampled negatives a cold item is only rarely
drawn, so its row should stay near initialization instead -- uninformative
rather than corrupted. Same symptom (unrankable), different disease, different
cure. This determines how broadly the paper's mechanism claim can be stated.

Trains one MI k0-capped text-arm run with --sampled-negs (no chunked full
softmax), then compares cold-row geometry against the full-softmax counterpart.
GPU-guarded; foreground; skip-if-exists.
"""
import json
import os
import subprocess
import sys

import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
MAIN_RUN = r"C:\Users\rayxc\Documents\R\_bestrec_run"
OUT = os.path.join(HERE, "poc_out")
TRAINER = os.path.join(HERE, "run_sasrec_sbert_kdial.py")
REF = os.path.join(MAIN_RUN, "results_MI_COLDFUSE_base_seed20260736.json")
SEED = 20260736
EXCLUDE = {"seed", "out", "category", "save_ckpt", "eval_every",
           "fir_v3", "fir_v3_kernel", "fir_v3_wd", "zfusion_sweep",
           "chunked_full_softmax", "item_chunk"}          # <- the swap
GPU_BUSY_MIB = 6000


def gpu_busy():
    try:
        o = subprocess.run(["nvidia-smi", "--query-gpu=memory.used",
                            "--format=csv,noheader,nounits"],
                           capture_output=True, text=True, timeout=30)
        return int(o.stdout.strip().splitlines()[0]) >= GPU_BUSY_MIB
    except Exception:
        return False


def train_if_needed():
    out = os.path.join(OUT, f"results_NEGCTRL_text_k0_MI_seed{SEED}.json")
    if os.path.exists(out):
        print("SKIP training (exists)", flush=True)
        return out
    if gpu_busy():
        print("GPU BUSY — not launching.", flush=True)
        sys.exit(0)
    cfg = json.load(open(REF, encoding="utf-8"))["config"]
    argv = [cfg["category"]]
    for k in sorted(cfg):
        if k in EXCLUDE or cfg[k] is None or cfg[k] is False:
            continue
        flag = "--" + k.replace("_", "-")
        if cfg[k] is True:
            argv.append(flag)
        else:
            argv += [flag, str(cfg[k])]
    cmd = ([sys.executable, "-u", TRAINER] + argv
           + ["--sampled-negs", "1024",
              "--item-cap-k", "0", "--item-cap-frac", "0.25",
              "--item-cap-seed", "7", "--eval-every", "5", "--save-ckpt",
              "--seed", str(SEED), "--out", out])
    log = out.replace(".json", ".log")
    print("LAUNCH sampled-negatives control", flush=True)
    with open(log, "w", encoding="utf-8") as lf:
        rc = subprocess.run(cmd, stdout=lf, stderr=subprocess.STDOUT).returncode
    print(f"DONE rc={rc}", flush=True)
    if rc != 0:
        sys.exit(rc)
    return out


def geometry(ckpt, deg, label):
    sd = torch.load(ckpt, map_location="cpu", weights_only=False)["state_dict"]
    V = sd["item_emb.weight"].numpy().astype(np.float64)[:len(deg)]
    cold, warm = deg == 0, deg >= 21
    nrm = np.linalg.norm(V, axis=1)
    sup = V[cold].mean(axis=0)
    sup = sup / max(np.linalg.norm(sup), 1e-12)
    # coherence: how aligned are cold rows with their own mean direction?
    coh_cold = float(np.mean((V[cold] / np.maximum(np.linalg.norm(V[cold], axis=1, keepdims=True), 1e-12)) @ sup))
    coh_warm = float(np.mean((V[warm] / np.maximum(np.linalg.norm(V[warm], axis=1, keepdims=True), 1e-12)) @ sup))
    r = {"label": label, "cold_norm": float(nrm[cold].mean()),
         "warm_norm": float(nrm[warm].mean()),
         "norm_ratio": float(nrm[cold].mean() / nrm[warm].mean()),
         "cold_coherence": coh_cold, "warm_coherence": coh_warm,
         "cold_norm_sd": float(nrm[cold].std())}
    print(f"  {label:>26}: cold||v||={r['cold_norm']:.4f} "
          f"warm||v||={r['warm_norm']:.4f} ratio={r['norm_ratio']:.3f}  "
          f"cold-coherence={coh_cold:+.3f} (warm {coh_warm:+.3f})", flush=True)
    return r


def main():
    out = train_if_needed()
    sys.path.insert(0, MAIN_RUN)
    import run_sasrec_sbert as rsp
    cat = "Musical_Instruments"
    tr = rsp.load_split_csv(rsp.SPLIT_DIR / f"{cat}.train.csv")
    va = rsp.load_split_csv(rsp.SPLIT_DIR / f"{cat}.valid.csv")
    te = rsp.load_split_csv(rsp.SPLIT_DIR / f"{cat}.test.csv")
    train_inters, _, _, _, item_list = rsp.reindex(tr, va, te)
    deg = np.zeros(len(item_list), dtype=np.int64)
    for _, i, _, _ in train_inters:
        deg[i] += 1
    cs = json.load(open(out + ".capset.json", encoding="utf-8"))
    deg[np.array(cs["capped_items"], dtype=np.int64)] = 0

    print("\n=== cold-row geometry: full-softmax vs sampled-negatives ===")
    rows = []
    full = os.path.join(OUT, f"results_K5_text_k0_MI_seed{SEED}.best.pt")
    if os.path.exists(full):
        rows.append(geometry(full, deg, "full-catalog softmax"))
    rows.append(geometry(out.replace(".json", ".best.pt"), deg,
                         "sampled negatives (1024)"))

    for tag, f in (("full-catalog softmax",
                    os.path.join(OUT, f"results_K5_text_k0_MI_seed{SEED}.json")),
                   ("sampled negatives (1024)", out)):
        if os.path.exists(f):
            j = json.load(open(f, encoding="utf-8"))
            bt = j.get("best_test", {})
            print(f"  {tag:>26}: overall test NDCG@10="
                  f"{bt.get('NDCG@10', float('nan')):.5f}")
    json.dump(rows, open(os.path.join(OUT, "negatives_control.json"), "w",
                         encoding="utf-8"), indent=1)
    print(f"\nwrote {os.path.join(OUT, 'negatives_control.json')}")


if __name__ == "__main__":
    main()
