"""Recompute significance markers for Table 5.2 (warm-LOO) and Table 5.4b
(cold-item) with proper Holm-Bonferroni correction, plus a user-clustered
bootstrap CI on the cold-item delta.

This script has three sections:

  1. Warm-LOO Holm-corrected per-USER Wilcoxon for Table 5.2.
     - For the four closed-form methods (popularity, ease_pure, higher_order,
       ease_sbert) we recompute the per-USER paired Wilcoxon directly from the
       per-(fold, user, ndcg) records saved by run_warm_loo.py to
       results_warm_loo_perfold_<dataset>.json (round 4 addresses review F5).
       Each user contributes one observation = mean(NDCG) over all their
       held-out pairs across the 5 folds.
     - For the deep baselines (multvae, ials, lightgcn) we continue to consume
       the raw p-values stored in results_FINAL.json (round-3 pipeline);
       saving their per-user vectors in the same standalone format is
       camera-ready scope.
     - Holm-Bonferroni correction is then applied across the six (or five, on
       Books where iALS is OOM) baseline comparisons within each dataset.

  2. Cold-item Holm-corrected per-USER Wilcoxon for Table 5.4b.
     - Reads (fold, user, item, ndcg) records from
       results_cold_item_v2_perpair_<dataset>.json.
     - Each user contributes one observation = mean(NDCG) over all their
       cold-test pairs across the 5 folds.
     - Three comparisons per dataset, Holm-corrected within dataset:
       lc2c_v2 vs content_direct, lc2c, and a simplified DropoutNet-style.

  3. User-clustered bootstrap 95% CI on the V2 - content-direct cold-item
     delta (round 4 addresses review F11). The clustering unit is the user:
     within each bootstrap replicate we resample users (not pairs) with
     replacement, recompute the per-user mean NDCG for V2 and content-direct
     on the resampled users, and take the mean-difference; we then report the
     2.5th and 97.5th percentile of that bootstrap distribution as the CI.
     This respects the user dependency unit but does NOT fully resample folds
     or items, which is camera-ready scope.

Usage:
    uv run python compute_significance.py
"""
import json
import os
from typing import Dict, List, Tuple

import numpy as np
from scipy.stats import wilcoxon

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(os.path.dirname(__file__), "results_FINAL.json")


def holm_bonferroni(p_values: List[Tuple[str, float]], alpha: float = 0.05
                     ) -> Dict[str, Tuple[float, bool, str]]:
    """Holm-Bonferroni step-down correction.

    Args:
        p_values: list of (label, raw_p) tuples.
        alpha: family-wise error rate.

    Returns:
        Dict mapping label -> (raw_p, is_significant, marker).
            marker is one of '***', '**', '*', 'n.s.'.
    """
    # Sort ascending by p-value
    sorted_pairs = sorted(p_values, key=lambda kv: kv[1])
    m = len(sorted_pairs)
    out: Dict[str, Tuple[float, bool, str]] = {}
    first_failure = False
    for rank, (label, p) in enumerate(sorted_pairs):
        # Holm threshold for the k-th smallest (1-indexed): alpha / (m - k + 1)
        threshold = alpha / (m - rank)
        if first_failure:
            sig = False
        else:
            sig = p < threshold
            if not sig:
                first_failure = True

        # Marker based on the raw p, BUT only mark sig if the Holm test passed
        if not sig:
            marker = 'n.s.'
        elif p < 0.001:
            marker = '***'
        elif p < 0.01:
            marker = '**'
        elif p < 0.05:
            marker = '*'
        else:
            marker = 'n.s.'
        out[label] = (p, sig, marker)
    return out


