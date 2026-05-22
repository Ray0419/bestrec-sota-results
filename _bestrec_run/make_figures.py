"""Generate publication-ready figures from result JSONs.

All warm-LOO numbers are loaded from the single canonical source
``results_FINAL.json`` (under ``datasets/<ds>/baselines/<method>``).
Earlier rounds also read ``results_lightgcn.json`` directly, but that
file is a per-run snapshot that drifted from the canonical numbers
after the round-3 single-pipeline rerun (Beauty 0.0521 -> 0.0568 in
FINAL, Instruments 0.0524 -> 0.0538). Reading from FINAL keeps the
figure annotations in lock-step with the values quoted in the paper.
``results_lightgcn.json`` / ``results_v6_baselines.json`` /
``cache/books/v5/v5_results.json`` are kept on disk as historical
provenance only and are NOT consulted here.
"""
import os, json
import numpy as np
import matplotlib
matplotlib.use('Agg')  # non-interactive
import matplotlib.pyplot as plt

ROOT = os.path.dirname(__file__)
FIG_DIR = os.path.join(ROOT, "figures")
os.makedirs(FIG_DIR, exist_ok=True)

plt.rcParams.update({
    'font.size': 11, 'axes.labelsize': 12, 'axes.titlesize': 13,
    'legend.fontsize': 10, 'figure.dpi': 100, 'savefig.dpi': 200,
    'savefig.bbox': 'tight', 'figure.figsize': (10, 5),
})

# === Load ALL results ===
def load(fname):
    p = os.path.join(ROOT, fname)
    return json.load(open(p)) if os.path.exists(p) else {}


# Canonical single source of truth for warm-LOO numbers.
final = load("results_FINAL.json")
ablation = load("results_ablation_embeddings.json")
cold = load("results_v7_2_coldstart.json")

DATASETS = ['beauty', 'fashion', 'instruments', 'books']
COLORS = {
    'popularity':   '#888888',
    'multvae':      '#e74c3c',
    'ials':         '#9b59b6',
    'lightgcn':     '#e67e22',
    'ease_pure':    '#3498db',
    'higher_order': '#2ecc71',
    'ease_sbert':   '#16a085',
}
METHOD_LABEL = {
    'popularity':   'Popularity',
    'multvae':      'MultiVAE',
    'ials':         'iALS',
    'lightgcn':     'LightGCN',
    'ease_pure':    'EASE',
    'higher_order': 'EASE^2',
    'ease_sbert':   'EASE+SBERT (ours)',
}


# Build unified warm dict: warm_all[ds][method] = {NDCG@10, std, ...}
# Single canonical source: results_FINAL.json::datasets.<ds>.baselines
warm_all = {ds: {} for ds in DATASETS}
ds_dict = final.get('datasets', {})
for ds in DATASETS:
    bl = ds_dict.get(ds, {}).get('baselines', {})
    for m, v in bl.items():
        warm_all[ds][m] = v


# ============================================================
# Figure 1: NDCG@10 across methods x datasets (grouped bar chart)
# ============================================================
fig, ax = plt.subplots(figsize=(12, 5.5))
methods = ['popularity', 'multvae', 'ials', 'lightgcn', 'ease_pure', 'higher_order', 'ease_sbert']
n_methods = len(methods)
x = np.arange(len(DATASETS))
width = 0.11

for i, m in enumerate(methods):
    means, stds = [], []
    for ds in DATASETS:
        v = warm_all[ds].get(m, {})
        means.append(v.get('NDCG@10', np.nan))
        stds.append(v.get('NDCG@10_std', 0))
    means = np.array(means); stds = np.array(stds)
    bars = ax.bar(x + (i - n_methods/2 + 0.5) * width, means, width,
                   yerr=stds, label=METHOD_LABEL[m],
                   color=COLORS[m], edgecolor='black', linewidth=0.5,
                   error_kw={'linewidth': 0.8, 'capsize': 2})
    # Bold our method
    if m == 'ease_sbert':
        for b in bars:
            b.set_edgecolor('black'); b.set_linewidth(2.0)

