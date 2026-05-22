"""Top-journal architecture diagram v3 - clean flow, swim lanes, orthogonal routing.

Final layout principles
-----------------------
* Single top-to-bottom flow with two horizontal swim lanes (warm vs.
  cold-item) starting at Stage 5.
* Compact stage badges anchored at the top-left corner of each band,
  inline with title; subtitle sits flush-right of the same band so it
  cannot collide with content boxes.
* Manhattan (orthogonal) connectors with explicit junction dots; no
  diagonal arrow crosses any box.
* The W = Ridge training step lives inside the cold-item swim lane
  (not floating in the solver stage) so the cold-item flow reads top-down
  in a single column.
* No long advisory arrows that cross the canvas.  Instead, the cold-item
  scoring box names the inputs it uses inside its own caption.
"""
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import (FancyBboxPatch, FancyArrowPatch, Rectangle,
                                 Circle)

ROOT = "C:/Users/rayxc/Documents/R"
OUT_DIR = os.path.join(ROOT, "figures")
os.makedirs(OUT_DIR, exist_ok=True)

# -------------------------------------------------------------------------
# Color palette
# -------------------------------------------------------------------------
C_BG_A      = '#FBFCFD'
C_BG_B      = '#F1F4F7'
C_RAW       = '#FCE4D6'
C_PREP      = '#FFE6B3'
C_DATA      = '#FFF7C2'
C_TEXT      = '#D6E4F0'
C_CORE      = '#CFE7DC'
C_WARM      = '#BFE3C8'
C_COLD      = '#F4D1E6'
C_HEAD      = '#E2D3F0'
C_OUT       = '#F8C8C0'
C_BADGE     = '#2C3E50'
C_BADGE_T   = '#FFFFFF'
C_ARROW     = '#34495E'
C_ARROW_C   = '#B03A60'
C_ARROW_W   = '#1E8449'
C_TXT       = '#1B2631'
C_MUTED     = '#566573'
C_LANE_W_F  = '#E9F7EE'
C_LANE_W_E  = '#27AE60'
C_LANE_C_F  = '#FBE7F1'
C_LANE_C_E  = '#B03A60'


def rbox(ax, x, y, w, h, text, color, fontsize=10, bold=False, italic=False,
         edge='#1F2D3D', lw=1.0, pad=0.06, zorder=3):
    b = FancyBboxPatch((x, y), w, h,
                       boxstyle=f"round,pad={pad},rounding_size=0.18",
                       linewidth=lw, edgecolor=edge, facecolor=color,
                       zorder=zorder)
    ax.add_patch(b)
    weight = 'bold' if bold else 'normal'
    style  = 'italic' if italic else 'normal'
    ax.text(x + w/2, y + h/2, text, ha='center', va='center',
            fontsize=fontsize, fontweight=weight, fontstyle=style,
            color=C_TXT, zorder=zorder + 1)


def straight_arrow(ax, x1, y1, x2, y2, color=C_ARROW, lw=1.6, dashed=False,
                   label=None, label_pos=0.5, label_off=(0, 0),
                   label_color=None):
    style = '--' if dashed else '-'
    arr = FancyArrowPatch((x1, y1), (x2, y2),
                          arrowstyle='-|>',
                          mutation_scale=16, linewidth=lw, color=color,
                          linestyle=style, zorder=2)
    ax.add_patch(arr)
    if label:
        mx = x1 + (x2 - x1) * label_pos + label_off[0]
        my = y1 + (y2 - y1) * label_pos + label_off[1]
        ax.text(mx, my, label, ha='center', va='center', fontsize=8.6,
                color=label_color or C_TXT, fontstyle='italic',
                bbox=dict(facecolor='white', edgecolor='none',
                          alpha=0.95, pad=1.8), zorder=4)


def L_arrow(ax, x1, y1, x2, y2, color=C_ARROW, lw=1.6, dashed=False,
            label=None, label_off=(0, 0), label_color=None, side='V'):
    """Right-angle arrow with rounded corner."""
    style = '--' if dashed else '-'
    if side == 'V':
        corner = (x1, y2)
        label_xy = (x1, (y1 + y2) / 2)
    else:
        corner = (x2, y1)
        label_xy = ((x1 + x2) / 2, y1)

    seg1 = FancyArrowPatch((x1, y1), corner,
                           arrowstyle='-', mutation_scale=10,
                           linewidth=lw, color=color, linestyle=style,
                           zorder=2)
    seg2 = FancyArrowPatch(corner, (x2, y2),
                           arrowstyle='-|>', mutation_scale=16,
                           linewidth=lw, color=color, linestyle=style,
                           zorder=2)
    ax.add_patch(seg1)
    ax.add_patch(seg2)
    if label:
        mx = label_xy[0] + label_off[0]
        my = label_xy[1] + label_off[1]
        ax.text(mx, my, label, ha='center', va='center', fontsize=8.6,
                color=label_color or C_TXT, fontstyle='italic',
                bbox=dict(facecolor='white', edgecolor='none',
                          alpha=0.95, pad=1.8), zorder=4)


