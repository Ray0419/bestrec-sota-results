"""Create a top-journal-quality architecture diagram for BEST-Rec v4.

Shows the full data flow:
  Raw jsonl -> Dedup -> K-core -> [SBERT title encoding] + [X matrix]
            -> Three split protocols
            -> S_content (cosine sim)
            -> Augmented Gram G + Cholesky -> B
            -> Two paths:
               - Warm:  score = X @ B
               - Cold:  Ridge(SBERT -> B-row) -> score for cold j
            -> Rating head (Ridge) -> ratings
            -> Metrics: NDCG@10, HR@10, MRR, MAE, RMSE
"""
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
from matplotlib.patches import ConnectionPatch
import numpy as np

ROOT = "C:/Users/rayxc/Documents/R"
OUT_DIR = os.path.join(ROOT, "figures")
os.makedirs(OUT_DIR, exist_ok=True)


# ============================================================
# Color palette (top-journal: muted, distinguishable, print-friendly)
# ============================================================
C_RAW    = '#FAE3D9'   # raw data: warm beige
C_PREP   = '#FFD4A3'   # preprocessing: peach
C_DATA   = '#FFFFE0'   # data structures: light yellow
C_TEXT   = '#D4E6F1'   # SBERT/text: light blue
C_WARM   = '#D5F0DC'   # warm path: light green
C_COLD   = '#F5D0E8'   # cold path: pink
C_HEAD   = '#E8DAEF'   # heads: lavender
C_OUT    = '#FADBD8'   # output: pale red
C_ARROW  = '#34495E'   # arrows: dark slate
C_TEXT_  = '#1B2631'   # text: very dark


def draw_box(ax, x, y, w, h, text, color, fontsize=9, bold=False, italic=False,
              edgecolor='black', lw=1.0, rounded=True):
    """Draw a rounded box with text inside."""
    if rounded:
        box = FancyBboxPatch((x, y), w, h,
                              boxstyle="round,pad=0.04,rounding_size=0.08",
                              linewidth=lw, edgecolor=edgecolor, facecolor=color)
    else:
        box = Rectangle((x, y), w, h, linewidth=lw,
                         edgecolor=edgecolor, facecolor=color)
    ax.add_patch(box)
    weight = 'bold' if bold else 'normal'
    style = 'italic' if italic else 'normal'
    ax.text(x + w/2, y + h/2, text, ha='center', va='center',
             fontsize=fontsize, fontweight=weight, fontstyle=style,
             color=C_TEXT_, wrap=True)


def draw_arrow(ax, x1, y1, x2, y2, label=None, color=C_ARROW, lw=1.5,
               style='-|>', mutation_scale=14, dashed=False, label_offset=(0, 0)):
    linestyle = '--' if dashed else '-'
    arr = FancyArrowPatch((x1, y1), (x2, y2),
                           arrowstyle=style, mutation_scale=mutation_scale,
                           linewidth=lw, color=color, linestyle=linestyle,
                           connectionstyle="arc3,rad=0")
    ax.add_patch(arr)
    if label:
        mx = (x1 + x2) / 2 + label_offset[0]
        my = (y1 + y2) / 2 + label_offset[1]
        ax.text(mx, my, label, ha='center', va='center', fontsize=8,
                 color=C_TEXT_, fontstyle='italic',
                 bbox=dict(facecolor='white', edgecolor='none', alpha=0.8, pad=1))


# ============================================================
# Layout
# ============================================================
fig, ax = plt.subplots(figsize=(15, 12))
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.set_aspect('equal')
ax.axis('off')

# Title
ax.text(50, 97, 'BEST-Rec v4: End-to-End Architecture',
        ha='center', va='top', fontsize=15, fontweight='bold',
        color=C_TEXT_)
ax.text(50, 94.2, 'From raw Amazon Reviews 2023 jsonl to ranking & rating predictions',
        ha='center', va='top', fontsize=10, style='italic', color='#555555')


# ============================================================
# STAGE 1: Raw data (top)
# ============================================================
ax.text(2, 90, 'STAGE 1', fontsize=8, fontweight='bold', color='#7F8C8D')
ax.text(2, 88.7, 'Data ingest', fontsize=8, color='#7F8C8D', style='italic')

draw_box(ax, 8, 86, 18, 5,
         'Amazon Reviews 2023\n(.jsonl: interactions + metadata)',
         C_RAW, fontsize=9, bold=True)

draw_box(ax, 32, 86, 18, 5,
         'Item title strings\n(parent_asin -> title)',
         C_RAW, fontsize=9, bold=True)


