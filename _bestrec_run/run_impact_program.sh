#!/bin/bash
# IMPACT program driver (IMPACT_REVISION_PLAN.md approaches A+B) — 30 runs total.
#
#   Segment 1: PREREG_FIR_BREADTH.md — 20 runs.
#     Categories AS PRE-REGISTERED, NO SUBSTITUTION:
#       Industrial_and_Scientific (50,985 users / 25,848 items / 412,947 inters)
#       CDs_and_Vinyl             (123,876 users / 89,370 items / 1,552,764 inters)
#     CDs_and_Vinyl feasibility (prereg fallback NOT triggered): 89,370 items is
#     far below the ~450k chunked-full-softmax ceiling on the 16 GB GPU (Office
#     ran 77,551 items at item-chunk 32768), and the projected epoch time
#     (~1.5 min incl. two full-catalog evals) is far below the 12 min/epoch
#     (4 h/run) VOID bound, so Toys_and_Games stays unused.
#     Arms per category: F (--causal-filter --filter-kernel 8) and N (no filter),
#     seeds 20260713..20260717 (never-inspected; frozen in the prereg).
#   Segment 2: PREREG_OFFICE_V3.md — 10 runs.
#     Office_Products (223,308 users / 77,551 items), arms k16/k8,
#     seeds 20260728..20260732 (never-inspected; frozen in the prereg).
#
# Conventions (matching run_sota_confirm_v2.sh / run_office_program.sh):
#   set -euo pipefail; PYBIN override; RESUME=1 default.
#   RESUME=1: skip a run iff its output json exists AND parses AND has a
#             best_test key. An existing-but-invalid json is NEVER overwritten:
#             it is renamed to <name>.json.invalid.<ts> (rename-preserve).
#   RESUME=0: regenerate everything, but still never overwrite — any existing
#             output json (valid or not) is rename-preserved first.
# Circuit breakers (checked before EVERY run):
#   exit 42 — repo-root PAUSE_EXPERIMENTS sentinel present (same convention
#             run_sasrec_sbert.py honors internally).
#   exit 43 — tracked tree dirty before an OFFICE-V3 run (PREREG_OFFICE_V3.md
#             comparability condition 3 requires clean-tracked-tree provenance
#             in every run manifest; running would VOID the campaign). For
#             FIR-BREADTH runs a dirty tree only WARNS (that prereg proves code
#             identity via embedded code hashes and does not void on tree state).
#   exit 44 — a foreign python GPU job is still present after a 30 min bounded
#             wait (one-GPU-job-at-a-time rule).
#   exit 45 — missing split/cache preconditions.
# After each segment the matching adjudicator runs in NON-FATAL --report mode.
# On full completion: prints 'IMPACT PROGRAM COMPLETE' and writes
# _bestrec_run/impact_program.DONE with the finish timestamp.
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYBIN:-}"
if [ -z "$PY" ]; then
  if command -v uv >/dev/null 2>&1; then PY="uv --project _bestrec_run run python";
  else PY=_bestrec_run/.venv/Scripts/python; fi
fi
RESUME="${RESUME:-1}"

ts() { date '+%Y-%m-%d %H:%M:%S'; }

is_valid_result() {  # $1 = json path -> rc 0 iff parses and has best_test
  $PY -c "
import json, sys
try:
    d = json.load(open(sys.argv[1], encoding='utf-8'))
    sys.exit(0 if d.get('best_test') is not None else 1)
except Exception:
    sys.exit(1)
" "$1"
}

check_pause() {
  if [ -e PAUSE_EXPERIMENTS ]; then
    echo "[$(ts)] PAUSE_EXPERIMENTS sentinel present — stopping (exit 42)"
    exit 42
  fi
}

check_gpu_free() {  # bounded wait (30 x 60s) for foreign python GPU jobs
  local i
  for i in $(seq 1 30); do
    if ! nvidia-smi --query-compute-apps=process_name --format=csv,noheader 2>/dev/null \
        | grep -qi python; then
      return 0
    fi
    echo "[$(ts)] foreign python GPU job detected — waiting 60s ($i/30)"
    sleep 60
  done
  echo "[$(ts)] GPU still occupied by a python job after 30 min — stopping (exit 44)"
  exit 44
}

check_tree() {  # $1 = 'hard' (exit 43) or 'warn'
  # PREREG_OFFICE_V3.md ERRATUM E1 (pre-campaign): the two external audit-log
  # files are exempt from condition 3 -- they are appended by the hourly audit
  # process outside this campaign's control.
  local dirty nonexempt
  dirty="$(git status --porcelain -uno 2>/dev/null || true)"
  nonexempt="$(printf '%s\n' "$dirty" | grep -v -E ' (PAPER_REVIEW_AUDIT\.md|RESPONSE_TO_PAPER_REVIEW_AUDIT\.md)$' | grep -v '^$' || true)"
  if [ -n "$nonexempt" ]; then
    echo "[$(ts)] TRACKED TREE DIRTY (non-exempt files):"; echo "$nonexempt"
    if [ "$1" = "hard" ]; then
      echo "[$(ts)] OFFICE-V3 condition 3 requires clean tracked-tree provenance;"
      echo "        commit/revert the files above, then relaunch (exit 43)"
      exit 43
    fi
    echo "[$(ts)] WARNING: proceeding (FIR-BREADTH provenance uses embedded code hashes)"
  elif [ -n "$dirty" ]; then
    echo "[$(ts)] tree dirty ONLY in E1-exempt audit-log files (OK):"; echo "$dirty"
  fi
}

