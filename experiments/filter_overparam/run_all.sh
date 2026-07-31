#!/bin/bash
# FMLP-Rec filter-parameterisation ladder.
#
#   BSAREC_DIR=/path/to/BSARec PYBIN=/path/to/python ./run_all.sh <n_parallel> <dataset:n_seeds>...
#
# Example (6 concurrent, 5 seeds each):
#   ./run_all.sh 6 LastFM:5 Beauty:5 Toys_and_Games:5 ML-1M:5
#
# Re-running is safe: any run whose log already contains a Test Score is skipped.
set -u

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BSAREC_DIR="${BSAREC_DIR:-$HERE/BSARec}"
PYBIN="${PYBIN:-python}"
SRC="$BSAREC_DIR/src"

if [[ ! -f "$SRC/main.py" ]]; then
  echo "error: $SRC/main.py not found. Set BSAREC_DIR, or run setup.sh first." >&2
  exit 1
fi

NPAR=$1; shift
cd "$SRC" || exit 1
mkdir -p output

JOBS="$(mktemp)"
for spec in "$@"; do
  DATA="${spec%%:*}"; NSEED="${spec##*:}"
  for ((i=0;i<NSEED;i++)); do
    seed=$((42+i))
    for mode in full rank1 shared none; do
      name="LADDER_${DATA}_${mode}_s${seed}"
      if grep -q "Test Score" "output/${name}.log" 2>/dev/null; then continue; fi
      echo "$DATA $mode $seed $name" >> "$JOBS"
    done
  done
done
echo "queued $(wc -l < "$JOBS") runs, ${NPAR} at a time"

# 2 threads per worker; keep n_parallel*2 at or below your physical core count.
# Oversubscribing here is not merely slow, it thrashes: an early attempt at
# 32 concurrent workers on 14 cores stretched a 7 s epoch to over 15 minutes.
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 VECLIB_MAXIMUM_THREADS=2
cat "$JOBS" | xargs -P "$NPAR" -L 1 bash -c '
  set -- $0 $@
  echo "[start] $4"
  '"$PYBIN"' main.py --model_type FMLPRec --data_name "$1" --no_cuda \
      --num_workers 0 --seed "$3" --filter_mode "$2" --train_name "$4" \
      > "output/$4.stdout" 2>&1
  echo "[done ] $4"
'
rm -f "$JOBS"
echo "ALL COMPLETE"