def stage_band(ax, y_lo, y_hi, color):
    ax.add_patch(Rectangle((0, y_lo), 100, y_hi - y_lo,
                           facecolor=color, edgecolor='none', zorder=0))


def stage_header(ax, n, y_top, title, sub):
    """Inline header at the top of a band: badge + title (left), subtitle (right)."""
    cx, cy, r = 4.0, y_top - 1.7, 1.6
    ax.add_patch(Circle((cx, cy), r, facecolor=C_BADGE, edgecolor='none',
                        zorder=5))
    ax.text(cx, cy, str(n), ha='center', va='center', fontsize=11,
            fontweight='bold', color=C_BADGE_T, zorder=6)
    ax.text(cx + r + 1.0, cy, title, fontsize=10.8, fontweight='bold',
            color=C_TXT, ha='left', va='center', zorder=6)
    if sub:
        ax.text(99, cy, sub, fontsize=8.6, fontstyle='italic',
                color=C_MUTED, ha='right', va='center', zorder=6)


def merge_dot(ax, x, y, color=C_ARROW):
    ax.add_patch(Circle((x, y), 0.45, facecolor=color, edgecolor='none',
                        zorder=4))


# =========================================================================
# Layout constants
# =========================================================================
fig, ax = plt.subplots(figsize=(13.5, 19.5))
ax.set_xlim(0, 100)
ax.set_ylim(-3, 152)
ax.set_aspect('equal')
ax.axis('off')

# -------------------------------------------------------------------------
# Title
# -------------------------------------------------------------------------
ax.text(50, 150, 'BEST-Rec v4: End-to-End Architecture',
        ha='center', va='top', fontsize=18, fontweight='bold', color=C_TXT)
ax.text(50, 146,
        'Closed-form linear recommender with SBERT content prior + LC2C cold-item mapping',
        ha='center', va='top', fontsize=11, fontstyle='italic', color=C_MUTED)

# -------------------------------------------------------------------------
# Stage definitions
# (lo, hi, band_color, badge_n, title, subtitle)
# -------------------------------------------------------------------------
STAGES = [
    (126, 142, C_BG_A, 1, 'Raw input',          'Amazon Reviews 2023 JSONL'),
    (108, 126, C_BG_B, 2, 'Preprocessing',      'dedup, retain titles, k-core'),
    ( 86, 108, C_BG_A, 3, 'Encodings & splits', 'sparse X, three split protocols, SBERT embeddings'),
    ( 68,  86, C_BG_B, 4, 'EASE + SBERT solver','closed-form item-item matrix B'),
    ( 38,  68, C_BG_A, 5, 'Scoring',            'warm path / cold-item LC2C path'),
    ( 22,  38, C_BG_B, 6, 'Prediction heads',   'ranking head + ridge rating head'),
    (  6,  22, C_BG_A, 7, 'Reported metrics',   '5-fold mean ± std + paired Wilcoxon'),
]
for lo, hi, c, *_ in STAGES:
    stage_band(ax, lo, hi, c)
for lo, hi, c, n, t, s in STAGES:
    stage_header(ax, n, hi, t, s)


# =========================================================================
# STAGE 1 - Raw input  (band 126-142)
# =========================================================================
rbox(ax, 22, 132, 30, 5.5,
     'Interactions JSONL\n(user_id, parent_asin, rating, ts)',
     C_RAW, fontsize=9.8, bold=True)
rbox(ax, 60, 132, 30, 5.5,
     'Item metadata JSONL\n(parent_asin → title, price, ...)',
     C_RAW, fontsize=9.8, bold=True)


# =========================================================================
# STAGE 2 - Preprocessing  (band 108-126)
# =========================================================================
rbox(ax, 22, 117, 30, 4.5,
     'Stream parse + dedup by (u, i)\nkeep latest rating per pair',
     C_PREP, fontsize=9.4)
rbox(ax, 60, 117, 30, 4.5,
     'Stream parse, retain only titles\nfor items present in interactions',
     C_PREP, fontsize=9.4)

rbox(ax, 30, 109, 40, 4.6,
     'k-core filter   ( k = 4 / 5 / 10 / 20 )',
     C_PREP, fontsize=10.5, bold=True)