# ============================================================
# STAGE 2: Preprocessing
# ============================================================
ax.text(2, 80, 'STAGE 2', fontsize=8, fontweight='bold', color='#7F8C8D')
ax.text(2, 78.7, 'Preprocessing', fontsize=8, color='#7F8C8D', style='italic')

draw_box(ax, 8, 74, 18, 4,
         'Dedup by (user, item):\nkeep latest rating',
         C_PREP, fontsize=9)

draw_box(ax, 8, 67, 18, 4,
         'K-core filtering:\nk={4,5,10,20}',
         C_PREP, fontsize=9)


# ============================================================
# STAGE 3: Splits + Encodings
# ============================================================
ax.text(2, 61, 'STAGE 3', fontsize=8, fontweight='bold', color='#7F8C8D')
ax.text(2, 59.7, 'Encodings', fontsize=8, color='#7F8C8D', style='italic')

# Sparse interaction matrix
draw_box(ax, 4, 53, 14, 5,
         'Sparse X in R^{m×n}\nbinary user-item matrix',
         C_DATA, fontsize=9, bold=True)

# Three splits
draw_box(ax, 20, 53, 14, 5,
         '3 split protocols\n(warm LOO, cold-user GKF, cold-item GKF)',
         C_DATA, fontsize=8)

# SBERT model
draw_box(ax, 36, 65, 18, 4,
         'SBERT (all-MiniLM-L6-v2)\nfrozen, pretrained',
         C_TEXT, fontsize=9, bold=True)

# Title embeddings
draw_box(ax, 36, 53, 18, 5,
         'Title embeddings\ne_i in R^{384}, i=1..n',
         C_TEXT, fontsize=9, bold=True)

# S_content
draw_box(ax, 56, 53, 14, 5,
         'S_content in R^{n×n}\ncosine(e_i, e_j), diag=0',
         C_TEXT, fontsize=9, bold=True)


# ============================================================
# STAGE 4: EASE + SBERT (warm)
# ============================================================
ax.text(2, 47, 'STAGE 4', fontsize=8, fontweight='bold', color='#7F8C8D')
ax.text(2, 45.7, 'EASE + SBERT\n(closed form)', fontsize=8, color='#7F8C8D', style='italic')

# Augmented Gram
draw_box(ax, 14, 41, 26, 4,
         'Augmented Gram:  G = X^T X + λI + β·S_content',
         C_WARM, fontsize=10, bold=True)

# Cholesky / inversion
draw_box(ax, 14, 35, 26, 4,
         'Cholesky / LU solver:  P = G^{-1}',
         C_WARM, fontsize=10)

# B matrix
draw_box(ax, 14, 29, 26, 4,
         'B = -P / diag(P);  diag(B) = 0',
         C_WARM, fontsize=10, bold=True)


# ============================================================
# STAGE 5a: Warm scoring path
# ============================================================
ax.text(2, 23, 'STAGE 5', fontsize=8, fontweight='bold', color='#7F8C8D')
ax.text(2, 21.7, 'Two scoring\npaths', fontsize=8, color='#7F8C8D', style='italic')

draw_box(ax, 14, 18, 26, 4,
         'WARM:  score(u, i) = (X @ B)[u, i]',
         C_WARM, fontsize=10, bold=True)


# ============================================================
# STAGE 5b: Cold-item scoring (LC2C)
# ============================================================
draw_box(ax, 50, 41, 32, 4,
         'B_warm: EASE on warm items only',
         C_COLD, fontsize=10)

draw_box(ax, 50, 35, 32, 4,
         'Ridge:  W = argmin ||SBERT_warm·W − B_warm^T||²',
         C_COLD, fontsize=9, bold=True)

draw_box(ax, 50, 29, 32, 4,
         'Predict:  B_cold[j] = (SBERT(t_j) · W)^T',
         C_COLD, fontsize=10)

draw_box(ax, 50, 18, 32, 4,
         'COLD:  score(u, j_cold) = X[u] · B_cold[j]',
         C_COLD, fontsize=10, bold=True)


# ============================================================
# STAGE 6: Heads
# ============================================================
ax.text(2, 11.5, 'STAGE 6', fontsize=8, fontweight='bold', color='#7F8C8D')
ax.text(2, 10.2, 'Prediction\nheads', fontsize=8, color='#7F8C8D', style='italic')

# Ranking head
draw_box(ax, 14, 6, 32, 6,
         'Ranking head\nFull-item ranking among unseen items\n→ NDCG@10, HR@10, MRR',
         C_HEAD, fontsize=10, bold=True)

