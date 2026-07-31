#!/bin/bash
# One-time setup for the filter-parameterisation ladder.
# Clones the official BSARec benchmark suite (which ships FMLP-Rec and all six
# standard datasets), pins it to the commit this experiment was built against,
# and applies the filter_mode patch.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BSAREC_DIR="${BSAREC_DIR:-$HERE/BSARec}"
UPSTREAM_COMMIT="c80bdc0"   # yehjin-shin/BSARec, main, as used for these runs

if [[ -d "$BSAREC_DIR/.git" ]]; then
  echo "BSARec already present at $BSAREC_DIR"
else
  echo "cloning BSARec into $BSAREC_DIR (~1.8 GB, includes all datasets)"
  git clone https://github.com/yehjin-shin/BSARec.git "$BSAREC_DIR"
fi

cd "$BSAREC_DIR"
echo "upstream HEAD: $(git rev-parse --short HEAD)  (expected $UPSTREAM_COMMIT)"
if [[ "$(git rev-parse --short HEAD)" != "$UPSTREAM_COMMIT" ]]; then
  echo "WARNING: upstream has moved. The patch may not apply cleanly." >&2
  echo "         To reproduce exactly: git checkout $UPSTREAM_COMMIT" >&2
fi

if git diff --quiet; then
  git apply "$HERE/patches/filter_mode.patch"
  echo "patch applied"
else
  echo "working tree already modified - skipping patch (verify manually)"
fi

echo
echo "verifying arm parameter counts..."
cd src
"${PYBIN:-python}" - <<'PY'
import argparse, torch
from model.fmlprec import FMLPRecModel
a = argparse.Namespace(max_seq_length=50, hidden_size=64, num_hidden_layers=2,
                       hidden_dropout_prob=0.5, hidden_act='gelu',
                       initializer_range=0.02, item_size=12103,
                       attention_probs_dropout_prob=0.5,
                       num_attention_heads=2, batch_size=256)
EXPECT = {'full': 6656, 'rank1': 360, 'shared': 104, 'none': 0}
ok = True
for m in ['full', 'rank1', 'shared', 'none']:
    a.filter_mode = m
    net = FMLPRecModel(a)
    f = sum(p.numel() for n, p in net.named_parameters()
            if 'complex_weight' in n or 'channel_gain' in n)
    net(torch.randint(1, 12000, (4, 50)))       # forward must not raise
    flag = 'OK' if f == EXPECT[m] else f'MISMATCH (expected {EXPECT[m]})'
    ok &= f == EXPECT[m]
    print(f'  {m:<7} filter_params={f:>6}  {flag}')
raise SystemExit(0 if ok else 1)
PY
echo
echo "setup complete. Next:"
echo "  BSAREC_DIR=$BSAREC_DIR ./run_all.sh 6 LastFM:5 Beauty:5 Toys_and_Games:5 ML-1M:5"