def _warm_loo_per_user_p_value(perfold_path: str, method: str, baseline: str
                                 ) -> Tuple[float, int]:
    """One-sided paired Wilcoxon (greater) on per-USER mean warm-LOO NDCG.

    Reads the per-(fold, user, ndcg) records produced by run_warm_loo.py and
    aggregates each user's observation as the mean NDCG over all their
    held-out pairs across the 5 folds. Returns (raw_p, n_users).
    """
    if not os.path.exists(perfold_path):
        return float('nan'), 0
    raw = json.load(open(perfold_path))
    methods = raw.get('methods', {})
    if method not in methods or baseline not in methods:
        return float('nan'), 0

    def _per_user_mean(records):
        by_user: Dict[int, List[float]] = {}
        for row in records:
            if isinstance(row, dict):
                u = row['user_id']
                val = row.get('ndcg10', row.get('NDCG@10'))
            elif len(row) >= 9:
                # Canonical schema:
                # [dataset, fold_id, seed, method, user_id, target_item_id, ndcg10, hr10, rr]
                u = row[4]
                val = row[6]
            else:
                # Legacy schema: [fold_id, user_id, ndcg]
                _, u, val = row
            by_user.setdefault(int(u), []).append(float(val))
        return {u: float(np.mean(vs)) for u, vs in by_user.items()}

    mu_m = _per_user_mean(methods[method])
    mu_b = _per_user_mean(methods[baseline])
    common = sorted(set(mu_m.keys()) & set(mu_b.keys()))
    if len(common) < 5:
        return float('nan'), len(common)
    arr_m = np.array([mu_m[u] for u in common], dtype=np.float64)
    arr_b = np.array([mu_b[u] for u in common], dtype=np.float64)
    diffs = arr_m - arr_b
    if np.all(diffs == 0):
        return 1.0, len(common)
    try:
        _, p = wilcoxon(diffs, alternative='greater', zero_method='wilcox')
    except Exception:
        return float('nan'), len(common)
    return float(p), len(common)


