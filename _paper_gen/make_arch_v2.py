"""Top-journal architecture diagram v2 — cleaner spacing, vertical flow."""
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
import numpy as np

ROOT = "C:/Users/rayxc/Documents/R"
OUT_DIR = os.path.join(ROOT, "figures")
os.makedirs(OUT_DIR, exist_ok=True)

# Color palette: muted, distinguishable, print-friendly
C_RAW    = '#FAE3D9'
C_PREP   = '#FFD4A3'
C_DATA   = '#FFFFE0'
C_TEXT   = '#D4E6F1'
C_WARM   = '#D5F0DC'
C_COLD   = '#F5D0E8'
C_HEAD   = '#E8DAEF'
C_OUT    = '#FADBD8'
C_ARROW  = '#34495E'
C_TEXT_  = '#1B2631'


def box(ax, x, y, w, h, text, color, fontsize=10, bold=False, italic=False,
         edge='black', lw=1.2):
    b = FancyBboxPatch((x, y), w, h,
                        boxstyle="round,pad=0.05,rounding_size=0.10",
                        linewidth=lw, edgecolor=edge, facecolor=color)
    ax.add_patch(b)
    weight = 'bold' if bold else 'normal'
    style = 'italic' if italic else 'normal'
    ax.text(x + w/2, y + h/2, text, ha='center', va='center',
             fontsize=fontsize, fontweight=weight, fontstyle=style,
             color=C_TEXT_)


def arrow(ax, x1, y1, x2, y2, label=None, color=C_ARROW, lw=1.6,
          label_off=(0, 0), label_color=None, dashed=False):
    style = '--' if dashed else '-'
    a = FancyArrowPatch((x1, y1), (x2, y2),
                         arrowstyle='-|>', mutation_scale=18,
                         linewidth=lw, color=color, linestyle=style)
    ax.add_patch(a)
    if label:
        mx = (x1 + x2) / 2 + label_off[0]
        my = (y1 + y2) / 2 + label_off[1]
        ax.text(mx, my, label, ha='center', va='center', fontsize=9,
                 color=label_color or C_TEXT_, fontstyle='italic',
                 bbox=dict(facecolor='white', edgecolor='none', alpha=0.85, pad=2))


def stage(ax, x, y, label_top, label_bot=''):
    ax.text(x, y, label_top, fontsize=9, fontweight='bold', color='#566573',
             ha='left', va='top')
    if label_bot:
        ax.text(x, y - 1.5, label_bot, fontsize=8, fontstyle='italic',
                 color='#566573', ha='left', va='top')


# ============================================================
# Layout — wider canvas, more whitespace
# ============================================================
fig, ax = plt.subplots(figsize=(14, 16))
ax.set_xlim(0, 100)
ax.set_ylim(0, 130)
ax.set_aspect('equal')
ax.axis('off')

# Title
ax.text(50, 127, 'BEST-Rec v4: End-to-End Architecture',
        ha='center', va='top', fontsize=16, fontweight='bold', color=C_TEXT_)
ax.text(50, 124, 'Closed-form linear recommender with SBERT content prior + LC2C cold-item mapping',
        ha='center', va='top', fontsize=10.5, style='italic', color='#555')


# ============================================================
# STAGE 1 — Raw inputs
# ============================================================
stage(ax, 2, 120, 'STAGE 1', 'Data ingest')

box(ax, 12, 113, 30, 6,
     'Amazon Reviews 2023 jsonl\n(interactions: user_id, parent_asin, rating, ts)',
     C_RAW, fontsize=10, bold=True)
box(ax, 56, 113, 30, 6,
     'Amazon Reviews 2023 metadata\n(parent_asin -> title, price, avg_rating)',
     C_RAW, fontsize=10, bold=True)


# ============================================================
# STAGE 2 — Preprocessing
# ============================================================
stage(ax, 2, 107, 'STAGE 2', 'Preprocessing')

box(ax, 12, 100, 30, 5,
     'Stream parse + dedup by (user, item)\nkeep latest rating per pair',
     C_PREP, fontsize=10)
