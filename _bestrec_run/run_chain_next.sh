#!/bin/bash
# Auto-chain after the B/C POC batch: pick best (epochs, K) config from the
# four combo POC results, run 4 more seeds of it (A: 5-seed confirmation),
# then one Beauty_and_PC transfer run (D).
cd /c/Users/rayxc/Documents/R

# 1. Wait for the B+C batch sentinel (last file it writes)
until [ -f _bestrec_run/results_poc_CK1024_VG.json ]; do sleep 60; done
sleep 10

# 2. Pick best config among the four combo variants
CFG=$(_bestrec_run/.venv/Scripts/python -c "
import json
cands = [
    ('50 512',  '_bestrec_run/results_poc_P4_all_VG.json'),
    ('100 512', '_bestrec_run/results_poc_B100ep_VG.json'),
    ('50 256',  '_bestrec_run/results_poc_CK256_VG.json'),
    ('50 1024', '_bestrec_run/results_poc_CK1024_VG.json'),
]
best, bv = None, -1
for tag, p in cands:
    try:
        d = json.load(open(p))
        v = d['best_test']['NDCG@10']
        if v > bv: bv, best = v, tag
    except Exception:
        pass
print(best)
")
EPOCHS=$(echo $CFG | cut -d' ' -f1)
K=$(echo $CFG | cut -d' ' -f2)
echo "CHAIN: best config epochs=$EPOCHS K=$K"

# 3. A: 4 more seeds of the best config (seed 20260608 already done)
for s in 20260609 20260610 20260611 20260612; do
  _bestrec_run/.venv/Scripts/python -u _bestrec_run/run_sasrec_sbert.py Video_Games \
    --epochs $EPOCHS --batch-size 256 --d-model 64 --n-layers 2 --n-heads 2 --dropout 0.3 \
    --chunked-full-softmax --item-chunk 32768 --seed $s --lr-schedule warmup_cosine \
    --time-bias --text-sim-bias --text-prototypes $K --eval-every 10 \
    --out _bestrec_run/results_combo_VG_seed${s}.json \
    > _bestrec_run/run_combo_VG_seed${s}.log 2>&1
  echo "CHAIN: seed $s done"
done

# 4. D: Beauty transfer, single seed (tuned recipe + combo flags, MiniLM titles)
_bestrec_run/.venv/Scripts/python -u _bestrec_run/run_sasrec_sbert.py Beauty_and_Personal_Care \
  --epochs 15 --batch-size 256 --d-model 64 --n-layers 2 --n-heads 2 --dropout 0.3 \
  --chunked-full-softmax --item-chunk 32768 --seed 42 --lr-schedule warmup_cosine \
  --time-bias --text-sim-bias --text-prototypes $K --eval-every 5 --eval-subsample 10000 \
  --out _bestrec_run/results_combo_Beauty_seed42.json \
  > _bestrec_run/run_combo_Beauty_seed42.log 2>&1
echo "CHAIN: Beauty transfer done"
echo "CHAIN ALL DONE"