# =========================================================================
# STAGE 3 - Encodings & splits  (band 86-108)
# =========================================================================
# left: X
rbox(ax, 14, 96, 22, 5,
     'Sparse  X ∈ {0,1}^(m×n)',
     C_DATA, fontsize=10, bold=True)

# centre: splits
rbox(ax, 39, 96, 22, 5,
     'Three split protocols',
     C_DATA, fontsize=10, bold=True)
rbox(ax, 39, 90.5, 22, 4,
     'warm LOO  •  cold-user  •  cold-item',
     C_DATA, fontsize=8.6, italic=True)

# right: SBERT chain
rbox(ax, 64, 96, 22, 5,
     'SBERT all-MiniLM-L6-v2',
     C_TEXT, fontsize=9.8, bold=True)
rbox(ax, 64, 90.5, 22, 4,
     'e_i = SBERT(title_i) ∈ R^384',
     C_TEXT, fontsize=9.3)
rbox(ax, 64, 86.6, 22, 3.4,
     'S_content[i,j] = cos(e_i, e_j)',
     C_TEXT, fontsize=9.4, bold=True)


# =========================================================================
# STAGE 4 - EASE+SBERT solver  (band 68-86)
# =========================================================================
rbox(ax, 22, 71, 56, 9,
     'G  =  Xᵀ X  +  λ I  +  β · S_content\n'
     'P  =  G⁻¹       (Cholesky → LU → pinv fallback)\n'
     'B  =  − P / diag(P);     diag(B) = 0',
     C_CORE, fontsize=11.5, bold=True)


# =========================================================================
# STAGE 5 - Scoring  (band 38-68) - two swim lanes
# =========================================================================
LANE_LO = 40
LANE_HI = 63

# Lane backgrounds (slightly inset from the band edges)
ax.add_patch(Rectangle((10, LANE_LO), 38, LANE_HI - LANE_LO,
                       facecolor=C_LANE_W_F, edgecolor=C_LANE_W_E,
                       linewidth=1.2, alpha=0.55, zorder=1))
ax.add_patch(Rectangle((52, LANE_LO), 38, LANE_HI - LANE_LO,
                       facecolor=C_LANE_C_F, edgecolor=C_LANE_C_E,
                       linewidth=1.2, alpha=0.55, zorder=1))

# Lane headers (clearly inside the lane, well below the top border)
ax.text(29, LANE_HI - 2.4, 'WARM PATH',
        ha='center', va='center', fontsize=10.5, fontweight='bold',
        color=C_LANE_W_E, zorder=2)
ax.text(71, LANE_HI - 2.4, 'COLD-ITEM PATH  (LC2C)',
        ha='center', va='center', fontsize=10.5, fontweight='bold',
        color=C_LANE_C_E, zorder=2)

# Warm lane: a single scoring box (centered vertically within lane)
rbox(ax, 13, 47, 32, 7,
     'score(u, i)\n=\n( X · B )[u, i]',
     C_WARM, fontsize=11, bold=True)

# Cold lane: training step, then mapping step, then scoring step
rbox(ax, 55, 54.5, 32, 4.2,
     'Train:  W  =  Ridge_α=μ ( e_warm  →  B_warmᵀ )',
     C_COLD, fontsize=9.4, italic=True)

rbox(ax, 55, 48.5, 32, 4.2,
     'Map:   B̂[:, j_cold]  =  ( e_j · W )ᵀ',
     C_COLD, fontsize=9.8)

rbox(ax, 55, 42, 32, 4.2,
     'Score:  score(u, j)  =  X[u] · B̂[:, j]',
     C_COLD, fontsize=9.8, bold=True)


# =========================================================================
# STAGE 6 - Prediction heads  (band 22-38)
# =========================================================================
rbox(ax, 13, 25, 32, 8.5,
     'Ranking head\n'
     'rank against full unseen-item set\n'
     '→ NDCG@10,  HR@10,  MRR',
     C_HEAD, fontsize=10, bold=True)

rbox(ax, 55, 25, 32, 8.5,
     'Rating head  (ridge regression)\n'
     'r̂ = clip( w₀ + w₁·b_u + w₂·b_i + w₃·s,  1, 5 )\n'
     '→ MAE,  RMSE',
     C_HEAD, fontsize=9.4, bold=True)


# =========================================================================
# STAGE 7 - Output  (band 6-22)
# =========================================================================
rbox(ax, 22, 10, 56, 8,
     'NDCG@10   •   HR@10   •   MRR   •   MAE   •   RMSE\n\n'
     'paired Wilcoxon p-values vs. each baseline',
     C_OUT, fontsize=10.8, bold=True)


# =========================================================================
# Arrows
# =========================================================================
# Stage 1 -> Stage 2
straight_arrow(ax, 37, 132, 37, 121.5)
straight_arrow(ax, 75, 132, 75, 121.5)