box(ax, 56, 100, 30, 5,
     'Stream parse, retain only items in interactions\n(saves 5-14 GB metadata RAM)',
     C_PREP, fontsize=10)

box(ax, 22, 92, 56, 5,
     'K-core filter (per dataset: k=4 Fashion, k=5 Beauty, k=10 Instr., k=20 Books)',
     C_PREP, fontsize=10, bold=True)


# ============================================================
# STAGE 3 — Encodings
# ============================================================
stage(ax, 2, 87, 'STAGE 3', 'Encodings & splits')

# Sparse interaction matrix
box(ax, 6, 78, 28, 6,
     'Sparse X in {0,1}^(m x n)\nbinary user-item matrix',
     C_DATA, fontsize=10, bold=True)

# Three splits
box(ax, 38, 78, 24, 6,
     'Three split protocols\n(LOO + 2 GroupKFold)',
     C_DATA, fontsize=9.5, bold=True)

# SBERT path
box(ax, 66, 78, 28, 6,
     'SBERT all-MiniLM-L6-v2\nfrozen, pretrained',
     C_TEXT, fontsize=10, bold=True)


# Title embeddings + S_content (next row)
box(ax, 6, 70, 28, 5,
     'item titles t_i (used by both paths)',
     C_DATA, fontsize=9, italic=True)
box(ax, 38, 70, 24, 5,
     'warm / cold-user / cold-item',
     C_DATA, fontsize=9, italic=True)
box(ax, 66, 70, 28, 5,
     'e_i = SBERT(t_i) in R^384',
     C_TEXT, fontsize=10, bold=True)

box(ax, 66, 62, 28, 5,
     'S_content[i,j] = cos(e_i, e_j); diag=0',
     C_TEXT, fontsize=10, bold=True)


# ============================================================
# STAGE 4 — EASE+SBERT (warm)
# ============================================================
stage(ax, 2, 58, 'STAGE 4', 'EASE+SBERT (closed form)')

box(ax, 18, 51, 60, 5,
     'Augmented Gram:  G = X^T X + λ I + β · S_content',
     C_WARM, fontsize=11, bold=True)

box(ax, 18, 44, 60, 5,
     'Cholesky / LU / pinv solve:  P = G^{-1}',
     C_WARM, fontsize=11)

box(ax, 18, 37, 60, 5,
     'B = -P / diag(P);  diag(B) = 0',
     C_WARM, fontsize=11, bold=True)


# ============================================================
# STAGE 5 — Two scoring paths
# ============================================================
stage(ax, 2, 32, 'STAGE 5', 'Scoring')

# Warm scoring
box(ax, 6, 24, 38, 6,
     'WARM PATH\nscore(u, i) = (X B)[u, i]',
     C_WARM, fontsize=11, bold=True)

# Cold-item scoring (LC2C)
box(ax, 56, 24, 38, 6,
     'COLD-ITEM PATH (LC2C)\nscore(u, j_cold) = X[u] · B̂[:, j_cold]',
     C_COLD, fontsize=10.5, bold=True)


# LC2C internals (above the cold scoring box)
box(ax, 56, 32, 38, 4,
     'B̂[:, j_cold] = (SBERT(t_j) · W)^T',
     C_COLD, fontsize=10)


# Box explaining W (Ridge regression) — placed to the right of Stage 4
box(ax, 80, 44, 18, 4,
     'W = Ridge(\n  SBERT_warm -> B_warm^T)',
     C_COLD, fontsize=9, italic=True)


# ============================================================
# STAGE 6 — Heads
# ============================================================
stage(ax, 2, 19, 'STAGE 6', 'Prediction heads')

box(ax, 6, 11, 38, 7,
     'Ranking head\nFull-item rank against unseen items\n→ NDCG@10, HR@10, MRR',
     C_HEAD, fontsize=10.5, bold=True)