def main():
    data = json.load(open(RESULTS))
    print('Holm-Bonferroni-corrected significance markers for Table 5.2')
    print('=' * 78)
    print('(one-sided paired Wilcoxon signed-rank, H1: NDCG_ours > NDCG_baseline)')
    print('Source for closed-form methods (popularity/ease_pure/higher_order): '
          'results_warm_loo_perfold_<ds>.json (round 4, per-USER recompute).')
    print('Source for deep baselines (multvae/ials/lightgcn): results_FINAL.json '
          'raw p-values from prior pipeline.')
    print()

    method_order = ['popularity', 'multvae', 'ials', 'lightgcn',
                    'ease_pure', 'higher_order']
    # Map paper-baseline name -> per-fold JSON method name (run_warm_loo.py)
    PERFOLD_NAME = {
        'popularity':    'popularity',
        'ease_pure':     'ease_pure',
        'higher_order':  'higher_order_ease',
    }

    per_dataset = {}
    per_dataset_source = {}   # for transparency on which path produced each p
    for ds in ['beauty', 'fashion', 'instruments', 'books']:
        bls = data['datasets'][ds]['baselines']
        pvs: List[Tuple[str, float]] = []
        srcs: Dict[str, str] = {}
        perfold_path = os.path.join(
            os.path.dirname(__file__),
            f"results_warm_loo_perfold_{ds}.json")
        perfold_available = os.path.exists(perfold_path)
        for m in method_order:
            if m not in bls or 'p_vs_ease_sbert' not in bls[m]:
                continue
            # Prefer per-user recompute for the closed-form methods
            if perfold_available and m in PERFOLD_NAME:
                p_new, n = _warm_loo_per_user_p_value(
                    perfold_path, 'ease_sbert', PERFOLD_NAME[m])
                if not np.isnan(p_new):
                    pvs.append((m, p_new))
                    srcs[m] = f'perfold ({n} users)'
                    continue
            # Fallback to stored value
            pvs.append((m, bls[m]['p_vs_ease_sbert']))
            srcs[m] = 'results_FINAL.json (stored)'
        per_dataset[ds] = holm_bonferroni(pvs, alpha=0.05)
        per_dataset_source[ds] = srcs

    # print per-dataset summaries
    for ds in ['beauty', 'fashion', 'instruments', 'books']:
        print(f'--- {ds.upper()} ---')
        print(f'{"method":<14} {"NDCG@10":>10} {"raw p":>10} {"Holm sig?":>10} '
              f'{"marker":>8} {"source":>26}')
        for m in method_order:
            if m not in per_dataset[ds]:
                print(f'{m:<14} {"---":>10} {"---":>10} {"---":>10} '
                      f'{"---":>8} {"---":>26}')
                continue
            p, sig, marker = per_dataset[ds][m]
            ndcg = data['datasets'][ds]['baselines'][m]['NDCG@10']
            src = per_dataset_source.get(ds, {}).get(m, '?')
            print(f'{m:<14} {ndcg:>10.4f} {p:>10.4f} {str(sig):>10} '
                  f'{marker:>8} {src:>26}')
        print()

    # Output the corrected Table 5.2 cell strings
    print()
    print('=' * 78)
    print('Suggested Table 5.2 cells (NDCG@10 + marker):')
    print('=' * 78)
    print(f'{"Method":<22} {"Beauty":>14} {"Fashion":>14} {"Instr.":>14} {"Books":>14}')
    for m in method_order:
        cells = []
        for ds in ['beauty', 'fashion', 'instruments', 'books']:
            if m not in per_dataset[ds]:
                cells.append('OOM')
                continue
            p, sig, marker = per_dataset[ds][m]
            ndcg = data['datasets'][ds]['baselines'][m]['NDCG@10']
            cell = f'{ndcg:.3f} {marker}' if marker != 'n.s.' else f'{ndcg:.3f} n.s.'
            cells.append(cell)
        print(f'{m:<22} {cells[0]:>14} {cells[1]:>14} {cells[2]:>14} {cells[3]:>14}')

    # Save corrected markers to JSON for the paper builder
    out = {ds: {m: {'p_raw': p, 'holm_sig': sig, 'marker': marker}
                for m, (p, sig, marker) in per_dataset[ds].items()}
           for ds in per_dataset}
    out_path = os.path.join(os.path.dirname(__file__), "significance_corrected.json")
    json.dump(out, open(out_path, "w"), indent=2)
    print()
    print(f'Saved corrected markers to {out_path}')

    # ----------------------------------------------------------------
    # Cold-item: mean differences for LC2C V1 / V2 vs. content-direct.
    # Reads from the REGENERATED results_cold_item_v2.json which contains
    # both `lc2c` (V1) and `lc2c_v2` (V2 headline) keys produced by the
    # updated run_cold_item_v2.py.
    # ----------------------------------------------------------------
    print()
    print('=' * 78)
    print('Cold-item mean-NDCG comparison (5-fold means)')
    print('=' * 78)
    ci_path = os.path.join(os.path.dirname(__file__), "results_cold_item_v2.json")
    if not os.path.exists(ci_path):
        print(f'{ci_path} missing; skipping cold-item summary.')
        return
    ci_data = json.load(open(ci_path))
    print(f'{"Dataset":<14} {"content-dir":>12} {"LC2C V1":>10} {"LC2C V2":>10} '
          f'{"V2-vs-CD":>10} {"V2-vs-V1":>10}')
    for ds in ['beauty', 'fashion', 'instruments', 'books']:
        if ds not in ci_data:
            continue
        cd = ci_data[ds].get('content_direct', {}).get('NDCG@10')
        v1 = ci_data[ds].get('lc2c', {}).get('NDCG@10')
        v2 = ci_data[ds].get('lc2c_v2', {}).get('NDCG@10')
        if cd is None or v1 is None or v2 is None:
            print(f'{ds:<14}  missing one or more methods in JSON')
            continue
        pct_v2_cd = 100 * (v2 - cd) / cd if cd else 0
        pct_v2_v1 = 100 * (v2 - v1) / v1 if v1 else 0
        print(f'{ds:<14} {cd:>12.4f} {v1:>10.4f} {v2:>10.4f} '
              f'{pct_v2_cd:>9.1f}% {pct_v2_v1:>9.1f}%')
    print()
    print('Note: LC2C V2 is the headline method (key `lc2c_v2`). LC2C V1 (key `lc2c`)')
    print('is the SVD-compressed legacy variant kept as an ablation.')

    # ----------------------------------------------------------------
    # Cold-item paired Wilcoxon with PROPER unit of analysis: per-user
    # mean NDCG (pooled within user across all their cold-test pairs and
    # all 5 folds). This eliminates the pseudo-replication issue flagged
    # in round-3 review, where pooling at the (user, item, fold)-pair
    # level inflated the sample size and produced absurd p-values.
    #
    # Reads the (fold, user, item, ndcg) records saved by
    # run_cold_item_v2.py to results_cold_item_v2_perpair_<dataset>.json.
    # ----------------------------------------------------------------
    print()
    print('=' * 78)
    print('Cold-item PAIRED WILCOXON (per-USER mean NDCG, unit-of-analysis fixed)')
    print('=' * 78)
    print('H1: NDCG_target_method > NDCG_baseline_method, one-sided.')
    print('Each user contributes one observation = mean(NDCG) over all their')
    print('cold-test pairs across all 5 folds. This eliminates the per-pair')
    print('pseudo-replication issue that inflated p-values in the prior round.')
    print()
    print(f'{"Dataset":<14} {"Comparison":<26} {"n_users":>9} {"raw p":>12} {"sig":>6}')
    print('-' * 78)

    def _per_user_mean_ndcg(records: List) -> Dict[int, float]:
        """Return user_id -> mean NDCG for legacy or canonical cold records."""
        by_user: Dict[int, List[float]] = {}
        for row in records:
            if isinstance(row, dict):
                u = row['user_id']
                val = row.get('ndcg10', row.get('NDCG@10'))
            elif len(row) >= 10:
                # [dataset, fold_id, seed, method, user_id, target_item_id,
                #  candidate_scope, ndcg10, hr10, rr]
                u = row[4]
                val = row[7]
            else:
                # Legacy [fold, user, item, ndcg]
                _, u, _, val = row
            by_user.setdefault(int(u), []).append(float(val))
        return {u: float(np.mean(vs)) for u, vs in by_user.items()}

    def _fmt_p(p):
        if p < 1e-300:
            return '<1e-300'
        if p < 1e-10:
            return f'{p:.2e}'
        return f'{p:.4g}'

    pairwise_results = {}
    for ds in ['beauty', 'fashion', 'instruments', 'books']:
        perpair_path = os.path.join(
            os.path.dirname(__file__),
            f"results_cold_item_v2_perpair_{ds}.json")
        if not os.path.exists(perpair_path):
            print(f'{ds:<14}  (no per-pair file)')
            continue
        per_raw = json.load(open(perpair_path))
        # The file is now {'schema': ..., 'methods': {name: [[fold,u,i,ndcg], ...]}}
        # Older files may still be {name: [ndcg, ...]} without metadata; we
        # detect that and skip the per-user test in that case.
        if isinstance(per_raw, dict) and 'methods' in per_raw:
            per = per_raw['methods']
            has_metadata = True
        else:
            per = per_raw
            has_metadata = False

        comparisons = [
            ('lc2cpp_zfusion > lc2c_v2', 'lc2cpp_zfusion', 'lc2c_v2'),
            ('lc2cpp_zfusion > content_direct', 'lc2cpp_zfusion', 'content_direct'),
            ('lc2cpp_zfusion > dropoutnet', 'lc2cpp_zfusion', 'dropoutnet'),
            ('lc2c_v2 > content_direct', 'lc2c_v2', 'content_direct'),
            ('lc2c_v2 > lc2c (V1)',       'lc2c_v2', 'lc2c'),
            ('lc2c_v2 > dropoutnet',      'lc2c_v2', 'dropoutnet'),
        ]
        pairwise_results[ds] = {}

        if not has_metadata:
            print(f'{ds:<14}  per-pair file lacks (fold, user, item) metadata; '
                  'rerun run_cold_item_v2.py to regenerate.')
            continue

        for label, a, b in comparisons:
            if a not in per or b not in per:
                continue
            mu_a = _per_user_mean_ndcg(per[a])
            mu_b = _per_user_mean_ndcg(per[b])
            common_users = sorted(set(mu_a.keys()) & set(mu_b.keys()))
            n = len(common_users)
            if n == 0:
                continue
            arr_a = np.array([mu_a[u] for u in common_users], dtype=np.float64)
            arr_b = np.array([mu_b[u] for u in common_users], dtype=np.float64)
            diffs = arr_a - arr_b
            try:
                if np.all(diffs == 0):
                    p = 1.0
                else:
                    _, p = wilcoxon(diffs, alternative='greater', zero_method='wilcox')
            except Exception as e:
                print(f'{ds:<14} {label:<26}: skipped ({e})')
                continue
            sig = ('***' if p < 0.001 else
                   '**'  if p < 0.01  else
                   '*'   if p < 0.05  else
                   'n.s.')
            pairwise_results[ds][label] = {'n_users': n, 'raw_p': float(p),
                                             'raw_p_str': _fmt_p(p), 'marker': sig}
            print(f'{ds:<14} {label:<26} {n:>9d} {_fmt_p(p):>12} {sig:>6}')

    # Apply Holm-Bonferroni within each dataset.
    print()
    print('Holm-Bonferroni-corrected markers (within-dataset cold-item comparison family):')
    print(f'{"Dataset":<14} {"Comparison":<26} {"Holm sig?":>10} {"marker":>8}')
    print('-' * 70)
    holm_out = {}
    for ds, res in pairwise_results.items():
        pvs = [(label, info['raw_p']) for label, info in res.items()]
        corrected = holm_bonferroni(pvs, alpha=0.05)
        holm_out[ds] = {label: {'p_raw': p,
                                  'p_raw_str': _fmt_p(p),
                                  'holm_sig': sig,
                                  'marker': marker,
                                  'n_users': res[label]['n_users']}
                         for label, (p, sig, marker) in corrected.items()}
        for label, (p, sig, marker) in corrected.items():
            print(f'{ds:<14} {label:<26} {str(sig):>10} {marker:>8}')

    out2 = os.path.join(os.path.dirname(__file__), "significance_cold_item_corrected.json")
    json.dump(holm_out, open(out2, 'w'), indent=2)
    print(f'\nSaved cold-item Holm-corrected markers to {os.path.basename(out2)}')

    # ----------------------------------------------------------------
    # User-clustered bootstrap CI on the V2 - content-direct cold-item
    # delta (round 4: review F11). Within each replicate we resample
    # users (not pairs) with replacement, recompute per-user mean NDCG
    # for V2 and content-direct on the resampled users, and take the
    # mean difference. Reported as the 2.5th and 97.5th percentile of
    # the bootstrap distribution. This respects the user dependency
    # unit but does NOT fully resample folds or items, which is
    # camera-ready scope.
    # ----------------------------------------------------------------
    print()
    print('=' * 78)
    print('User-clustered bootstrap 95% CI on V2 - content-direct cold-item delta')
    print('=' * 78)
    print('B = 2000 bootstrap replicates, resampling users with replacement.')
    print()
    rng = np.random.default_rng(42)
    B = 2000
    boot_out: Dict[str, Dict[str, float]] = {}
    print(f'{"Dataset":<14} {"n_users":>9} {"V2 mean":>10} {"CD mean":>10} '
          f'{"delta":>10} {"95% CI":>22}')
    print('-' * 78)
    for ds in ['beauty', 'fashion', 'instruments', 'books']:
        perpair_path = os.path.join(
            os.path.dirname(__file__),
            f"results_cold_item_v2_perpair_{ds}.json")
        if not os.path.exists(perpair_path):
            continue
        per_raw = json.load(open(perpair_path))
        per = per_raw.get('methods', per_raw)
        if 'lc2c_v2' not in per or 'content_direct' not in per:
            continue
        mu_v2 = _per_user_mean_ndcg(per['lc2c_v2'])
        mu_cd = _per_user_mean_ndcg(per['content_direct'])
        users = sorted(set(mu_v2.keys()) & set(mu_cd.keys()))
        n = len(users)
        if n < 30:
            continue
        v2_arr = np.array([mu_v2[u] for u in users])
        cd_arr = np.array([mu_cd[u] for u in users])
        delta_point = float((v2_arr - cd_arr).mean())
        boot_deltas = np.empty(B, dtype=np.float64)
        idx_all = np.arange(n)
        for b in range(B):
            sample = rng.choice(idx_all, size=n, replace=True)
            boot_deltas[b] = (v2_arr[sample] - cd_arr[sample]).mean()
        lo, hi = np.percentile(boot_deltas, [2.5, 97.5])
        boot_out[ds] = {
            'n_users':         n,
            'v2_mean':         float(v2_arr.mean()),
            'content_mean':    float(cd_arr.mean()),
            'delta_point':     delta_point,
            'ci_lo_95':        float(lo),
            'ci_hi_95':        float(hi),
            'B_replicates':    B,
            'resampling_unit': 'user',
        }
        ci_str = f'[{lo:+.4f}, {hi:+.4f}]'
        print(f'{ds:<14} {n:>9d} {v2_arr.mean():>10.4f} {cd_arr.mean():>10.4f} '
              f'{delta_point:>+10.4f} {ci_str:>22}')

    out3 = os.path.join(os.path.dirname(__file__),
                          "significance_cold_item_bootstrap.json")
    json.dump(boot_out, open(out3, 'w'), indent=2)
    print(f'\nSaved user-clustered bootstrap CI to {os.path.basename(out3)}')


if __name__ == "__main__":
    main()