# Stage 2 internal: both feeds -> k-core
L_arrow(ax, 37, 117, 50, 113.6, side='V')
L_arrow(ax, 75, 117, 50, 113.6, side='V')
merge_dot(ax, 50, 113.6)

# Stage 2 -> Stage 3 (k-core fans into three columns at y=101)
merge_dot(ax, 50, 109)
L_arrow(ax, 50, 109, 25, 101, side='V', label='X', label_off=(-3.6, 0))
straight_arrow(ax, 50, 109, 50, 101, label='groups', label_off=(3.4, 0))
L_arrow(ax, 50, 109, 75, 101, side='V', label='titles', label_off=(3.0, 0))

# Stage 3 internal vertical chains (right column)
straight_arrow(ax, 75, 96, 75, 92.5)
straight_arrow(ax, 75, 90.5, 75, 90.0)   # tiny visual link e_i -> S_content

# Stage 3 -> Stage 4
straight_arrow(ax, 25, 96, 25, 80.0,
               label='Xᵀ X', label_off=(-3.4, 0))
L_arrow(ax, 75, 86.6, 65, 80.0, side='V',
        label='β · S_content', label_off=(2.8, 0))
# splits feed warm/cold masks (advisory dashed, short, parallel)
straight_arrow(ax, 50, 90.5, 50, 80.0, dashed=True, color=C_MUTED,
               label='warm/cold masks', label_off=(8.4, 0))

# Stage 4 -> Stage 5
# Warm lane: B (full) -> warm scoring
L_arrow(ax, 35, 71, 29, 54, side='V',
        color=C_ARROW_W, label='B', label_off=(-2.8, 5.0))
# Cold lane: B_warm subset -> Ridge training input
L_arrow(ax, 65, 71, 71, 58.7, side='V',
        color=C_ARROW_C, label='B_warm', label_off=(3.2, 4.0))

# Cold lane internal flow: train -> map -> score
straight_arrow(ax, 71, 54.5, 71, 52.7, color=C_ARROW_C,
               label='W', label_off=(2.0, 0))
straight_arrow(ax, 71, 48.5, 71, 46.2, color=C_ARROW_C,
               label='B̂[:,j]', label_off=(2.8, 0))

# Stage 5 -> Stage 6
straight_arrow(ax, 29, 47, 29, 33.5, color=C_ARROW_W,
               label='warm score', label_off=(-7, 0))
straight_arrow(ax, 71, 42, 71, 33.5, color=C_ARROW_C,
               label='cold score', label_off=(7, 0))

# Stage 6 -> Stage 7
L_arrow(ax, 29, 25, 38, 18, side='V')
L_arrow(ax, 71, 25, 62, 18, side='V')


# =========================================================================
# Legend - bottom row
# =========================================================================
legend_y = 1.5
ax.text(50, legend_y + 4.5, 'Legend', ha='center', va='bottom',
        fontsize=10.5, fontweight='bold', color=C_TXT)

legend_items = [
    (C_RAW,  'Raw input'),
    (C_PREP, 'Preprocessing'),
    (C_DATA, 'Data structure'),
    (C_TEXT, 'SBERT / content'),
    (C_CORE, 'EASE+SBERT'),
    (C_WARM, 'Warm path'),
    (C_COLD, 'Cold-item path'),
    (C_HEAD, 'Heads'),
    (C_OUT,  'Output'),
]
n = len(legend_items)
total_w = 92
slot_w = total_w / n
x0 = 4
for i, (col, lbl) in enumerate(legend_items):
    cx = x0 + slot_w * i + slot_w / 2
    ax.add_patch(Rectangle((cx - 1.6, legend_y + 1.2), 3.2, 1.7,
                           facecolor=col, edgecolor='#1F2D3D',
                           linewidth=0.6, zorder=3))
    ax.text(cx, legend_y - 0.3, lbl, fontsize=8.2, ha='center', va='top',
            color=C_TXT)

# Arrow style legend
ax.text(50, -2,
        'solid arrows: data flow         dashed arrows: derived / advisory dependency',
        ha='center', va='top', fontsize=8.5, fontstyle='italic',
        color=C_MUTED)


# =========================================================================
# Save
# =========================================================================
out_png = os.path.join(OUT_DIR, "fig_architecture_overview.png")
out_pdf = os.path.join(OUT_DIR, "fig_architecture_overview.pdf")
plt.savefig(out_png, dpi=220, bbox_inches='tight', pad_inches=0.4)
plt.savefig(out_pdf, bbox_inches='tight', pad_inches=0.4)
plt.close(fig)
print(f"Saved: {out_png}")
print(f"Saved: {out_pdf}")