box(ax, 56, 11, 38, 7,
     'Rating head (Ridge regression)\nr̂ = clip(w₀+w₁·b_u+w₂·b_i+w₃·score, 1, 5)\n→ MAE, RMSE',
     C_HEAD, fontsize=10, bold=True)

# Output box
box(ax, 22, 2, 56, 6,
     'Reported metrics: 5-fold mean ± std + paired-Wilcoxon p-values vs. baselines',
     C_OUT, fontsize=10.5, bold=True)


# ============================================================
# Arrows — vertical flow
# ============================================================
# Stage 1 → 2
arrow(ax, 27, 113, 27, 105)
arrow(ax, 71, 113, 71, 105)

# Within Stage 2
arrow(ax, 27, 100, 35, 97)
arrow(ax, 71, 100, 65, 97)

# Stage 2 → 3 (X, splits, SBERT inputs)
arrow(ax, 35, 92, 20, 84, label='X', label_off=(-2, 0))
arrow(ax, 50, 92, 50, 84, label='groups', label_off=(2, 0))
arrow(ax, 65, 92, 80, 84, label='titles', label_off=(2, 0))

# Within stage 3
arrow(ax, 20, 78, 20, 75)
arrow(ax, 80, 78, 80, 75)
arrow(ax, 80, 70, 80, 67)

# Stage 3 → 4
arrow(ax, 20, 70, 28, 56, label='X^T X', label_off=(-3, 0.5))
arrow(ax, 80, 62, 65, 56, label='β S_content', label_off=(2, 0.5))

# Within Stage 4
arrow(ax, 48, 51, 48, 49)
arrow(ax, 48, 44, 48, 42)

# Stage 4 → 5 split
arrow(ax, 30, 37, 25, 30, label='warm', label_off=(-3, 1), label_color='#27AE60')
arrow(ax, 65, 37, 65, 36, label='warm only\n(B_warm)', label_off=(7, 0), label_color='#C0392B')

# Cold-item internals
arrow(ax, 65, 32, 65, 30)

# SBERT cold → W → B̂
arrow(ax, 90, 67, 90, 48, label='SBERT_cold', label_off=(5, 0), dashed=True, color='#C0392B')
arrow(ax, 89, 44, 89, 36, dashed=True, color='#C0392B')

# Stage 5 → 6
arrow(ax, 25, 24, 25, 18)
arrow(ax, 75, 24, 75, 18, label='ranks of cold', label_off=(7, 0), color='#27AE60')
arrow(ax, 75, 24, 35, 18, label='', dashed=False)

# To metrics
arrow(ax, 25, 11, 35, 8)
arrow(ax, 75, 11, 65, 8)


# ============================================================
# Legend (bottom right)
# ============================================================
legend_x = 78
legend_y = 99
ax.text(legend_x, legend_y, 'Legend', fontsize=10, fontweight='bold', va='top')
items = [
    (C_RAW, 'Raw / external'),
    (C_PREP, 'Preprocessing'),
    (C_DATA, 'Data structures'),
    (C_TEXT, 'Text content'),
    (C_WARM, 'EASE warm path'),
    (C_COLD, 'LC2C cold path'),
    (C_HEAD, 'Prediction heads'),
    (C_OUT, 'Output metrics'),
]
for i, (col, lbl) in enumerate(items):
    y = legend_y - 2.5 - i * 1.6
    rect = Rectangle((legend_x, y), 1.5, 1.2, facecolor=col,
                      edgecolor='black', linewidth=0.6)
    ax.add_patch(rect)
    ax.text(legend_x + 2, y + 0.6, lbl, fontsize=8.5, va='center')


# Save
out_png = os.path.join(OUT_DIR, "fig_architecture_overview.png")
out_pdf = os.path.join(OUT_DIR, "fig_architecture_overview.pdf")
plt.savefig(out_png, dpi=200, bbox_inches='tight', pad_inches=0.4)
plt.savefig(out_pdf, bbox_inches='tight', pad_inches=0.4)
plt.close(fig)
print(f"Saved: {out_png}")
print(f"Saved: {out_pdf}")