# Rating head
draw_box(ax, 50, 6, 32, 6,
         'Rating head: Ridge regression\nr̂ = clip(w₀ + w₁·b_u + w₂·b_i + w₃·score, 1, 5)\n→ MAE, RMSE',
         C_HEAD, fontsize=9, bold=True)


# ============================================================
# Significance/baseline panel (right side)
# ============================================================
draw_box(ax, 86, 43, 12, 16,
         'BASELINES\n(per fold)\n\n• Popularity\n• iALS\n• MultiVAE\n• LightGCN\n• EASE-pure\n• Higher-Order EASE\n\n→ paired Wilcoxon\n  vs. ours',
         '#FDFEFE', fontsize=8, italic=True)


# ============================================================
# DRAW ARROWS — flow connections
# ============================================================
# Stage 1 -> 2
draw_arrow(ax, 17, 86, 17, 78)
draw_arrow(ax, 41, 86, 41, 69, label='SBERT inputs', label_offset=(2, 0))

# Within stage 2 (dedup -> kcore)
draw_arrow(ax, 17, 74, 17, 71)

# Stage 2 -> 3
draw_arrow(ax, 13, 67, 11, 58, label='X', label_offset=(-2, 0))
draw_arrow(ax, 21, 67, 27, 58, label='groups', label_offset=(2, 0))

# Title embeddings
draw_arrow(ax, 45, 65, 45, 58)

# SBERT -> S_content
draw_arrow(ax, 54, 55.5, 56, 55.5)

# Stage 3 -> 4 (G construction)
draw_arrow(ax, 11, 53, 18, 45, label='X^T X', label_offset=(-3, 0))
draw_arrow(ax, 63, 53, 36, 45, label='β·S_content', label_offset=(2, 0))

# Stage 4 internal
draw_arrow(ax, 27, 41, 27, 39)
draw_arrow(ax, 27, 35, 27, 33)

# Stage 4 -> Stage 5 (warm and cold paths split)
draw_arrow(ax, 22, 29, 22, 22, label='warm', label_offset=(-3, 0), color='#27AE60')
draw_arrow(ax, 35, 29, 50, 45, label='warm only', label_offset=(0, 1), color='#C0392B', dashed=True)

# LC2C path
draw_arrow(ax, 66, 41, 66, 39)
draw_arrow(ax, 66, 35, 66, 33)
draw_arrow(ax, 66, 29, 66, 22)

# SBERT -> Ridge (LC2C)
draw_arrow(ax, 70, 55, 70, 39, label='SBERT_cold', label_offset=(4, 0), color='#C0392B', dashed=True)

# Stage 5 -> 6
draw_arrow(ax, 22, 18, 22, 12)
draw_arrow(ax, 66, 18, 30, 12, label='cold-item ranks', label_offset=(0, 1), color='#27AE60')
draw_arrow(ax, 66, 18, 66, 12)

# Cross to rating head
draw_arrow(ax, 35, 9, 50, 9, label='', mutation_scale=10)


# ============================================================
# Legend
# ============================================================
legend_x = 86; legend_y = 90
ax.text(legend_x, legend_y, 'LEGEND', fontsize=9, fontweight='bold')
legend_items = [
    (C_RAW, 'Raw / external data'),
    (C_PREP, 'Preprocessing'),
    (C_DATA, 'Data structures'),
    (C_TEXT, 'Text content (SBERT)'),
    (C_WARM, 'Warm path (EASE)'),
    (C_COLD, 'Cold path (LC2C)'),
    (C_HEAD, 'Prediction heads'),
]
for i, (col, lbl) in enumerate(legend_items):
    y = legend_y - 2.5 - i * 2.2
    rect = Rectangle((legend_x, y), 1.5, 1.4, facecolor=col,
                      edgecolor='black', linewidth=0.5)
    ax.add_patch(rect)
    ax.text(legend_x + 2, y + 0.7, lbl, fontsize=8, va='center')


# Save
out_png = os.path.join(OUT_DIR, "fig_architecture_overview.png")
out_pdf = os.path.join(OUT_DIR, "fig_architecture_overview.pdf")
plt.savefig(out_png, dpi=200, bbox_inches='tight', pad_inches=0.3)
plt.savefig(out_pdf, bbox_inches='tight', pad_inches=0.3)
plt.close(fig)
print(f"Saved: {out_png}")
print(f"Saved: {out_pdf}")