ax.set_xticks(x)
ax.set_xticklabels([ds.capitalize() for ds in DATASETS])
ax.set_ylabel('NDCG@10')
ax.set_title('Warm Leave-One-Out NDCG@10 (5-fold mean ± std) — Full-item Ranking')
ax.legend(loc='upper left', frameon=True, ncol=2, fontsize=9)
ax.grid(True, axis='y', alpha=0.3)
ax.set_axisbelow(True)
ax.set_ylim(0, max(0.13, ax.get_ylim()[1]))
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "fig1_warm_methods_x_datasets.png"))
plt.savefig(os.path.join(FIG_DIR, "fig1_warm_methods_x_datasets.pdf"))
print(f"Saved fig1_warm_methods_x_datasets.{{png,pdf}}")
plt.close(fig)


# ============================================================
# Figure 2: Improvement of EASE+SBERT over LightGCN (the headline)
# ============================================================
fig, ax = plt.subplots(figsize=(8, 5))
ours = []; lgc = []; pcts = []
for ds in DATASETS:
    o = warm_all[ds].get('ease_sbert', {}).get('NDCG@10', np.nan)
    l = warm_all[ds].get('lightgcn', {}).get('NDCG@10', np.nan)
    ours.append(o); lgc.append(l)
    pcts.append((o - l) / l * 100 if (l and not np.isnan(l)) else 0)

x = np.arange(len(DATASETS))
ax.bar(x - 0.2, lgc, 0.4, label='LightGCN (He 2020)', color='#e67e22',
       edgecolor='black', linewidth=0.5)
ax.bar(x + 0.2, ours, 0.4, label='EASE+SBERT (ours)', color='#16a085',
       edgecolor='black', linewidth=2.0)
for i, p in enumerate(pcts):
    if p > 0:
        ax.text(i, ours[i] + 0.005, f'+{p:.0f}%', ha='center', fontsize=11, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels([ds.capitalize() for ds in DATASETS])
ax.set_ylabel('NDCG@10')
ax.set_title('EASE+SBERT vs LightGCN on 4 Amazon Datasets')
ax.legend(loc='upper left', frameon=True)
ax.grid(True, axis='y', alpha=0.3); ax.set_axisbelow(True)
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "fig2_vs_lightgcn.png"))
plt.savefig(os.path.join(FIG_DIR, "fig2_vs_lightgcn.pdf"))
print(f"Saved fig2_vs_lightgcn.{{png,pdf}}")
plt.close(fig)


# ============================================================
# Figure 3: Embedding ablation - does SBERT specifically help?
# ============================================================
if ablation:
    fig, ax = plt.subplots(figsize=(10, 5))
    abl_methods = ['no_content (beta=0)', 'random_emb', 'bow_svd', 'sbert (ours)']
    abl_labels = ['No content\n(pure EASE)', 'Random emb\n(384-d Gaussian)',
                   'TF-IDF + SVD\n(lexical)', 'SBERT\n(semantic, ours)']
    abl_colors = ['#888888', '#e74c3c', '#3498db', '#16a085']
    abl_datasets = [ds for ds in ['beauty', 'fashion', 'instruments'] if ds in ablation]
    x = np.arange(len(abl_datasets))
    n_methods_a = len(abl_methods)
    width = 0.18
    for i, m in enumerate(abl_methods):
        means, stds = [], []
        for ds in abl_datasets:
            v = ablation[ds].get(m, {})
            means.append(v.get('NDCG@10', np.nan))
            stds.append(v.get('NDCG@10_std', 0))
        means = np.array(means); stds = np.array(stds)
        bars = ax.bar(x + (i - n_methods_a/2 + 0.5) * width, means, width,
                       yerr=stds, label=abl_labels[i], color=abl_colors[i],
                       edgecolor='black', linewidth=0.5,
                       error_kw={'linewidth': 0.8, 'capsize': 2})
        if 'sbert' in m:
            for b in bars: b.set_edgecolor('black'); b.set_linewidth(2.0)
    ax.set_xticks(x)
    ax.set_xticklabels([ds.capitalize() for ds in abl_datasets])
    ax.set_ylabel('NDCG@10')
    ax.set_title('Content Embedding Ablation — does SBERT specifically help?')
    ax.legend(loc='upper left', frameon=True, ncol=2, fontsize=9)
    ax.grid(True, axis='y', alpha=0.3); ax.set_axisbelow(True)
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, "fig3_ablation_embeddings.png"))
    plt.savefig(os.path.join(FIG_DIR, "fig3_ablation_embeddings.pdf"))
    print(f"Saved fig3_ablation_embeddings.{{png,pdf}}")
    plt.close(fig)