capture_treestate() {  # $1 = out.json path, $2 = tag(pre|post); E1 evidence sidecar
  git status --porcelain -uno >> "$1.treestate.txt" 2>/dev/null || true
  echo "---- $2 $(ts)" >> "$1.treestate.txt"
}

run_one() {  # $1 label  $2 out.json  $3 log  $4 tree-mode(hard|warn)  $5... = args after 'run_sasrec_sbert.py'
  local label="$1" O="$2" LOG="$3" tree_mode="$4"; shift 4
  check_pause
  check_tree "$tree_mode"
  if [ -f "$O" ]; then
    if [ "$RESUME" = "1" ] && is_valid_result "$O"; then
      echo "[$(ts)] SKIP  $label (valid result exists: $O)"
      return 0
    fi
    local Q="$O.invalid.$(date +%Y%m%d_%H%M%S)"
    echo "[$(ts)] rename-preserving existing $O -> $Q (never overwrite)"
    mv "$O" "$Q"
  fi
  check_gpu_free
  echo "[$(ts)] BEGIN $label -> $O"
  capture_treestate "$O" pre
  local t0=$SECONDS
  $PY -u _bestrec_run/run_sasrec_sbert.py "$@" --out "$O" > "$LOG" 2>&1
  capture_treestate "$O" post
  echo "[$(ts)] END   $label (rc=0, $((SECONDS - t0))s)"
}

# ---- preconditions -----------------------------------------------------
for c in Industrial_and_Scientific CDs_and_Vinyl Office_Products; do
  for f in "data_5core/5core/last_out/$c.train.csv" "data_5core/5core/last_out/$c.valid.csv" \
           "data_5core/5core/last_out/$c.test.csv" "cache_5core/sbert_titles_$c.npy"; do
    if [ ! -f "$f" ]; then echo "[$(ts)] MISSING PRECONDITION: $f (exit 45)"; exit 45; fi
  done
done
echo "[$(ts)] preconditions OK (splits + caches for all 3 categories)"

# ---- Segment 1: FIR-BREADTH (PREREG_FIR_BREADTH.md, frozen commands) ----
# Both arms identical to the V2 stack except the filter flags.
FIRB_SEEDS="20260713 20260714 20260715 20260716 20260717"
V2_STACK="--epochs 20 --batch-size 256 --d-model 64 --n-layers 4 --n-heads 2 --dropout 0.5 \
 --chunked-full-softmax --item-chunk 32768 --lr-schedule warmup_cosine --encoder hstu \
 --time-bias --text-sim-bias --text-prototypes 512 --pos-rab --label-smoothing 0.2"
for CAT in Industrial_and_Scientific CDs_and_Vinyl; do
  for S in $FIRB_SEEDS; do
    run_one "FIRB $CAT filter k8 seed $S" \
      "_bestrec_run/results_FIRB_${CAT}_filter_seed${S}.json" \
      "_bestrec_run/run_FIRB_${CAT}_filter_seed${S}.log" warn \
      "$CAT" $V2_STACK --causal-filter --filter-kernel 8 --eval-every 1 --seed "$S"
  done
  for S in $FIRB_SEEDS; do
    run_one "FIRB $CAT nofilter seed $S" \
      "_bestrec_run/results_FIRB_${CAT}_nofilter_seed${S}.json" \
      "_bestrec_run/run_FIRB_${CAT}_nofilter_seed${S}.log" warn \
      "$CAT" $V2_STACK --eval-every 1 --seed "$S"
  done
done
echo "[$(ts)] FIR-BREADTH segment done — adjudicating (non-fatal --report)"
$PY -u _bestrec_run/adjudicate_fir_breadth.py --report || true

# ---- Segment 2: OFFICE V3 (PREREG_OFFICE_V3.md, frozen commands) --------
OV3_SEEDS="20260728 20260729 20260730 20260731 20260732"
for ARM in 16 8; do
  for S in $OV3_SEEDS; do
    run_one "OFFICEV3 k$ARM seed $S" \
      "_bestrec_run/results_OFFICEV3_k${ARM}_seed${S}.json" \
      "_bestrec_run/run_OFFICEV3_k${ARM}_seed${S}.log" hard \
      Office_Products $V2_STACK --causal-filter --filter-kernel "$ARM" --eval-every 1 --seed "$S"
  done
done
echo "[$(ts)] OFFICE-V3 segment done — adjudicating (non-fatal --report)"
$PY -u _bestrec_run/adjudicate_office_v3.py --report || true

echo "IMPACT PROGRAM COMPLETE"
date '+%Y-%m-%d %H:%M:%S' > _bestrec_run/impact_program.DONE
