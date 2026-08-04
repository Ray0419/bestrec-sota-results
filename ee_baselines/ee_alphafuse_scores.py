# -*- coding: utf-8 -*-
"""E-E V2 arm wrapper — AlphaFuse checkpoint -> per-user full-catalogue scores
-> per-user rank0 via the SHARED evaluator (ee_shared_eval), so AlphaFuse is
scored under OUR masking + tie policy (fixing the pilot's estimand mismatch).

It reconstructs the AlphaFuse model exactly as train.py does (same key_words),
loads a saved checkpoint, and replicates SASRec_backbone.predict directly
(forward -> state; return_item_emb -> item table; state @ items[:-1].T) to get
full-catalogue scores WITHOUT AlphaFuse's own (unmasked) eval. Those scores then
go through ee_shared_eval.target_rank0.

VALIDATION built in: with mask_seen=False the wrapper must reproduce AlphaFuse's
own pilot NDCG@10 (its unmasked estimand); with mask_seen=True it yields the
shared-policy (masked) number that is comparable to our stack. Both are printed.

This is DEV-PROBE tooling for E-E V2 (numbers are NOT countable until PREREG_EE
V2 is frozen with provenance + immutable attempts). It edits NOTHING in the
AlphaFuse clone.

  python ee_baselines/ee_alphafuse_scores.py --category Video_Games --seed 22
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd
import torch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AF = os.path.join(ROOT, "ee_baselines", "AlphaFuse")
DATA = os.path.join(ROOT, "ee_baselines", "ours_DiT", "data", "ourdata")
sys.path.insert(0, AF)              # so `import models.*` resolves
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # ee_shared_eval
from ee_shared_eval import target_rank0  # noqa: E402
sys.path.insert(0, os.path.join(ROOT, "_bestrec_run"))
from metrics_family import family_from_rank0  # noqa: E402


def key_words(data_dir, seed, model_type="AlphaFuse"):
    # AlphaFuse train.py parse_args defaults + our FROZEN E-E overrides. model_type
    # selects the matched-backbone factorial arm: AlphaFuse (fusion) / SASRec (ID).
    return dict(random_seed=seed, lr=0.001, lr_delay_rate=0.99, lr_delay_epoch=100,
                epoch=500, data=f"ourdata", cuda=0, l2_decay=1e-6, batch_size=256,
                num_blocks=2, num_heads=1, dropout_rate=0.1, loss_type="infoNCE",
                neg_ratio=64, temperature=0.07, beta=0.1,
                language_model_type="minilm", language_embs_scale=40,
                hidden_dim=128, ID_embs_init_type="zeros", model_type=model_type,
                SR_aligement_type="con", null_thres=None, null_dim=64,
                item_frequency_flag=False, standardization=True, cover=False,
                ID_space="singular", inject_space="singular",
                language_embs_path=data_dir)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--category", default="Video_Games")
    ap.add_argument("--seed", type=int, default=22)
    ap.add_argument("--model_type", default="AlphaFuse",
                    choices=["AlphaFuse", "SASRec"])
    ap.add_argument("--batch_size", type=int, default=256)
    args = ap.parse_args()
    cat = args.category
    data_dir = os.path.join(DATA, cat)
    ckpt = os.path.join(AF, "saved", "ourdata",
                        f"{cat}{args.model_type}_rs{args.seed}_IDdim128_"
                        f"Textdim64_0.001_infoNCE.pth")
    if not os.path.exists(ckpt):
        raise SystemExit(f"no checkpoint {ckpt}")

    from models.backbone_SASRec import AlphaFuse, SASRec  # noqa: E402
    ModelCls = {"AlphaFuse": AlphaFuse, "SASRec": SASRec}[args.model_type]
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    n_items = int(pd.read_pickle(os.path.join(data_dir, "data_statis.df"))
                  ["item_num"][0])
    model = ModelCls(device, **key_words(data_dir, args.seed,
                                         args.model_type)).to(device)
    model.load_state_dict(torch.load(ckpt, map_location=device))
    model.eval()

    test = pd.read_pickle(os.path.join(data_dir, "test_data.df"))
    test.reset_index(inplace=True, drop=True)
    seqs = list(test["seq"])
    nxts = [int(x) for x in test["next"]]
    ranks_mask, ranks_nomask = [], []
    B = args.batch_size
    with torch.no_grad():
        items = model.return_item_emb()          # (n_items+1, hidden)
        item_mat = items[:-1]                     # drop pad row -> (n_items, hidden)
        for s in range(0, len(seqs), B):
            seq_b = torch.tensor(seqs[s:s + B], dtype=torch.long, device=device)
            state = model.forward(seq_b)          # (b, hidden)
            if state.dim() == 1:
                state = state.unsqueeze(0)
            scores = (state @ item_mat.t()).float().cpu().numpy()  # (b, n_items)
            for k in range(scores.shape[0]):
                seq_k = seqs[s + k]
                seen = {int(i) for i in seq_k if int(i) != n_items}
                tgt = nxts[s + k]
                ranks_mask.append(target_rank0(scores[k], tgt, seen, True))
                ranks_nomask.append(target_rank0(scores[k], tgt, seen, False))
    fam_mask = family_from_rank0(ranks_mask)
    fam_nomask = family_from_rank0(ranks_nomask)
    out = {"experiment": "E-E V2", "arm": args.model_type,
           "category": cat, "seed": args.seed, "n_users": len(ranks_mask),
           "shared_evaluator": True,
           "family_shared_masked": {k: round(v, 6) for k, v in fam_mask.items()},
           "family_unmasked_VALIDATION": {k: round(v, 6)
                                          for k, v in fam_nomask.items()},
           "note": "DEV PROBE, NOT countable. unmasked must reproduce the "
                   "pilot's AlphaFuse NDCG@10 (validates the wrapper); masked is "
                   "the shared-policy number."}
    outp = os.path.join(ROOT, "_bestrec_run",
                        f"results_EE_{cat}_{args.model_type.lower()}_shared_"
                        f"seed{args.seed}.json")
    json.dump(out, open(outp, "w"), indent=1)
    print(f"seed {args.seed}: unmasked NDCG@10={fam_nomask['NDCG@10']:.5f} "
          f"HR@10={fam_nomask['HR@10']:.5f}  (should match pilot)")
    print(f"seed {args.seed}: SHARED-masked NDCG@10={fam_mask['NDCG@10']:.5f} "
          f"HR@10={fam_mask['HR@10']:.5f}")
    print("wrote", outp)
    return 0


if __name__ == "__main__":
    sys.exit(main())
