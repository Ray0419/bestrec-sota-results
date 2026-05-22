"""Merge results from all sources into one paper-ready 4-dataset table."""
import json, numpy as np, os

ROOT = os.path.dirname(__file__)


def load(name):
    p = os.path.join(ROOT, f"results_{name}.json")
    return json.load(open(p)) if os.path.exists(p) else {}


warm = load("v6_baselines")
lightgcn = load("lightgcn")
cold = load("v7_2_coldstart")
books_warm = load("books_warm")  # {method: {NDCG@10, ...}}

datasets = ['beauty', 'fashion', 'instruments', 'books']
methods = ['popularity', 'multvae', 'ials', 'lightgcn', 'ease_pure', 'higher_order', 'ease_sbert']
method_label = {
    'popularity': 'Popularity',
    'multvae': 'MultiVAE (Liang 2018)',
    'ials': 'iALS (Hu 2008)',
    'lightgcn': 'LightGCN (He 2020)',
    'ease_pure': 'EASE (Steck 2019)',
    'higher_order': 'Higher-Order EASE',
    'ease_sbert': 'EASE+SBERT (ours)',
}

# Build warm_table[method][dataset]
warm_table = {m: {} for m in methods}
for ds in ['beauty', 'fashion', 'instruments']:
    if ds in warm:
        for m in methods:
            if m in warm[ds]:
                warm_table[m][ds] = warm[ds][m]
    if ds in lightgcn and ds not in warm_table.get('lightgcn', {}):
        warm_table['lightgcn'][ds] = lightgcn[ds]

# Books from results_books_warm.json
for m in methods:
    if m in books_warm:
        warm_table[m]['books'] = books_warm[m]

# Stats per dataset
stats = {
    'beauty':      {'n_users': 253,    'n_items': 356,    'n_inters': 2535,   'k_core': 5},
    'fashion':     {'n_users': 513,    'n_items': 614,    'n_inters': 3805,   'k_core': 4},
    'instruments': {'n_users': 3911,   'n_items': 2269,   'n_inters': 59026,  'k_core': 10},
    'books':       {'n_users': 14407,  'n_items': 13164,  'n_inters': 601992, 'k_core': 20},
}


print('=' * 120)
print('PAPER TABLE 1 - Warm leave-one-out NDCG@10 (5-fold mean +/- std), * = p<0.05 vs ours')
print('=' * 120)
header = f'{"Method":<24}'
for ds in datasets:
    s = stats[ds]
    header += f'  {ds[:10]} (k={s["k_core"]:2d}, {s["n_users"]:>6,}u/{s["n_items"]:>6,}i)'
print(header)
print('-' * 120)
for m in methods:
    line = f'{method_label[m]:<24}'
    for ds in datasets:
        if ds in warm_table[m]:
            v = warm_table[m][ds]
            ndcg = v.get('NDCG@10', 0)
            sd = v.get('NDCG@10_std', 0)
            p = v.get('p_vs_ease_sbert', None)
            mark = ''
            if m != 'ease_sbert' and p is not None:
                if p < 0.001: mark = '***'
                elif p < 0.01: mark = '**'
                elif p < 0.05: mark = '*'
            cell = f'{ndcg:.4f}+/-{sd:.3f}{mark}'
            line += f' {cell:>30}'
        else:
            line += f' {"---":>30}'
    print(line)

print()
print('=' * 80)
print('PAPER TABLE 2 - Cold-start NDCG@10 (GroupKFold by user, few-shot context)')
print('=' * 80)
cold_methods = ['popularity', 'ctx_title_only', 'rank_fuse_pop_ctxtitle']
cold_method_label = {
    'popularity': 'Popularity',
    'ctx_title_only': 'Item title (ours)',
    'rank_fuse_pop_ctxtitle': 'Pop + Title rank fuse (ours)',
}
header = f'{"Method":<32}'
for ds in datasets: header += f' {ds:>14}'
print(header)
print('-' * (32 + 15 * len(datasets)))
# v7_2_coldstart has different keys for books (renamed to ctx_title)
def get_cold(ds, m):
    if ds == 'books':
        # books cold uses 'ctx_title' not 'ctx_title_only'
        m2 = {'ctx_title_only': 'ctx_title'}.get(m, m)
        return cold.get(ds, {}).get(m2)
    return cold.get(ds, {}).get(m)

for m in cold_methods:
    line = f'{cold_method_label[m]:<32}'
    for ds in datasets:
        v = get_cold(ds, m)
        if v:
            line += f' {v["NDCG@10"]:.4f}+/-{v.get("NDCG@10_std",0):.3f}'.rjust(15)
        else:
            line += f' {"---":>14}'
    print(line)

print()
print('Headline: EASE+SBERT (ours) vs LightGCN (most-cited modern baseline):')
for ds in datasets:
    if 'ease_sbert' in warm_table and ds in warm_table['ease_sbert']:
        ours = warm_table['ease_sbert'][ds]['NDCG@10']
        lgc_v = warm_table.get('lightgcn', {}).get(ds)
        if lgc_v:
            lgc = lgc_v['NDCG@10']
            if lgc > 0:
                pct = (ours - lgc) / lgc * 100
                print(f'  {ds:<12}: ours={ours:.4f}  LightGCN={lgc:.4f}  delta=+{pct:.1f}%')
        else:
            # Books: estimate LightGCN ~0.05 from partial
            if ds == 'books':
                print(f'  {ds:<12}: ours={ours:.4f}  LightGCN=~0.0510 (partial folds 0-1)  delta=~+{(ours-0.0510)/0.0510*100:.0f}%')
