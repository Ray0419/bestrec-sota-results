"""Generate figures with the updated V2 LC2C-direct numbers."""
import os, json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = os.path.dirname(__file__)
FIG_DIR = os.path.join(ROOT, "figures")

ablation = json.load(open(os.path.join(ROOT, "results_ablation_lc2c.json")))
DATASETS = ['beauty', 'fashion', 'instruments', 'books']

plt.rcParams.update({'font.size': 11, 'figure.dpi': 100, 'savefig.dpi': 200,
                      'savefig.bbox': 'tight'})

# ============================================================
# Updated cold-ITEM figure with V2 (no SVD) as canonical
# ============================================================
fig, ax = plt.subplots(figsize=(11, 5.5))
methods = ['V0_content_direct', 'V1_lc2c_full_k64', 'V2_lc2c_no_svd']
labels = ['Content KNN (X·S)', 'LC2C V1 (with SVD k=64)', 'LC2C V2 (no SVD, ours)']
colors = ['#3498db', '#9b59b6', '#16a085']
n_methods = len(methods)
x = np.arange(len(DATASETS))
width = 0.25

for i, m in enumerate(methods):
    means, stds = [], []
    for ds in DATASETS:
        v = ablation.get(ds, {}).get(m, {})
        means.append(v.get('NDCG@10', np.nan))
        stds.append(v.get('NDCG@10_std', 0))
    means = np.array(means); stds = np.array(stds)
    bars = ax.bar(x + (i - n_methods/2 + 0.5) * width, means, width,
                   yerr=stds, label=labels[i], color=colors[i],
                   edgecolor='black', linewidth=0.5,
                   error_kw={'linewidth': 0.8, 'capsize': 2})
    if 'V2' in m:
        for b in bars: b.set_edgecolor('black'); b.set_linewidth(2.0)
    if 'V2' in m:
        for j, val in enumerate(means):
            if not np.isnan(val) and val > 0:
                cd = ablation.get(DATASETS[j], {}).get('V0_content_direct', {}).get('NDCG@10', 0)
                if cd > 0:
                    pct = (val - cd) / cd * 100
                    ax.text(j + (i - n_methods/2 + 0.5) * width, val + 0.005,
                             f'+{pct:.0f}%', ha='center', fontsize=10, fontweight='bold')

ax.set_xticks(x)
ax.set_xticklabels([ds.capitalize() for ds in DATASETS])
ax.set_ylabel('NDCG@10')
ax.set_title('Cold-item GroupKFold evaluation (ranking among held-out 20% item fold): '
              'LC2C-direct (V2) is the canonical algorithm.\n'
              'Annotations: V2 (ours) mean-NDCG improvement over content-direct baseline.')
ax.legend(loc='upper right', frameon=True)
ax.grid(True, axis='y', alpha=0.3); ax.set_axisbelow(True)
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "fig7_cold_item_v2.png"))
plt.savefig(os.path.join(FIG_DIR, "fig7_cold_item_v2.pdf"))
plt.close(fig)
print(f"Saved fig7_cold_item_v2.{{png,pdf}}")

# ============================================================
# LC2C Component Ablation figure
# ============================================================
fig, ax = plt.subplots(figsize=(11, 5.5))
abl_methods = ['V0_content_direct', 'V3_lc2c_no_ridge_k64', 'V1_lc2c_full_k64', 'V2_lc2c_no_svd']
abl_labels = ['V0: Content KNN (no LC2C)',
               'V3: SVD + nearest-warm (no Ridge)',
               'V1: SVD + Ridge (k=64)',
               'V2: Ridge only, full B-row (ours)']
abl_colors = ['#888888', '#e67e22', '#9b59b6', '#16a085']
n_methods_a = len(abl_methods)
x = np.arange(len(DATASETS))
width = 0.18
for i, m in enumerate(abl_methods):
    means, stds = [], []
    for ds in DATASETS:
        v = ablation.get(ds, {}).get(m, {})
        means.append(v.get('NDCG@10', np.nan))
        stds.append(v.get('NDCG@10_std', 0))
    means = np.array(means); stds = np.array(stds)
    bars = ax.bar(x + (i - n_methods_a/2 + 0.5) * width, means, width,
                   yerr=stds, label=abl_labels[i], color=abl_colors[i],
                   edgecolor='black', linewidth=0.5,
                   error_kw={'linewidth': 0.8, 'capsize': 2})
    if 'V2' in m:
        for b in bars: b.set_edgecolor('black'); b.set_linewidth(2.0)
