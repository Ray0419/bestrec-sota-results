"""Add cold-item figure to the figures collection."""
import os, json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = os.path.dirname(__file__)
FIG_DIR = os.path.join(ROOT, "figures")
os.makedirs(FIG_DIR, exist_ok=True)

plt.rcParams.update({'font.size': 11, 'figure.dpi': 100, 'savefig.dpi': 200,
                      'savefig.bbox': 'tight'})

cold_item = json.load(open(os.path.join(ROOT, "results_cold_item_v2.json")))
DATASETS = ['beauty', 'fashion', 'instruments', 'books']

# ============================================================
# Figure 7: Cold-ITEM evaluation - LC2C wins
# ============================================================
fig, ax = plt.subplots(figsize=(11, 5.5))
methods = ['random', 'content_direct', 'content_topk', 'lc2c']
labels = ['Random', 'Content KNN (X@S)', 'Content KNN top-rated', 'LC2C (ours)']
colors = ['#888888', '#3498db', '#9b59b6', '#16a085']
n_methods = len(methods)
x = np.arange(len(DATASETS))
width = 0.18

for i, m in enumerate(methods):
    means, stds = [], []
    for ds in DATASETS:
        v = cold_item.get(ds, {}).get(m, {})
        means.append(v.get('NDCG@10', np.nan))
        stds.append(v.get('NDCG@10_std', 0))
    means = np.array(means); stds = np.array(stds)
    bars = ax.bar(x + (i - n_methods/2 + 0.5) * width, means, width,
                   yerr=stds, label=labels[i], color=colors[i],
                   edgecolor='black', linewidth=0.5,
                   error_kw={'linewidth': 0.8, 'capsize': 2})
    if m == 'lc2c':
        for b in bars: b.set_edgecolor('black'); b.set_linewidth(2.0)
    # Annotate winning method on each dataset
    if m == 'lc2c':
        for j, val in enumerate(means):
            if not np.isnan(val) and val > 0:
                cd = cold_item.get(DATASETS[j], {}).get('content_direct', {}).get('NDCG@10', 0)
                if cd > 0:
                    pct = (val - cd) / cd * 100
                    ax.text(j + (i - n_methods/2 + 0.5) * width, val + 0.005,
                             f'+{pct:.0f}%', ha='center', fontsize=9, fontweight='bold')

ax.set_xticks(x)
ax.set_xticklabels([ds.capitalize() for ds in DATASETS])
ax.set_ylabel('NDCG@10')
ax.set_title('TRUE Cold-ITEM Evaluation (held-out items via GroupKFold-by-item)\n' +
              'Annotations: LC2C improvement over Content KNN baseline')
ax.legend(loc='upper right', frameon=True)
ax.grid(True, axis='y', alpha=0.3); ax.set_axisbelow(True)
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "fig7_cold_item.png"))
plt.savefig(os.path.join(FIG_DIR, "fig7_cold_item.pdf"))
print(f"Saved fig7_cold_item.{{png,pdf}}")
plt.close(fig)


# Print summary
print('\n=== Cold-ITEM summary (paper table material) ===')
print(f'{"Method":<28}', end='')
for ds in DATASETS: print(f'{ds:>12}', end='')
print()
print('-' * (28 + 13 * len(DATASETS)))
for m in methods:
    print(f'{m:<28}', end='')
    for ds in DATASETS:
        v = cold_item.get(ds, {}).get(m, {})
        ndcg = v.get('NDCG@10', np.nan)
        if not np.isnan(ndcg):
            print(f' {ndcg:.4f}      ', end='')
        else:
            print(f' {"--":>12}', end='')
    print()

# Improvement of LC2C over content_direct
print('\nLC2C improvement over content_direct (cold-item NDCG@10):')
for ds in DATASETS:
    cd = cold_item.get(ds, {}).get('content_direct', {}).get('NDCG@10', 0)
    lc = cold_item.get(ds, {}).get('lc2c', {}).get('NDCG@10', 0)
    if cd > 0 and lc > 0:
        pct = (lc - cd) / cd * 100
        print(f'  {ds:<14}: content_direct={cd:.4f}  LC2C={lc:.4f}  delta=+{pct:.1f}%')
