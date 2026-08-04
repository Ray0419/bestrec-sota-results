#!/usr/bin/env bash
set -euo pipefail

WORK_DIR="${HSTU_BLAIR_WORK_DIR:-$HOME/.bestrec_hstu_blair}"
SRC="${HSTU_BLAIR_SRC:-$WORK_DIR/HSTU-BLaIR}"
ENV_DIR="${HSTU_BLAIR_SM120_ENV_DIR:-$WORK_DIR/venv_py39_sm120}"

if [[ ! -x "$ENV_DIR/bin/python" ]]; then
  echo "SM120 environment missing: $ENV_DIR" >&2
  exit 2
fi

cd "$SRC"
SOURCE_STATUS="$(git status --short -- . ':(exclude)tmp' ':(exclude)exps' ':(exclude)ckpts')"
if [[ -n "$SOURCE_STATUS" ]]; then
  echo "Native WSL HSTU-BLaIR source/config files are dirty; refusing preprocessing." >&2
  echo "$SOURCE_STATUS" >&2
  exit 3
fi

mkdir -p tmp
export PYTHONPATH="$SRC:${PYTHONPATH:-}"

"$ENV_DIR/bin/python" - <<'PY'
import torch
from pathlib import Path
from generative_recommenders.research.data.preprocessor import get_common_preprocessors

print("torch", torch.__version__, "cuda", torch.version.cuda, "cuda_available", torch.cuda.is_available())
print("preprocessing amzn23_game with BLaIR embeddings")
processor = get_common_preprocessors(text_embedding_model="blair")["amzn23_game"]
saved_name = Path(processor._saved_name)
if processor._download_path.endswith(".csv.gz") and not str(saved_name).endswith(".gz"):
    repaired_name = Path(str(saved_name) + ".gz")
    if saved_name.exists() and not repaired_name.exists():
        with saved_name.open("rb") as handle:
            magic = handle.read(2)
        if magic == b"\x1f\x8b":
            saved_name.rename(repaired_name)
            print(f"renamed gzip archive {saved_name} -> {repaired_name}")
    processor._saved_name = str(repaired_name)
    print(f"runtime_saved_name_repair {saved_name} -> {processor._saved_name}")
processor.preprocess_rating()
PY

test -f tmp/amzn23_game/sasrec_format.csv
test -f tmp/amzn23_game/item_text_embeddings_blair.pt
du -sh tmp/amzn23_game
echo "HSTU-BLaIR amzn23_game preprocessing complete."