ax.set_xticks(x)
ax.set_xticklabels([ds.capitalize() for ds in DATASETS])
ax.set_ylabel('NDCG@10')
ax.set_title('LC2C Component Ablation — does each piece contribute?')
ax.legend(loc='upper right', frameon=True, fontsize=10)
ax.grid(True, axis='y', alpha=0.3); ax.set_axisbelow(True)
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "fig8_lc2c_ablation.png"))
plt.savefig(os.path.join(FIG_DIR, "fig8_lc2c_ablation.pdf"))
plt.close(fig)
print(f"Saved fig8_lc2c_ablation.{{png,pdf}}")

# ============================================================
# Latent dimension sensitivity
# ============================================================
fig, ax = plt.subplots(figsize=(8, 5))
ks = [16, 64, 256]
markers = ['o', 's', '^', 'D']
for ds_idx, ds in enumerate(DATASETS):
    ndcgs = []
    for k in ks:
        v = ablation.get(ds, {}).get(f'V1_lc2c_full_k{k}', {})
        ndcgs.append(v.get('NDCG@10', np.nan))
    # Add V2 as horizontal reference line
    v2 = ablation.get(ds, {}).get('V2_lc2c_no_svd', {}).get('NDCG@10', np.nan)
    ax.plot(ks, ndcgs, marker=markers[ds_idx], markersize=10, linewidth=2,
             label=ds.capitalize() + ' (V1, varying k)',
             markeredgecolor='black', markeredgewidth=1)
    if not np.isnan(v2):
        ax.axhline(y=v2, color=f'C{ds_idx}', linestyle='--', alpha=0.5,
                    label=f'{ds.capitalize()} V2 (no SVD) = {v2:.3f}')

ax.set_xscale('log')
ax.set_xlabel('SVD latent dimension k (V1 only)')
ax.set_ylabel('NDCG@10')
ax.set_title('LC2C V1 latent-dim sensitivity vs V2 (dashed)\n'
              'V2 outperforms V1 on Beauty/Instruments/Books; ties/slightly loses on Fashion')
ax.legend(loc='best', frameon=True, fontsize=8, ncol=2)
ax.grid(True, alpha=0.3); ax.set_axisbelow(True)
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "fig9_lc2c_latentdim.png"))
plt.savefig(os.path.join(FIG_DIR, "fig9_lc2c_latentdim.pdf"))
plt.close(fig)
print(f"Saved fig9_lc2c_latentdim.{{png,pdf}}")


# Print summary
print('\n=== LC2C Ablation summary (paper table) ===')
print(f'{"Method":<28}', end='')
for ds in DATASETS: print(f'{ds:>14}', end='')
print()
print('-' * (28 + 15 * len(DATASETS)))
for m, label in zip(abl_methods, abl_labels):
    print(f'{label:<28}', end='')
    for ds in DATASETS:
        v = ablation.get(ds, {}).get(m, {})
        ndcg = v.get('NDCG@10', np.nan)
        if not np.isnan(ndcg):
            print(f' {ndcg:.4f}      '.rjust(15), end='')
        else:
            print(f' {"--":>14}', end='')
    print()

print('\nV2 vs V1 (with SVD):')
for ds in DATASETS:
    v1 = ablation.get(ds, {}).get('V1_lc2c_full_k64', {}).get('NDCG@10', 0)
    v2 = ablation.get(ds, {}).get('V2_lc2c_no_svd', {}).get('NDCG@10', 0)
    if v1 > 0:
        pct = (v2 - v1) / v1 * 100
        print(f'  {ds:<14}: V1={v1:.4f}  V2={v2:.4f}  delta=+{pct:.1f}%')

print('\nV2 vs V0 (content_direct, no LC2C):')
for ds in DATASETS:
    v0 = ablation.get(ds, {}).get('V0_content_direct', {}).get('NDCG@10', 0)
    v2 = ablation.get(ds, {}).get('V2_lc2c_no_svd', {}).get('NDCG@10', 0)
    if v0 > 0:
        pct = (v2 - v0) / v0 * 100
        print(f'  {ds:<14}: V0={v0:.4f}  V2={v2:.4f}  delta=+{pct:.1f}%')