# ============================================================
# Figure 4: Cold-start NDCG@10 — popularity vs ours
# ============================================================
if cold:
    cold_datasets = [ds for ds in DATASETS if ds in cold]
    fig, ax = plt.subplots(figsize=(9, 5))
    methods_cold = ['popularity', 'ctx_title_only', 'rank_fuse_pop_ctxtitle']
    # Books has 'ctx_title' (not 'ctx_title_only') and 'rank_fuse_pop_ctxtitle'
    method_label_cold = {
        'popularity': 'Popularity',
        'ctx_title_only': 'Item title (ours)',
        'rank_fuse_pop_ctxtitle': 'Pop + Title (ours)',
    }
    method_color_cold = {'popularity': '#888888',
                          'ctx_title_only': '#e67e22',
                          'rank_fuse_pop_ctxtitle': '#16a085'}
    width = 0.27
    x = np.arange(len(cold_datasets))
    for i, m in enumerate(methods_cold):
        means, stds = [], []
        for ds in cold_datasets:
            # Books cold has 'ctx_title' instead of 'ctx_title_only'
            m_actual = m
            if ds == 'books' and m == 'ctx_title_only':
                m_actual = 'ctx_title'
            v = cold[ds].get(m_actual, {})
            means.append(v.get('NDCG@10', np.nan))
            stds.append(v.get('NDCG@10_std', 0))
        means = np.array(means); stds = np.array(stds)
        bars = ax.bar(x + (i - 1) * width, means, width, yerr=stds,
                       label=method_label_cold[m],
                       color=method_color_cold[m],
                       edgecolor='black', linewidth=0.5)
        if m == 'rank_fuse_pop_ctxtitle' or 'ctx_title' in m:
            for b in bars: b.set_edgecolor('black'); b.set_linewidth(1.5)
    ax.set_xticks(x)
    ax.set_xticklabels([ds.capitalize() for ds in cold_datasets])
    ax.set_ylabel('NDCG@10')
    ax.set_title('Cold-Start NDCG@10 (GroupKFold, few-shot context)')
    ax.legend(loc='upper left', frameon=True)
    ax.grid(True, axis='y', alpha=0.3); ax.set_axisbelow(True)
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, "fig4_cold_start.png"))
    plt.savefig(os.path.join(FIG_DIR, "fig4_cold_start.pdf"))
    print(f"Saved fig4_cold_start.{{png,pdf}}")
    plt.close(fig)


# ============================================================
# Figure 5: Dataset size vs NDCG@10 (scatter)
# ============================================================
fig, ax = plt.subplots(figsize=(8, 5))
ds_stats = {
    'beauty':      (2535,   '#e74c3c'),
    'fashion':     (3805,   '#3498db'),
    'instruments': (59026,  '#9b59b6'),
    'books':       (601992, '#2ecc71'),
}
plot_methods = ['popularity', 'lightgcn', 'ease_pure', 'ease_sbert']
for m in plot_methods:
    xs, ys = [], []
    for ds, (size, _) in ds_stats.items():
        v = warm_all[ds].get(m, {})
        if v and not np.isnan(v.get('NDCG@10', np.nan)):
            xs.append(size); ys.append(v['NDCG@10'])
    ax.plot(xs, ys, '-o', label=METHOD_LABEL[m], color=COLORS[m],
             markersize=8, linewidth=2,
             markeredgecolor='black', markeredgewidth=1)
ax.set_xscale('log')
ax.set_xlabel('Number of interactions (log scale)')
ax.set_ylabel('NDCG@10')
ax.set_title('Method NDCG@10 vs Dataset Size (log)')
ax.legend(loc='best', frameon=True)
ax.grid(True, alpha=0.3); ax.set_axisbelow(True)
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "fig5_size_vs_ndcg.png"))
plt.savefig(os.path.join(FIG_DIR, "fig5_size_vs_ndcg.pdf"))
print(f"Saved fig5_size_vs_ndcg.{{png,pdf}}")
plt.close(fig)


print(f"\nAll figures saved to: {FIG_DIR}")
